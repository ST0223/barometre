"""Pré-test du questionnaire : entretiens tests, durée réelle, problèmes relevés question par question et suite donnée,
avant la validation définitive et le déploiement. Grille d'observation (Excel) et rapport de pré-test (Word).
"""
import math
import shutil

from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation

from .charte import chiffres, p, rendre_modele, section, tableau
from .config import auteur_fichiers
from .formulaires import _feuille
from .outils import aujourdhui, date_courte, nombre
from .store import dossier

TYPES = {
    "comprehension": "Question mal comprise",
    "formulation": "Formulation à revoir",
    "modalite": "Modalité manquante ou inutile",
    "longueur": "Trop long, fatigue du répondant",
    "filtre": "Filtre ou enchaînement incorrect",
    "sensible": "Question sensible, refus de répondre",
    "technique": "Problème dans l'outil de collecte",
}
ACTIONS = {
    "reformuler": "Reformuler la question",
    "ajouter_modalite": "Ajouter ou retirer une modalité",
    "supprimer": "Supprimer la question",
    "deplacer": "Revoir l'ordre des questions",
    "filtre": "Corriger le filtre",
    "outil": "Corriger le formulaire",
    "aucune": "Aucune modification",
}
STATUTS = {"a_traiter": "À traiter", "corrige": "Corrigé", "sans_suite": "Sans suite"}
MODES = {"terrain": "Face à face (terrain)", "telephone": "Téléphone", "digital": "En ligne (auto-administré)"}


MENTION_FINALE = "Version finale, après pré-test"
DOSSIER_TESTEE = "questionnaire_pretest"


def donnees(projet):
    return projet.setdefault("pretest", {"entretiens": [], "problemes": [], "conclusion": ""})


def commence(projet):
    d = projet.get("pretest") or {}
    return bool(d.get("entretiens") or d.get("problemes"))


def empreinte(questions):
    """Ce qui change vraiment le questionnaire testé : un simple enregistrement sans modification ne compte pas."""
    return [[q.get(k) for k in ("id", "var", "texte", "type", "modalites", "consigne", "profils", "obligatoire", "conditions", "condition_sur")] for q in questions]


def archiver_version_testee(projet):
    """Garde une copie du questionnaire tel qu'il a été testé, avant la première correction. Une seule fois."""
    d = donnees(projet)
    e = projet["etapes"]["questionnaire"]
    if d.get("version_testee") or not commence(projet):
        return False
    racine = dossier(projet["slug"])
    cible = racine / "versions" / DOSSIER_TESTEE
    copies = []
    for f in e.get("fichiers") or []:
        src = racine / "livrables" / f["fichier"]
        if src.exists():
            cible.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, cible / f["fichier"])
            copies.append({"nom": f["nom"], "fichier": f["fichier"], "type": f["type"]})
    if not copies:
        return False
    d["version_testee"] = {"version": e.get("version") or 1, "date": aujourdhui(), "fichiers": copies}
    return True


def chemin_version_testee(projet, fichier):
    """Fichier archivé, seulement s'il figure dans la liste de la version testée."""
    v = (projet.get("pretest") or {}).get("version_testee") or {}
    if fichier not in {f["fichier"] for f in v.get("fichiers") or []}:
        return None
    return dossier(projet["slug"]) / "versions" / DOSSIER_TESTEE / fichier


def est_final(projet):
    """Validé après un pré-test : un questionnaire validé avant le pré-test ne l'est pas encore."""
    e = projet["etapes"]["questionnaire"]
    return e.get("statut") == "valide" and any(MENTION_FINALE in (m.get("meta") or []) for m in (e.get("docs") or {}).values())


def marquer_final(projet, final):
    """Mention sur la page de garde des documents du questionnaire validé après un pré-test."""
    for m in (projet["etapes"]["questionnaire"].get("docs") or {}).values():
        meta = [x for x in m.get("meta") or [] if x != MENTION_FINALE]
        if final and (projet.get("pretest") or {}).get("entretiens"):
            meta.insert(1 if meta else 0, MENTION_FINALE)
        m["meta"] = meta


def _quest(projet):
    return projet["etapes"]["questionnaire"].get("data") or {}


