"""Sorties tabulaires du questionnaire : dictionnaire des variables, XLSForm Kobo, import QuestionPro."""
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .banque import NSP_CODE, TYPES
from .config import MARINE

ENTETE_FILL = PatternFill("solid", fgColor=MARINE)
ENTETE_FONT = Font(bold=True, color="FFFFFF", name="Calibri")


def _feuille(ws, colonnes, lignes, largeurs=None):
    ws.append(colonnes)
    for c in ws[1]:
        c.fill, c.font = ENTETE_FILL, ENTETE_FONT
        c.alignment = Alignment(vertical="center", wrap_text=True)
    for l in lignes:
        ws.append(l)
    for i, col in enumerate(colonnes, 1):
        w = (largeurs or {}).get(col) or min(60, max(10, max((len(str(r[i - 1])) for r in lignes if i - 1 < len(r)), default=10) + 2))
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(vertical="top", wrap_text=True)


def dictionnaire(chemin, quest, cadrage):
    inds = {i["id"]: i for i in cadrage.get("indicateurs", [])}
    lib = {pr["code"]: pr["libelle"] for pr in quest["profils"]}
    wb = Workbook()
    ws = wb.active
    ws.title = "Variables"
    lignes = [["consentement", "Acceptez-vous de participer à cette étude ?", "select_one", "oui = Oui | non = Non", "", "Accueil", "", "Tous"]]
    for q in quest["questions_plates"]:
        mods = " | ".join(f"{m['code']} = {m['label']}" for m in q.get("modalites", []))
        ind = q.get("indicateur") or ""
        lignes.append([q["var"], q["texte"], q["type"], mods, f"{ind} {inds[ind]['libelle']}" if ind in inds else "",
                       q["section"], q.get("condition", ""), ", ".join(lib.get(c, c) for c in q["profils"]) if q.get("profils") else "Tous"])
        if q["type"] == "select_multiple":
            for m in q["modalites"]:
                lignes.append([f"{q['var']}_{m['code']}", f"{q['texte']} — {m['label']}", "binaire (0/1)", "0 = Non cité | 1 = Cité", ind, q["section"], q.get("condition", ""), ""])
            if any(m["code"] == "autre" for m in q["modalites"]):
                lignes.append([f"{q['var']}_autre_txt", f"{q['num']} — Préciser autre", "text", "", ind, q["section"], f"Si Autre coché en {q['num']}", ""])
    for v, l in (("enqueteur", "Enquêteur (copie de A1)"), ("start", "Début de l'entretien"), ("end", "Fin de l'entretien"),
                 ("duree_minutes", "Durée de l'entretien en minutes (calculée)"), ("_submission_time", "Date de soumission")):
        lignes.append([v, l, "automatique", "", "", "Système", "", ""])
    _feuille(ws, ["name", "label", "type", "modalités (code = libellé)", "indicateur rattaché", "section", "condition d'affichage", "profils concernés"],
             lignes, {"label": 60, "modalités (code = libellé)": 55, "condition d'affichage": 30})

    ws2 = wb.create_sheet("Indicateurs")
    l2 = []
    for i in cadrage.get("indicateurs", []):
        if not i.get("actif", True):
            continue
        vars_ = ", ".join(q["var"] for q in quest["questions_plates"] if q.get("indicateur") == i["id"])
        if i["type"] == "indice":
            vars_ = "Composantes : " + ", ".join(i.get("composantes", []))
        l2.append([i["id"], i["libelle"], i.get("definition", ""), TYPES[i["type"]]["libelle"], TYPES[i["type"]]["calcul"], vars_])
    _feuille(ws2, ["code", "indicateur", "définition", "type de mesure", "mode de calcul", "variables"], l2,
             {"définition": 50, "mode de calcul": 70, "indicateur": 40})
    wb.properties.creator = wb.properties.lastModifiedBy = "DATATYM"
    wb.save(chemin)
    return chemin


