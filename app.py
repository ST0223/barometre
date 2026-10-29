"""Plateforme Datatym — automatisation des baromètres.

Lancement : python app.py  puis ouvrir http://127.0.0.1:8765
"""
import json
import logging
import re
import shutil
import tempfile
import urllib.error
import uuid
import webbrowser
from pathlib import Path
from threading import Timer

from flask import Flask, abort, jsonify, request, send_file, send_from_directory

from datatym import budget, deroulement, equipe, importation, llm, moteur, store
from datatym.banque import TYPES
from datatym.config import BASE_DIR, PROJETS_DIR, STATIC_DIR, charger_parametres, enregistrer_parametres
from datatym.etapes import collecte
from datatym.outils import propre

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
app.json.sort_keys = False  # garde l'ordre des documents (version terrain avant version digitale)


def _projet(slug):
    p = store.charger(slug)
    if not p:
        abort(404)
    return p


def ok(projet):
    return jsonify(moteur.vue(projet))


@app.errorhandler(moteur.ErreurChaine)
def erreur_chaine(e):
    return jsonify({"erreur": str(e)}), 400


@app.errorhandler(Exception)
def erreur(e):
    code = getattr(e, "code", 500)
    if code != 500:
        return jsonify({"erreur": getattr(e, "description", str(e))}), code
    logging.exception("Erreur serveur")
    return jsonify({"erreur": f"Erreur interne : {e}"}), 500


@app.get("/")
def accueil():
    """Page unique ; chaque script et feuille de style porte sa date de modification, pour que le navigateur
    recharge un fichier mis à jour au lieu de garder l'ancien en cache."""
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    def versionner(m):
        chemin = STATIC_DIR / m.group(2)
        return f'{m.group(1)}/static/{m.group(2)}?v={int(chemin.stat().st_mtime)}"' if chemin.exists() else m.group(0)
    html = re.sub(r'((?:src|href)=")/static/([^"?]+\.(?:js|css))"', versionner, html)
    reponse = app.response_class(html, mimetype="text/html")
    reponse.headers["Cache-Control"] = "no-cache"
    return reponse


# ------------------------------------------------------------------ projets
@app.get("/api/projets")
def lister():
    return jsonify(store.lister())


@app.post("/api/projets")
def creer():
    fiche = store.nettoyer_fiche(request.get_json(force=True))
    manquants = store.erreurs_fiche(fiche)
    if manquants:
        return jsonify({"erreur": "Champs obligatoires manquants : " + ", ".join(manquants)}), 400
    return ok(store.creer(fiche))


@app.get("/api/projets/<slug>")
def detail(slug):
    return ok(_projet(slug))


@app.put("/api/projets/<slug>/fiche")
def maj_fiche(slug):
    p = _projet(slug)
    fiche = store.nettoyer_fiche({**p["fiche"], **request.get_json(force=True)})
    manquants = store.erreurs_fiche(fiche)
    if manquants:
        return jsonify({"erreur": "Champs obligatoires manquants : " + ", ".join(manquants)}), 400
    return ok(moteur.maj_fiche(p, fiche))


@app.delete("/api/projets/<slug>")
def supprimer(slug):
    try:
        store.supprimer(slug)
    except OSError:
        return jsonify({"erreur": "Suppression impossible : un fichier de cette étude est ouvert (Word, Excel…) ou en cours de "
                                  "synchronisation OneDrive. Fermez-le, puis réessayez."}), 409
    return jsonify({"ok": True})


# ------------------------------------------------------------------ étapes
ACTIONS = {"generer": moteur.generer, "regenerer": moteur.regenerer_texte, "valider": moteur.valider, "rouvrir": moteur.rouvrir}


@app.post("/api/projets/<slug>/etapes/<cle>/<action>")
def action_etape(slug, cle, action):
    if cle not in store.CLES or action not in ACTIONS:
        abort(404)
    return ok(ACTIONS[action](_projet(slug), cle))


@app.put("/api/projets/<slug>/etapes/<cle>/data")
def maj_data(slug, cle):
    if cle not in store.CLES:
        abort(404)
    return ok(moteur.maj_data(_projet(slug), cle, request.get_json(force=True)))


@app.put("/api/projets/<slug>/etapes/<cle>/docs/<nom>")
def maj_doc(slug, cle, nom):
    if cle not in store.CLES:
        abort(404)
    return ok(moteur.maj_doc(_projet(slug), cle, nom, request.get_json(force=True)))