def enregistrer(projet, maj):
    """Entretiens et problèmes saisis dans l'onglet Pré-test ; les champs inconnus sont ignorés."""
    def num(x):
        try:
            return round(float(str(x).replace(",", ".")), 1) if str(x).strip() else None
        except ValueError:
            return None
    entretiens = [{"date": str(e.get("date") or "")[:10], "profil": str(e.get("profil") or ""),
                   "mode": e.get("mode") if e.get("mode") in MODES else "terrain", "duree": num(e.get("duree")),
                   "enqueteur": str(e.get("enqueteur") or "")[:80], "remarque": str(e.get("remarque") or "")[:500]}
                  for e in maj.get("entretiens") or []]
    problemes = [{"var": str(x.get("var") or ""), "type": x.get("type") if x.get("type") in TYPES else "formulation",
                  "description": str(x.get("description") or "")[:600], "action": x.get("action") if x.get("action") in ACTIONS else "reformuler",
                  "statut": x.get("statut") if x.get("statut") in STATUTS else "a_traiter"}
                 for x in maj.get("problemes") or []]
    d = donnees(projet)
    d.update({"entretiens": entretiens, "problemes": problemes, "conclusion": str(maj.get("conclusion") or "")[:2000]})
    return d


def synthese(projet):
    d = projet.get("pretest") or {}
    q = _quest(projet)
    es, ps = d.get("entretiens") or [], d.get("problemes") or []
    durees = [e["duree"] for e in es if e.get("duree")]
    estimee = math.ceil(max((q.get("duree_terrain") or {0: 0}).values()) or 0) if q else None
    return {"entretiens": len(es), "duree_moyenne": round(sum(durees) / len(durees), 1) if durees else None, "duree_estimee": estimee,
            "problemes": len(ps), "a_traiter": sum(x["statut"] == "a_traiter" for x in ps),
            "corriges": sum(x["statut"] == "corrige" for x in ps), "questions": len({x["var"] for x in ps if x["var"]})}


def _lib_q(projet):
    return {x["var"]: f"{x['num']}. {x['texte']}" for x in _quest(projet).get("questions_plates") or []}


def _profils(projet):
    return {pr["code"]: pr["libelle"] for pr in _quest(projet).get("profils") or []}


def conclusion_auto(projet):
    s = synthese(projet)
    if not s["entretiens"]:
        return "Le pré-test n'a pas encore été réalisé."
    txt = []
    if s["duree_moyenne"] and s["duree_estimee"]:
        ecart = s["duree_moyenne"] - s["duree_estimee"]
        txt.append(f"La durée moyenne observée ({nombre(s['duree_moyenne'], 1)} min) est "
                   + ("conforme à l'estimation" if abs(ecart) <= 2 else ("supérieure de " if ecart > 0 else "inférieure de ")
                      + f"{nombre(abs(ecart), 0)} min à l'estimation") + f" ({s['duree_estimee']} min).")
    if s["a_traiter"]:
        txt.append("Un ajustement reste à apporter" if s["a_traiter"] == 1 else f"{s['a_traiter']} ajustements restent à apporter")
        txt[-1] += " avant la validation définitive du questionnaire."
    elif s["problemes"]:
        txt.append("Tous les problèmes relevés ont été traités : le questionnaire peut être validé et déployé.")
    else:
        txt.append("Aucun problème de compréhension n'a été relevé : le questionnaire peut être validé et déployé.")
    return " ".join(txt)