def xlsform(chemin, projet, quest, enqueteurs=None):
    """Formulaire XLSForm pour KoboToolbox (feuilles survey, choices, settings)."""
    fiche = projet["fiche"]
    survey, choices = [], []
    cols = ["type", "name", "label", "hint", "required", "relevant", "constraint", "constraint_message", "appearance", "calculation"]

    def ligne(**kw):
        survey.append([kw.get(c, "") for c in cols])

    ligne(type="start", name="start")
    ligne(type="end", name="end")
    ligne(type="today", name="today")
    ligne(type="note", name="message", label=quest["consentement"])
    ligne(type="select_one oui_non", name="consentement", label="Acceptez-vous de participer à cette étude ?", required="yes")
    ligne(type="note", name="consentement_fin", label="Merci de votre attention. L'entretien s'arrête ici.", relevant="${consentement} = 'non'")
    choices.extend([["oui_non", "oui", "Oui"], ["oui_non", "non", "Non"]])

    var_profil = next((q["var"] for q in quest["questions_plates"] if q["id"] == "id_profil"), "a3")
    for s in quest["sections"]:
        rel = "${consentement} = 'oui'"
        if s["lettre"] != "A":
            rel += f" and ${{{var_profil}}} != 'autre_hors'"
        ligne(type="begin_group", name=f"section_{s['lettre'].lower()}", label=f"{s['lettre']}. {s['titre']}", relevant=rel, appearance="field-list" if False else "")
        for q in s["ids"]:
            liste_nom = f"l_{q['var']}"
            if q["type"] in ("select_one", "select_multiple"):
                t = f"{q['type']} {liste_nom}"
                mods = q["modalites"]
                if q["id"] == "id_enqueteur" and enqueteurs:
                    mods = [{"code": e["code"], "label": e["nom"]} for e in enqueteurs]
                for m in mods:
                    choices.append([liste_nom, m["code"], m["label"]])
            elif q["type"] == "email":
                t = "text"
            else:
                t = q["type"]
            contrainte, msg = "", ""
            if q.get("max_choix"):
                contrainte, msg = f"count-selected(.) <= {q['max_choix']}", f"{q['max_choix']} réponses au maximum."
            if q["type"] == "email":
                contrainte, msg = "regex(., '^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$')", "Adresse e-mail invalide."
            if any(m["code"] == NSP_CODE for m in q.get("modalites", [])) and q["type"] == "select_multiple":
                contrainte = (contrainte + " and " if contrainte else "") + f"not(selected(., '{NSP_CODE}') and count-selected(.) > 1)"
            ligne(type=t, name=q["var"], label=q["texte"], hint=q.get("consigne", "") if q.get("terrain_seul") else "",
                  required="yes" if q.get("obligatoire", True) else "", relevant=q.get("relevant", ""),
                  constraint=contrainte, constraint_message=msg)
            if q["type"] == "select_multiple" and any(m["code"] == "autre" for m in q["modalites"]):
                ligne(type="text", name=f"{q['var']}_autre_txt", label="Préciser autre", required="yes",
                      relevant=f"selected(${{{q['var']}}}, 'autre')")
            if q["id"] == "id_profil":
                ligne(type="note", name="hors_cible", label="Ce baromètre ne concerne pas votre fonction. Merci de votre attention.",
                      relevant=f"${{{q['var']}}} = 'autre_hors'")
        ligne(type="end_group", name="")
    var_enq = next((q["var"] for q in quest["questions_plates"] if q["id"] == "id_enqueteur"), "a1")
    ligne(type="calculate", name="enqueteur", calculation=f"${{{var_enq}}}")
    ligne(type="calculate", name="duree_minutes", calculation="round((decimal-date-time(${end}) - decimal-date-time(${start})) * 1440, 1)")
    ligne(type="note", name="merci", label="Merci pour votre participation.", relevant="${consentement} = 'oui'")

    wb = Workbook()
    ws = wb.active
    ws.title = "survey"
    _feuille(ws, cols, survey, {"label": 60, "relevant": 40, "constraint": 35})
    _feuille(wb.create_sheet("choices"), ["list_name", "name", "label"], choices, {"label": 45})
    from .banque import slug
    _feuille(wb.create_sheet("settings"), ["form_title", "form_id", "version", "default_language"],
             [[f"Baromètre {fiche['theme']}", "barometre_" + slug(fiche["theme"], maxi=30), projet["etapes"]["questionnaire"].get("version") or 1, "French (fr)"]])
    wb.properties.creator = wb.properties.lastModifiedBy = "DATATYM"
    wb.save(chemin)
    return chemin


def questionpro(chemin, quest):
    """Fichier texte pour l'import en masse de QuestionPro : une question par paragraphe, une réponse par ligne."""
    lignes = [quest["consentement"], "", "Acceptez-vous de participer à cette étude ?", "Oui", "Non", ""]
    for s in quest["sections"]:
        for q in s["ids"]:
            if q.get("terrain_seul"):
                continue
            entete = f"{q['num']}. {q['texte']}"
            if q["type"] == "select_multiple":
                entete += f" (plusieurs réponses possibles, {q.get('max_choix', 3)} maximum)"
            lignes.append(entete)
            for m in q.get("modalites", []):
                lignes.append(m["label"])
            lignes.append("")
    with open(chemin, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lignes))
    return chemin
