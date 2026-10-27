"""Moteur de la chaîne de production : génération, édition, validation, propagation, exports."""
import shutil
import subprocess
from pathlib import Path

from . import budget, formulaires, formation, store
from .banque import nom_court, profils_depuis_cible
from .charte import rendre_modele
from .etapes import cadrage, collecte, echantillonnage, methodologie, questionnaire, rapport, suivi
from .outils import propre
from .store import CLES, ETAPES

MODULES = {"cadrage": cadrage, "questionnaire": questionnaire, "echantillonnage": echantillonnage,
           "methodologie": methodologie, "collecte": collecte, "suivi": suivi, "rapport": rapport}
LIBELLES = dict(ETAPES)


class ErreurChaine(Exception):
    pass


# ------------------------------------------------------------------ état
def precedente(cle):
    i = CLES.index(cle)
    return CLES[i - 1] if i else None


def suivantes(cle):
    return CLES[CLES.index(cle) + 1:]


def statut(projet, cle):
    e = projet["etapes"][cle]
    if e["statut"] in ("valide", "brouillon", "obsolete"):
        return e["statut"]
    prev = precedente(cle)
    if prev and projet["etapes"][prev]["statut"] != "valide":
        return "verrouille"
    return "a_generer"


def vue(projet):
    """Projet enrichi pour l'interface."""
    v = dict(projet)
    v["etapes"] = {}
    for cle in CLES:
        e = dict(projet["etapes"][cle])
        e["statut"] = statut(projet, cle)
        e["libelle"] = LIBELLES[cle]
        v["etapes"][cle] = e
    v["ordre"] = [{"cle": c, "libelle": l} for c, l in ETAPES]
    return v


def _data(projet, cle):
    return projet["etapes"][cle]["data"]


def _exiger_valide(projet, cle):
    prev = precedente(cle)
    if prev and projet["etapes"][prev]["statut"] != "valide":
        raise ErreurChaine(f"Validez d'abord l'étape « {LIBELLES[prev]} ».")


# ------------------------------------------------------------------ documents
def fusionner(nouveaux, anciens):
    """Conserve les sections rédigées à la main ; les sections calculées sont toujours régénérées."""
    res = {}
    for nom, modele in nouveaux.items():
        ancien = (anciens or {}).get(nom) or {}
        par_id = {s["id"]: s for s in ancien.get("sections", [])}
        sections = []
        for s in modele["sections"]:
            a = par_id.get(s["id"])
            if a and a.get("manuel") and s.get("source") != "auto":
                sections.append(a)
            else:
                sections.append(s)
        if ancien.get("entete_manuel"):
            for k in ("titre", "sous_titre", "surtitre", "meta"):
                modele[k] = ancien.get(k, modele.get(k))
            modele["entete_manuel"] = True
        modele["sections"] = sections
        res[nom] = modele
    return res


AUTEUR = "DATATYM"
# Documents destinés à l'extérieur : pas de mention « document interne »
EXTERNES = {"note_recrutement", "questionnaire_digital"}


def page_de_garde(projet, docs, cle):
    """Titre = thème du baromètre, sous-titre = type de document, auteur DATATYM."""
    types = {nom: affiche for nom, (_, affiche) in getattr(MODULES[cle], "DOCS", {}).items()}
    for nom, m in docs.items():
        if m.get("entete_manuel"):
            continue
        if not (cle == "rapport" and m.get("titre") and m["titre"] != projet["fiche"]["theme"]):
            m["titre"] = projet["fiche"]["theme"]
        if not (cle == "rapport" and m.get("sous_titre")):
            m["sous_titre"] = types.get(nom, m.get("sous_titre", ""))
        # la mention de confidentialité figure en note de bas de page, pas sur la couverture
        m["surtitre"] = ""
        m["pied"] = "Datatym" if nom in EXTERNES else "Document interne — Confidentiel"
        # pas de rappel d'échantillon ni de cible en page de garde : version, dates et auteur seulement
        meta = [x for x in m.get("meta", []) if x.startswith(("Version", "Collecte du", "Date limite", "Candidature"))]
        m["meta"] = meta + [f"Auteur : {AUTEUR}"]
        m["auteur"] = AUTEUR
        m["en_tete"] = f"{m['titre']} — {m['sous_titre']}"
    return docs


def construire_docs(projet, cle):
    return page_de_garde(projet, _construire_docs(projet, cle), cle)