# ------------------------------------------------------------------ import d'une note de cadrage (et de son questionnaire)
IMPORTS = PROJETS_DIR / ".imports"


@app.post("/api/import/analyser")
def import_analyser():
    """Lit la note (et le questionnaire s'il est joint) et renvoie une proposition d'étude à vérifier."""
    note, quest = request.files.get("note"), request.files.get("questionnaire")
    if not note or not note.filename.lower().endswith(".docx"):
        return jsonify({"erreur": "La note de cadrage doit être un document Word (.docx)."}), 400
    if quest and quest.filename and not quest.filename.lower().endswith(".docx"):
        return jsonify({"erreur": "Le questionnaire doit être un document Word (.docx)."}), 400
    ident = uuid.uuid4().hex
    d = IMPORTS / ident
    d.mkdir(parents=True, exist_ok=True)
    note.save(d / "note.docx")
    avec_q = bool(quest and quest.filename)
    if avec_q:
        quest.save(d / "questionnaire.docx")
    try:
        prop, notes = importation.proposer(d / "note.docx", d / "questionnaire.docx" if avec_q else None)
    except Exception as exc:  # document illisible ou d'un format inattendu
        shutil.rmtree(d, ignore_errors=True)
        return jsonify({"erreur": f"Lecture impossible du document : {exc}"}), 400
    (d / "proposition.json").write_text(json.dumps(prop, ensure_ascii=False), encoding="utf-8")
    return jsonify({"id": ident, "proposition": prop, "notes": notes,
                    "fichiers": {"note": note.filename, "questionnaire": quest.filename if avec_q else None}})


@app.post("/api/import/creer")
def import_creer():
    """Crée l'étude à partir de la proposition vérifiée et de la fiche corrigée."""
    c = request.get_json(force=True)
    ident = str(c.get("id", ""))
    d = IMPORTS / ident
    if not re.fullmatch(r"[0-9a-f]{32}", ident) or not (d / "proposition.json").exists():
        return jsonify({"erreur": "Import introuvable : déposez à nouveau les documents."}), 404
    prop = json.loads((d / "proposition.json").read_text(encoding="utf-8"))
    fiche = store.nettoyer_fiche({**prop["fiche"], **(c.get("fiche") or {})})
    manquants = store.erreurs_fiche(fiche)
    if manquants:
        return jsonify({"erreur": "Champs obligatoires manquants : " + ", ".join(manquants)}), 400
    q = d / "questionnaire.docx"
    p = importation.creer_etude(prop, fiche, d / "note.docx", q if q.exists() else None, valider=bool(c.get("valider", True)))
    shutil.rmtree(d, ignore_errors=True)
    return ok(p)


@app.post("/api/projets/<slug>/boucler")
def boucler(slug):
    return ok(moteur.boucler(_projet(slug)))


@app.get("/api/projets/<slug>/archive")
def archive(slug):
    chemin = moteur.chemin_archive(_projet(slug))
    if not chemin.exists():
        abort(404)
    return send_file(chemin, as_attachment=True, download_name=chemin.name)


@app.get("/api/projets/<slug>/deroulement")
def deroulement_etude(slug):
    """Déroulement de l'étude présenté au dirigeant : calendrier, scénarios, options de taille, vigilance."""
    return jsonify(deroulement.presenter(_projet(slug)))


@app.get("/api/projets/<slug>/deroulement/<fmt>")
def deroulement_fichier(slug, fmt):
    if fmt not in ("docx", "pptx"):
        abort(404)
    p = _projet(slug)
    chemin = store.dossier(slug) / "donnees" / store.nom_fichier(p, "Deroulement_Etude", 1, fmt).replace("_v1.", ".")
    chemin.parent.mkdir(parents=True, exist_ok=True)
    (deroulement.docx if fmt == "docx" else deroulement.pptx)(chemin, p)
    return send_file(chemin, as_attachment=True, download_name=chemin.name)


def _plan(p):
    d = (p["etapes"]["echantillonnage"].get("data") or {})
    if not d.get("zones"):
        raise moteur.ErreurChaine("Générez d'abord le plan d'échantillonnage.")
    besoin = d.get("besoin") or {z: sum(1 for m in d["enqueteurs"] if m["zone"] == z) for z in d["zones"]}
    return d["zones"], besoin, d.get("reserve") or {}