def docx(chemin, projet):
    d = donnees(projet)
    s = synthese(projet)
    lib, prof = _lib_q(projet), _profils(projet)
    theme = projet["fiche"]["theme"]
    secs = [
        section("objet", "1. Objet du pré-test", [
            p("Le pré-test consiste à administrer le questionnaire à quelques répondants de la cible, dans les conditions réelles de "
              "l'enquête, avant son déploiement. Il vérifie que les questions sont comprises, que les modalités couvrent les réponses "
              "données, que les filtres s'enchaînent correctement et que la durée reste raisonnable."),
            chiffres([{"valeur": str(s["entretiens"]), "libelle": "entretiens tests"},
                      {"valeur": f"{nombre(s['duree_moyenne'], 1)} min" if s["duree_moyenne"] else "–", "libelle": "durée moyenne observée"},
                      {"valeur": str(s["problemes"]), "libelle": "problèmes relevés"},
                      {"valeur": str(s["a_traiter"]), "libelle": "ajustements à faire"}]),
        ]),
        section("entretiens", "2. Entretiens réalisés", [
            tableau(["Date", "Profil", "Mode", "Durée", "Enquêteur", "Remarque générale"],
                    [[date_courte(e["date"]) if e["date"] else "", prof.get(e["profil"], e["profil"]), MODES[e["mode"]],
                      f"{nombre(e['duree'], 1)} min" if e.get("duree") else "", e["enqueteur"], e["remarque"]] for e in d["entretiens"]]
                    or [["", "", "", "", "", "Aucun entretien saisi"]], "Entretiens du pré-test", [0.8, 1.2, 1.1, 0.6, 1, 2.6], 9),
        ]),
        section("problemes", "3. Problèmes relevés et suite donnée", [
            tableau(["Question", "Problème", "Observation", "Action", "Statut"],
                    [[lib.get(x["var"], "Questionnaire entier"), TYPES[x["type"]], x["description"], ACTIONS[x["action"]], STATUTS[x["statut"]]]
                     for x in d["problemes"]] or [["", "", "Aucun problème relevé", "", ""]],
                    "Problèmes relevés pendant le pré-test", [2.2, 1.2, 2.2, 1.2, 0.7], 9),
        ]),
        section("conclusion", "4. Conclusion", [p(d.get("conclusion") or conclusion_auto(projet))]),
    ]
    modele = {"titre": theme, "sous_titre": "Rapport de pré-test du questionnaire", "surtitre": "",
              "meta": [f"Version du {aujourdhui()}", "Auteur : DATATYM"], "en_tete": f"{theme} — Rapport de pré-test",
              "pied": "Document interne — Confidentiel", "sections": secs}
    return rendre_modele(modele, chemin)


def grille_xlsx(chemin, projet):
    """Grille d'observation à remplir pendant chaque entretien test, et feuille de suivi des entretiens."""
    q = _quest(projet)
    wb = Workbook()
    ws = wb.active
    ws.title = "Grille d'observation"
    cols = ["N°", "Question", "Posée à", "Comprise ?", "Hésitation, reformulation demandée", "Réponse hors des modalités", "Remarque"]
    prof = _profils(projet)
    lignes = [[x["num"], x["texte"], ", ".join(prof.get(c, c) for c in x.get("profils") or []) or "Tous", "", "", "", ""]
              for x in q.get("questions_plates") or []]
    _feuille(ws, cols, lignes, {"Question": 70, "Posée à": 20, "Comprise ?": 14, "Hésitation, reformulation demandée": 24,
                                "Réponse hors des modalités": 24, "Remarque": 40})
    dv = DataValidation(type="list", formula1='"Oui,Partiellement,Non"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"D2:D{max(len(lignes) + 1, 2)}")
    ws2 = wb.create_sheet("Entretiens")
    _feuille(ws2, ["N°", "Date", "Profil du répondant", "Mode", "Heure de début", "Heure de fin", "Durée (min)", "Enquêteur", "Remarque générale"],
             [[k, "", "", "", "", "", "", "", ""] for k in range(1, 11)], {"Profil du répondant": 24, "Remarque générale": 50})
    ws3 = wb.create_sheet("Consignes")
    _feuille(ws3, ["Consigne"], [[t] for t in [
        "Réaliser 5 à 10 entretiens auprès de répondants de la cible, en couvrant chaque profil, dans les conditions réelles (même outil, même mode).",
        "Lire chaque question mot pour mot et noter toute hésitation, demande de répétition ou reformulation.",
        "Noter mot pour mot les réponses qui n'entrent dans aucune modalité : elles signalent une modalité manquante.",
        "Chronométrer l'entretien du consentement à la dernière question.",
        "En fin d'entretien, demander au répondant quelles questions lui ont paru difficiles, longues ou gênantes.",
        "Reporter les problèmes dans l'onglet Pré-test de la plateforme, avec l'action retenue, puis corriger le questionnaire avant de le valider.",
    ]], {"Consigne": 120})
    wb.properties.creator = wb.properties.lastModifiedBy = auteur_fichiers()
    wb.save(chemin)
    return chemin


def pour_methodologie(projet):
    """Phrase de la note méthodologique, si le pré-test a été réalisé."""
    s = synthese(projet)
    if not s["entretiens"]:
        return None
    n = len({x["var"] for x in (projet.get("pretest") or {}).get("problemes") or [] if x["statut"] == "corrige" and x["var"]})
    return (f"**Pré-test :** {s['entretiens']} entretien(s) test(s) dans les conditions réelles"
            + (f", durée moyenne observée de {nombre(s['duree_moyenne'], 1)} minutes" if s["duree_moyenne"] else "")
            + (f" ; {n} question(s) ajustée(s) à l'issue du pré-test." if n else " ; aucune question n'a nécessité d'ajustement."))