def _construire_docs(projet, cle):
    d = _data(projet, cle)
    if cle == "cadrage":
        return cadrage.construire_docs(projet, d)
    if cle == "questionnaire":
        return questionnaire.construire_docs(projet, d, _data(projet, "cadrage"))
    if cle == "echantillonnage":
        return echantillonnage.construire_docs(projet, d, _data(projet, "questionnaire"))
    if cle == "methodologie":
        return methodologie.construire_docs(projet, d, _data(projet, "cadrage"), _data(projet, "questionnaire"), _data(projet, "echantillonnage"))
    if cle == "suivi":
        return suivi.construire_docs(projet, d, _data(projet, "collecte").get("stats"))
    if cle == "rapport":
        return rapport.construire_docs(projet, d, _data(projet, "echantillonnage"))
    return {}


def exporter(projet, cle):
    """Écrit les fichiers de l'étape dans livrables/ et renvoie leur liste."""
    e = projet["etapes"][cle]
    v = e["version"] or 1
    out = store.dossier(projet["slug"]) / "livrables"
    out.mkdir(parents=True, exist_ok=True)
    fichiers = []

    def ajout(nom_affiche, nom_fichier, doc=None):
        fichiers.append({"nom": nom_affiche, "fichier": nom_fichier, "type": Path(nom_fichier).suffix[1:], "doc": doc})

    mod = MODULES[cle]
    for nom, (code, affiche) in getattr(mod, "DOCS", {}).items():
        if nom in e["docs"]:
            f = store.nom_fichier(projet, code, v, "docx")
            rendre_modele(e["docs"][nom], out / f)
            ajout(affiche, f, nom)
    if cle == "questionnaire":
        c = _data(projet, "cadrage")
        f = store.nom_fichier(projet, "Dictionnaire", v, "xlsx")
        formulaires.dictionnaire(out / f, e["data"], c)
        ajout("Dictionnaire des indicateurs et des variables", f)
        f = f"{nom_court(projet['fiche']['theme'])}.xlsx"  # nom court, identique au form_id du formulaire
        formulaires.xlsform(out / f, projet, e["data"], c)
        ajout("Formulaire XLSForm (KoboToolbox)", f)
        # fichier média à joindre au formulaire dans Kobo (nom imposé par le XLSForm)
        formulaires.liste_enqueteurs(out / formulaires.FICHIER_ENQUETEURS, e["data"])
        ajout("Liste des enquêteurs pour Kobo (Enq1, Enq2…)", formulaires.FICHIER_ENQUETEURS)
        f = store.nom_fichier(projet, "Import_QuestionPro", v, "txt")
        formulaires.questionpro(out / f, e["data"])
        ajout("Fichier d'import QuestionPro", f)
    if cle == "echantillonnage":
        q = _data(projet, "questionnaire")
        f = store.nom_fichier(projet, "Calendrier_Quotas", v, "xlsx")
        echantillonnage.calendrier_xlsx(out / f, e["data"])
        ajout("Calendrier et quotas détaillés", f)
        f = store.nom_fichier(projet, "Formation_Enqueteurs", v, "pptx")
        formation.generer_pptx(out / f, projet, _data(projet, "cadrage"), q, e["data"])
        ajout("Présentation de formation des enquêteurs", f)
        formulaires.liste_enqueteurs(out / formulaires.FICHIER_ENQUETEURS, q, e["data"]["enqueteurs"])
        ajout("Liste des enquêteurs pour Kobo (noms définitifs)", formulaires.FICHIER_ENQUETEURS)
    if cle == "collecte" and collecte.chemin_donnees(projet).exists():
        f = store.nom_fichier(projet, "Donnees_Collecte", v, "csv")
        shutil.copy(collecte.chemin_donnees(projet), out / f)
        ajout("Base des soumissions (CSV)", f)
    e["fichiers"] = fichiers
    nettoyer_livrables(projet)
    return fichiers