@app.get("/api/projets/<slug>/equipe/modele")
def modele_equipe(slug):
    """Fichier Excel que les RH renseignent avec les enquêteurs retenus."""
    p = _projet(slug)
    zones, besoin, reserve = _plan(p)
    chemin = store.dossier(slug) / "donnees" / store.nom_fichier(p, "Liste_Enqueteurs_A_Renseigner", 1, "xlsx").replace("_v1.", ".")
    chemin.parent.mkdir(parents=True, exist_ok=True)
    equipe.modele_xlsx(chemin, zones, besoin, reserve)
    return send_file(chemin, as_attachment=True, download_name=chemin.name)


@app.post("/api/projets/<slug>/equipe/lire")
def lire_equipe(slug):
    """Lit et contrôle la liste retournée par les RH ; elle n'est enregistrée qu'avec les paramètres de l'étape."""
    p = _projet(slug)
    zones, besoin, reserve = _plan(p)
    f = request.files.get("fichier")
    if not f or not f.filename.lower().endswith((".xlsx", ".csv")):
        return jsonify({"erreur": "Choisissez le fichier Excel (.xlsx) renseigné par les RH."}), 400
    chemin = store.dossier(slug) / "donnees" / ("equipe_rh" + Path(f.filename).suffix.lower())
    chemin.parent.mkdir(parents=True, exist_ok=True)
    f.save(chemin)
    try:
        liste, alertes, rejetes = equipe.lire(chemin, zones, besoin, reserve)
    except Exception as exc:  # fichier illisible ou sans les colonnes attendues
        return jsonify({"erreur": f"Lecture impossible : {exc}"}), 400
    return jsonify({"equipe": liste, "alertes": alertes, "rejetes": rejetes, "fichier": f.filename})


@app.get("/api/projets/<slug>/fichiers/<path:nom>")
def telecharger(slug, nom):
    _projet(slug)
    dossier = (store.dossier(slug) / "livrables").resolve()
    chemin = (dossier / nom).resolve()
    if dossier not in chemin.parents or not chemin.exists():
        abort(404)
    if request.args.get("format") == "pdf" and chemin.suffix == ".docx":
        chemin = moteur.vers_pdf(chemin)
    return send_file(chemin, as_attachment=request.args.get("voir") != "1", download_name=chemin.name)


@app.get("/media/<path:chemin>")
def media(chemin):
    """Images des graphiques (aperçu des documents)."""
    cible = (BASE_DIR / chemin).resolve()
    if PROJETS_DIR.resolve() not in cible.parents or cible.suffix.lower() not in (".png", ".jpg") or not cible.exists():
        abort(404)
    return send_file(cible)


# ------------------------------------------------------------------ collecte
def _etat_collecte(p):
    if moteur.statut(p, "collecte") in ("verrouille",):
        raise moteur.ErreurChaine("Validez d'abord la note méthodologique.")
    if moteur.statut(p, "collecte") == "a_generer":
        moteur.generer(p, "collecte")


@app.post("/api/projets/<slug>/collecte/import")
def importer(slug):
    p = _projet(slug)
    _etat_collecte(p)
    f = request.files.get("fichier")
    if not f or not f.filename:
        return jsonify({"erreur": "Aucun fichier reçu."}), 400
    suffixe = Path(f.filename).suffix.lower()
    if suffixe not in (".csv", ".xlsx", ".xls"):
        return jsonify({"erreur": "Format accepté : CSV ou Excel (export Kobo ou QuestionPro)."}), 400
    with tempfile.TemporaryDirectory() as d:
        chemin = Path(d) / f"import{suffixe}"
        f.save(chemin)
        n = collecte.importer_fichier(p, chemin)
    p["etapes"]["collecte"]["data"]["source"] = f"Fichier {f.filename}"
    store.journaliser(p, f"Collecte : {n} soumissions importées depuis {f.filename}.")
    moteur.rafraichir_collecte(p)
    return ok(p)