def nettoyer_livrables(projet):
    """Retire de livrables/ les fichiers générés qui ne sont plus d'actualité (ancien thème, ancienne version).
    Les versions validées restent archivées dans versions/ ; seuls les fichiers produits par la plateforme sont visés."""
    out = store.dossier(projet["slug"]) / "livrables"
    courants = {f["fichier"] for c in CLES for f in projet["etapes"][c].get("fichiers") or []}
    for f in out.glob("*"):
        genere = f.name.startswith("Barometre_") or (f.name.startswith("baro_") and f.suffix == ".xlsx") or f.name == formulaires.FICHIER_ENQUETEURS
        actuel = f.name in courants or (f.suffix == ".pdf" and f.with_suffix(".docx").name in courants)
        if f.is_file() and genere and not actuel:
            try:
                f.unlink()
            except OSError:
                pass  # fichier ouvert dans Word : il partira au prochain export


def _apres_maj(projet, cle, nouveaux_docs=True):
    e = projet["etapes"][cle]
    if nouveaux_docs:
        e["docs"] = fusionner(construire_docs(projet, cle), e.get("docs"))
    e["data"] = propre(e["data"])
    e["maj"] = store.maintenant()
    exporter(projet, cle)
    store.sauver(projet)


# ------------------------------------------------------------------ actions
def generer(projet, cle):
    _exiger_valide(projet, cle)
    e = projet["etapes"][cle]
    if e["statut"] == "valide":
        raise ErreurChaine("Étape validée : rouvrez-la pour la régénérer.")
    prec = e.get("data") or {}
    if cle == "cadrage":
        if prec:
            # la cible a pu changer dans la fiche : on garde le niveau déjà choisi pour chaque profil
            niveaux = {pr["code"]: pr["niveau"] for pr in prec.get("profils", [])}
            prec["profils"] = [{**pr, "niveau": niveaux.get(pr["code"], pr["niveau"])} for pr in profils_depuis_cible(projet["fiche"]["cible"])]
            prec, nouveau_domaine = cadrage.actualiser(projet, prec)
            if nouveau_domaine:
                store.journaliser(projet, f"Nouveau thème : indicateurs du domaine « {prec['domaine']} » proposés à la place des précédents.")
            prec["points_a_valider"] = cadrage.generer_points(projet["fiche"])
            e["data"] = cadrage.normaliser(prec)
        else:
            e["data"] = cadrage.generer(projet)
        # fourchette figée à la génération : c'est la référence annoncée au dirigeant
        e["data"]["estimation"] = budget.estimer_cadrage(projet["fiche"])
    elif cle == "questionnaire":
        e["data"] = questionnaire.generer(projet, _data(projet, "cadrage"), prec)
    elif cle == "echantillonnage":
        e["data"] = echantillonnage.generer(projet, _data(projet, "questionnaire"), prec)
    elif cle == "methodologie":
        e["data"] = methodologie.generer(projet, prec)
    elif cle == "collecte":
        e["data"] = collecte.generer(projet, prec)
        e["data"]["stats"] = collecte.tableau_de_bord(projet, _data(projet, "questionnaire"), _data(projet, "echantillonnage"))
    elif cle == "suivi":
        e["data"] = suivi.generer(projet, prec)
    elif cle == "rapport":
        e["data"] = rapport.generer(projet, _data(projet, "cadrage"), _data(projet, "questionnaire"), _data(projet, "echantillonnage"), prec)
    e["version"] = e["version"] or 1
    e["statut"] = "brouillon"
    store.journaliser(projet, f"« {LIBELLES[cle]} » : version {e['version']} générée.")
    _apres_maj(projet, cle)
    return projet


def regenerer_texte(projet, cle):
    """Repart de zéro pour l'étape (abandonne les rédactions manuelles)."""
    e = projet["etapes"][cle]
    if e["statut"] == "valide":
        raise ErreurChaine("Étape validée : rouvrez-la d'abord.")
    e["docs"] = {}
    if cle == "cadrage":
        e["data"] = {}
    return generer(projet, cle)


def _editable(projet, cle):
    s = statut(projet, cle)
    if s == "valide":
        raise ErreurChaine("Étape validée : rouvrez-la pour la modifier.")
    if s in ("verrouille", "a_generer"):
        raise ErreurChaine("Générez d'abord cette étape.")


def maj_data(projet, cle, maj):
    _editable(projet, cle)
    e = projet["etapes"][cle]
    d = e["data"]
    if cle == "cadrage":
        for k in ("indicateurs", "profils"):
            if k in maj:
                d[k] = maj[k]
        e["data"] = cadrage.normaliser(d)
    elif cle == "questionnaire":
        if "sections" in maj:
            d["sections"] = maj["sections"]
        if "consentement" in maj:
            d["consentement_modifie"] = maj["consentement"]
        e["data"] = questionnaire.normaliser(projet, d)
    elif cle == "echantillonnage":
        for k in ("params", "recrutement"):
            if k in maj:
                d[k] = maj[k]
        e["data"] = echantillonnage.normaliser(projet, _data(projet, "questionnaire"), d)
    elif cle == "methodologie":
        d.update({k: v for k, v in maj.items() if k in ("logiciel", "limites")})
    elif cle == "collecte":
        if "controle_qualite" in maj:
            d["controle_qualite"] = bool(maj["controle_qualite"])
            d["stats"] = collecte.tableau_de_bord(projet, _data(projet, "questionnaire"), _data(projet, "echantillonnage"))
    elif cle == "suivi":
        d.update({k: v for k, v in maj.items() if k in ("observations", "recommandations", "depenses")})
    elif cle == "rapport":
        d.update({k: v for k, v in maj.items() if k in ("titre", "sous_titre")})
    _marquer_aval(projet, cle)
    _apres_maj(projet, cle)
    return projet


def maj_doc(projet, cle, nom, modele):
    _editable(projet, cle)
    e = projet["etapes"][cle]
    ancien = e["docs"].get(nom, {})
    anciens = {s["id"]: s for s in ancien.get("sections", [])}
    for s in modele.get("sections", []):
        a = anciens.get(s["id"])
        if a is not None and s.get("source") != "auto" and (s.get("blocs") != a.get("blocs") or s.get("titre") != a.get("titre")):
            s["manuel"] = True
    if any(modele.get(k) != ancien.get(k) for k in ("titre", "sous_titre", "surtitre")):
        modele["entete_manuel"] = True
    e["docs"][nom] = modele
    store.journaliser(projet, f"« {LIBELLES[cle]} » : document modifié.")
    _apres_maj(projet, cle, nouveaux_docs=False)
    return projet


def valider(projet, cle):
    s = statut(projet, cle)
    if s == "valide":
        return projet
    if s == "obsolete":
        raise ErreurChaine("Une étape en amont a changé : régénérez cette étape avant de la valider.")
    if s != "brouillon":
        raise ErreurChaine("Rien à valider pour l'instant.")
    _exiger_valide(projet, cle)
    e = projet["etapes"][cle]
    exporter(projet, cle)
    archive = store.dossier(projet["slug"]) / "versions" / f"{cle}_v{e['version']}"
    archive.mkdir(parents=True, exist_ok=True)
    for f in e["fichiers"]:
        src = store.dossier(projet["slug"]) / "livrables" / f["fichier"]
        if src.exists():
            shutil.copy(src, archive / f["fichier"])
    e["statut"] = "valide"
    e["valide_le"] = store.maintenant()
    store.journaliser(projet, f"« {LIBELLES[cle]} » : version {e['version']} validée et archivée.")
    store.sauver(projet)
    return projet


def rouvrir(projet, cle):
    e = projet["etapes"][cle]
    if e["statut"] != "valide":
        return projet
    e["statut"] = "brouillon"
    e["version"] += 1
    _marquer_aval(projet, cle)
    store.journaliser(projet, f"« {LIBELLES[cle]} » : rouverte pour correction (version {e['version']}). Les étapes suivantes sont à mettre à jour.")
    _apres_maj(projet, cle, nouveaux_docs=False)
    return projet


def _marquer_aval(projet, cle):
    for c in suivantes(cle):
        e = projet["etapes"][c]
        if e["statut"] in ("valide", "brouillon"):
            if e["statut"] == "valide":
                e["version"] += 1
            e["statut"] = "obsolete"


def maj_fiche(projet, fiche):
    projet["fiche"] = store.nettoyer_fiche({**projet["fiche"], **fiche})
    for c in CLES:
        e = projet["etapes"][c]
        if e["statut"] in ("valide", "brouillon"):
            if e["statut"] == "valide":
                e["version"] += 1
            e["statut"] = "obsolete"
    store.journaliser(projet, "Fiche d'entrée modifiée : les documents existants sont à mettre à jour.")
    store.sauver(projet)
    return projet


def rafraichir_collecte(projet):
    e = projet["etapes"]["collecte"]
    e["data"]["stats"] = propre(collecte.tableau_de_bord(projet, _data(projet, "questionnaire"), _data(projet, "echantillonnage")))
    e["maj"] = store.maintenant()
    if e["statut"] == "valide":
        _marquer_aval(projet, "collecte")
    exporter(projet, "collecte")
    store.sauver(projet)
    return e["data"]["stats"]