def _sync_kobo(p, serveur, jeton, reference):
    """Télécharge les soumissions Kobo ; renvoie le message du journal, ou lève ErreurChaine."""
    try:
        n, serveur, asset = collecte.importer_kobo(p, serveur or "https://kf.kobotoolbox.org", jeton, reference)
    except urllib.error.HTTPError as exc:
        motif = {401: "jeton API refusé", 403: "ce jeton n'a pas accès au formulaire", 404: "formulaire introuvable sur ce serveur"}
        raise moteur.ErreurChaine(f"KoboToolbox : {motif.get(exc.code, f'erreur {exc.code}')}.")
    except ValueError as exc:
        raise moteur.ErreurChaine(str(exc))
    except Exception as exc:
        raise moteur.ErreurChaine(f"Connexion à KoboToolbox impossible : {exc}")
    d = p["etapes"]["collecte"]["data"]
    d["source"] = "API KoboToolbox"
    d["kobo"] = {"serveur": serveur, "asset": asset, "lien": reference if str(reference).startswith("http") else (d.get("kobo") or {}).get("lien", "")}
    return f"Collecte : {n} soumissions synchronisées depuis KoboToolbox."


def _sync_questionpro(p, env, cle, enquete):
    try:
        n, ecartees, ignorees = collecte.importer_questionpro(p, p["etapes"]["questionnaire"]["data"], env, cle, enquete)
    except urllib.error.HTTPError as exc:
        motif = {401: "clé API refusée", 403: "accès refusé à cette enquête", 404: "enquête introuvable (vérifiez l'identifiant et le centre de données)"}
        raise moteur.ErreurChaine(f"QuestionPro : {motif.get(exc.code, f'erreur {exc.code}')}.")
    except Exception as exc:
        raise moteur.ErreurChaine(f"Connexion à QuestionPro impossible : {exc}")
    d = p["etapes"]["collecte"]["data"]
    d["source"] = "API QuestionPro"
    d["questionpro"] = {"env": env, "enquete": enquete}
    message = f"Collecte : {n} réponses complétées synchronisées depuis QuestionPro"
    if ecartees:
        message += f", {ecartees} incomplètes écartées"
    if ignorees:
        message += f" ; {len(ignorees)} question(s) non reconnue(s) : {', '.join(ignorees[:5])}"
    return message + "."


@app.post("/api/projets/<slug>/collecte/kobo")
def kobo(slug):
    p = _projet(slug)
    _etat_collecte(p)
    c = request.get_json(force=True)
    jeton = (c.get("jeton") or "").strip() or charger_parametres().get("kobo_jeton", "")
    if not (jeton and c.get("asset")):
        return jsonify({"erreur": "Le lien du formulaire (ou son identifiant) et le jeton API Kobo sont requis."}), 400
    store.journaliser(p, _sync_kobo(p, c.get("serveur"), jeton, c["asset"]))
    if c.get("memoriser", True) and c.get("jeton"):
        enregistrer_parametres({"kobo_jeton": jeton})
    moteur.rafraichir_collecte(p)
    return ok(p)


@app.get("/api/projets/<slug>/collecte/indicateurs")
def indicateurs_collecte(slug):
    """Indicateurs de la note de cadrage calculés en direct sur les réponses (filtre facultatif)."""
    return jsonify(propre(collecte.indicateurs(_projet(slug), request.args.get("filtre", ""))))


@app.post("/api/projets/<slug>/collecte/questionpro")
def questionpro(slug):
    p = _projet(slug)
    _etat_collecte(p)
    c = request.get_json(force=True)
    env, enquete = (c.get("env") or "com").strip(), str(c.get("enquete") or "").strip()
    if not enquete.isdigit():
        # adresse de l'éditeur (…surveyID=13825453) : on en tire le numéro ; un lien de réponse (…/t/…) ne le contient pas
        trouve = re.search(r"(?:survey_?id=|/surveys/)(\d+)", enquete, re.I)
        if not trouve:
            return jsonify({"erreur": "Saisissez le numéro de l'enquête QuestionPro (ex. 13825453), pas le lien de réponse : "
                                      "il apparaît dans l'adresse de l'enquête ouverte en édition (surveyID=…)."}), 400
        enquete = trouve.group(1)
    cle = (c.get("cle") or "").strip() or charger_parametres().get("questionpro_cle", "")
    if not (cle and enquete):
        return jsonify({"erreur": "Clé API et identifiant de l'enquête QuestionPro sont requis."}), 400
    store.journaliser(p, _sync_questionpro(p, env, cle, enquete))
    if c.get("memoriser", True) and c.get("cle"):
        enregistrer_parametres({"questionpro_cle": cle})
    moteur.rafraichir_collecte(p)
    return ok(p)