# ------------------------------------------------------------------ PDF
def vers_pdf(chemin_docx):
    """Convertit un .docx en PDF avec Microsoft Word (ou LibreOffice s'il est installé)."""
    src = Path(chemin_docx).resolve()
    pdf = src.with_suffix(".pdf")
    if pdf.exists() and pdf.stat().st_mtime >= src.stat().st_mtime:
        return pdf
    script = (
        "$ErrorActionPreference='Stop';"
        "$w=New-Object -ComObject Word.Application;$w.Visible=$false;$w.DisplayAlerts=0;"
        f"try{{$d=$w.Documents.Open('{src}',$false,$true);$d.Fields.Update()|Out-Null;"
        "foreach($t in $d.TablesOfContents){$t.Update()};"
        f"$d.SaveAs([ref]'{pdf}',[ref]17);$d.Close([ref]0)}}finally{{$w.Quit()}}"
    )
    try:
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], check=True,
                       capture_output=True, timeout=180)
    except (subprocess.SubprocessError, FileNotFoundError):
        soffice = shutil.which("soffice") or shutil.which("libreoffice")
        if not soffice:
            raise ErreurChaine("Export PDF impossible : Microsoft Word ou LibreOffice est requis.")
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(src.parent), str(src)], check=True, timeout=180)
    if not pdf.exists():
        raise ErreurChaine("La conversion PDF a échoué.")
    return pdf


# ------------------------------------------------------------------ clôture
def chemin_archive(projet):
    return store.dossier(projet["slug"]) / "archive" / store.nom_fichier(projet, "Dossier_complet", 1, "zip").replace("_v1.zip", ".zip")


def historique_texte(projet, archives=()):
    """Historique de l'archive : la liste des fichiers générés, étape par étape, puis les versions validées archivées."""
    f = projet["fiche"]
    lignes = [f"Historique des fichiers générés — {f['theme']}", f"Archive constituée le {store.maintenant().replace('T', ' à ')}", ""]
    for cle in CLES:
        e = projet["etapes"][cle]
        if not e.get("fichiers"):
            continue
        lignes.append(f"{LIBELLES[cle].upper()} (version {e.get('version') or 1}"
                      + (f", validée le {e['valide_le'].replace('T', ' à ')}" if e.get("valide_le") else "") + ")")
        lignes += [f"  - {x['fichier']}  ({x['nom']})" for x in e["fichiers"]]
        lignes.append("")
    if archives:
        lignes.append("VERSIONS VALIDÉES ARCHIVÉES")
        lignes += [f"  - {a}" for a in archives]
    return "\n".join(lignes) + "\n"


def boucler(projet):
    """Clôt l'étude : tous les fichiers (livrables, versions validées, données) et l'historique dans une archive ZIP."""
    import zipfile
    racine = store.dossier(projet["slug"])
    zf_chemin = chemin_archive(projet)
    zf_chemin.parent.mkdir(parents=True, exist_ok=True)
    rubriques = [("livrables", "1_Livrables"), ("versions", "2_Versions_validees"), ("donnees", "3_Donnees")]
    nb = 0
    with zipfile.ZipFile(zf_chemin, "w", zipfile.ZIP_DEFLATED) as z:
        for dossier_src, dossier_zip in rubriques:
            src = racine / dossier_src
            for f in sorted(src.rglob("*")) if src.exists() else []:
                # données : seule la base des soumissions ; les fichiers techniques (empreinte, réponses brutes) restent sur le poste
                if f.is_file() and not (dossier_src == "donnees" and f.suffix != ".csv"):
                    z.write(f, f"{dossier_zip}/{f.relative_to(src).as_posix()}")
                    nb += 1
        archives = sorted(n for n in z.namelist() if n.startswith("2_Versions_validees/"))
        z.writestr("Historique.txt", historique_texte(projet, archives))
        nb += 1
    projet["cloture"] = {"date": store.maintenant(), "fichier": zf_chemin.name, "taille": zf_chemin.stat().st_size, "nb": nb}
    store.journaliser(projet, f"Étude bouclée : archive {zf_chemin.name} ({nb} fichiers).")
    store.sauver(projet)
    return projet