@app.post("/api/projets/<slug>/collecte/simuler")
def simuler(slug):
    p = _projet(slug)
    _etat_collecte(p)
    taux = float(request.get_json(force=True).get("taux", 1))
    n = collecte.simuler(p, p["etapes"]["questionnaire"]["data"], p["etapes"]["echantillonnage"]["data"], taux=taux)
    p["etapes"]["collecte"]["data"]["source"] = "Données de test simulées"
    store.journaliser(p, f"Collecte : {n} soumissions de test générées ({int(taux * 100)} % du calendrier).")
    moteur.rafraichir_collecte(p)
    return ok(p)


@app.post("/api/projets/<slug>/collecte/actualiser")
def actualiser(slug):
    """Retélécharge les soumissions depuis la plateforme de collecte (jeton mémorisé), puis recalcule le tableau de bord."""
    p = _projet(slug)
    _etat_collecte(p)
    d, params = p["etapes"]["collecte"]["data"], charger_parametres()
    if d.get("source") == "API KoboToolbox" and d.get("kobo", {}).get("asset") and params.get("kobo_jeton"):
        store.journaliser(p, _sync_kobo(p, d["kobo"].get("serveur"), params["kobo_jeton"], d["kobo"]["asset"]))
    elif d.get("source") == "API QuestionPro" and d.get("questionpro", {}).get("enquete") and params.get("questionpro_cle"):
        q = d["questionpro"]
        store.journaliser(p, _sync_questionpro(p, q.get("env", "com"), params["questionpro_cle"], q["enquete"]))
    moteur.rafraichir_collecte(p)
    return ok(p)


# ------------------------------------------------------------------ paramètres
@app.get("/api/parametres")
def lire_parametres():
    p = charger_parametres()
    cle = p.get("anthropic_api_key", "")
    p["anthropic_api_key"] = (cle[:7] + "…" + cle[-4:]) if cle else ""
    p["cle_definie"] = bool(cle)
    # les jetons de collecte ne quittent jamais le serveur : seule leur présence est signalée
    p["kobo_jeton_defini"], p["questionpro_cle_definie"] = bool(p.pop("kobo_jeton", "")), bool(p.pop("questionpro_cle", ""))
    p["couts_unitaires"] = budget.couts_reference()
    return jsonify(p)


@app.put("/api/parametres")
def ecrire_parametres():
    maj = request.get_json(force=True)
    if "…" in str(maj.get("anthropic_api_key", "")):
        maj.pop("anthropic_api_key")
    for oublier in ("kobo_jeton", "questionpro_cle"):  # seule l'action « oublier » (valeur vide) est acceptée ici
        if maj.get(oublier):
            maj.pop(oublier)
    enregistrer_parametres(maj)
    return lire_parametres()


@app.post("/api/parametres/tester")
def tester_ia():
    reussi, message = llm.tester()
    return jsonify({"ok": reussi, "message": message})


@app.post("/api/estimation")
def estimation():
    """Fourchette de coût calculée en direct pendant la saisie de la fiche."""
    return jsonify(budget.estimer_cadrage(store.nettoyer_fiche(request.get_json(force=True))))


@app.get("/api/types")
def types():
    return jsonify({k: {"libelle": v["libelle"], "calcul": v["calcul"]} for k, v in TYPES.items()})


if __name__ == "__main__":
    import os
    import socket
    port = int(os.environ.get("PORT", 8765))
    # Le rechargeur relance un processus enfant à chaque modification du code : seul le processus
    # principal vérifie le port et ouvre le navigateur.
    enfant = os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    if not enfant:
        # Sous Windows, un second serveur peut écouter le même port : les requêtes se répartissent alors
        # au hasard entre l'ancien et le nouveau code. On réutilise la plateforme déjà ouverte.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sonde:
            sonde.settimeout(0.5)
            if sonde.connect_ex(("127.0.0.1", port)) == 0:
                print(f"\n  La plateforme tourne déjà sur http://127.0.0.1:{port}\n"
                      "  Pour la redémarrer, fermez d'abord la fenêtre du serveur existant.\n")
                if not os.environ.get("SANS_NAVIGATEUR"):
                    webbrowser.open(f"http://127.0.0.1:{port}")
                raise SystemExit(0)
        PROJETS_DIR.mkdir(exist_ok=True)
        if not os.environ.get("SANS_NAVIGATEUR"):
            Timer(2.5, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
        print(f"\n  Plateforme Datatym : http://127.0.0.1:{port}"
              "\n  Le serveur se recharge tout seul quand le code est mis à jour.\n")
    # use_reloader : toute modification d'un fichier Python relance le serveur, plus besoin de relancer lancer.bat
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True, use_reloader=True)
