"""État de paiement des enquêteurs en fin de collecte : questionnaires validés × tarif, plus les forfaits journaliers
du budget (transport, communication) pour chaque jour travaillé, avec le moyen et le numéro de paiement donnés par les RH.
"""
import math

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font

from .etapes import collecte
from .formulaires import _feuille
from .config import auteur_fichiers
from .outils import fcfa, nombre


def calculer(projet):
    ech = projet["etapes"]["echantillonnage"].get("data") or {}
    quest = projet["etapes"]["questionnaire"].get("data") or {}
    if not ech.get("enqueteurs") or not quest:
        return None
    b = ech.get("budget") or {}
    u = {c["cle"]: c["valeur"] for c in b.get("couts") or []}
    postes = {l["cle"] for l in b.get("lignes") or []}
    tarif = u.get("remu_questionnaire", 0) if "remu_questionnaire" in postes else 0
    forfait = sum(u.get(k, 0) for k in ("transport_jour", "communication_jour") if k in postes)

    df = collecte.lire(projet)
    par_code, jours_code = {}, {}
    if df is not None and not df.empty:
        v_enq, _, _ = collecte.variables_cles(quest)
        controle = projet["etapes"]["collecte"]["data"].get("controle_qualite", True)
        v = collecte.valides(df, quest) if controle else df
        col = "enqueteur" if "enqueteur" in v else v_enq
        if col in v:
            codes = v[col].fillna("").astype(str).str.strip().str.lower()
            par_code = codes.value_counts().to_dict()
            if "start" in v:
                dates = v["start"].map(collecte._date)
                jours_code = pd.DataFrame({"c": codes, "d": dates}).dropna().groupby("c")["d"].nunique().to_dict()
    lignes = []
    for m, role in [(m, "Titulaire") for m in ech["enqueteurs"]] + [(r, "Réserve") for r in ech.get("reserves") or []]:
        c = m.get("contact") or {}
        nb = int(par_code.get(m["code"].lower(), 0))
        jours = int(jours_code.get(m["code"].lower(), 0))
        if role == "Réserve" and not nb:
            continue  # réserve jamais mobilisée : rien à payer
        lignes.append({
            "id": m["code"], "nom": c.get("nom") or m["nom"], "prenom": c.get("prenom", ""), "pays": m["zone"], "role": role,
            "valides": nb, "tarif": tarif, "montant_q": nb * tarif, "jours": jours, "forfait": forfait, "montant_j": jours * forfait,
            "total": nb * tarif + jours * forfait, "moyen": c.get("paiement", ""), "numero": c.get("num_paiement") or c.get("telephone", ""),
        })
    return {"lignes": lignes, "tarif": tarif, "forfait": forfait, "total": sum(l["total"] for l in lignes),
            "a_completer": [l["id"] for l in lignes if l["total"] and not (l["moyen"] and l["numero"])]}


def situation(projet):
    """Montant engagé à date, poste par poste, et reste disponible : estimation tirée du budget et de l'avancement de la
    collecte. Les enquêteurs n'étant payés qu'en fin de collecte, sur les questionnaires validés, le montant reste à ajuster."""
    ech = projet["etapes"]["echantillonnage"].get("data") or {}
    b = ech.get("budget")
    s = (projet["etapes"]["collecte"].get("data") or {}).get("stats")
    if not b or not s:
        return None
    h = b["hypotheses"]
    jour = max(min(s["jour_index"], s["nb_jours"]), 0)          # jours de collecte écoulés
    valides = s["realise"]
    commencee, finie = jour > 0, jour >= s["nb_jours"]
    rapport_fait = projet["etapes"]["rapport"]["statut"] == "valide"
    # jours réellement travaillés par enquêteur quand les réponses portent son identifiant, sinon équipe complète × jours écoulés
    etat = calculer(projet) if valides else None
    jours_trav = sum(l["jours"] for l in (etat or {}).get("lignes", []))
    if not jours_trav:
        jours_trav = b["nb_enqueteurs"] * jour
    jf = h.get("jours_formation", 1)
    lignes = []
    for l in b["lignes"]:
        cle, u, prevu = l["cle"], l["unitaire"], l["montant"]
        if cle == "remu_questionnaire":
            engage, base = valides * u, f"{valides} questionnaires validés × {fcfa(u)} (payés en fin de collecte)"
        elif cle in ("transport_jour", "communication_jour"):
            engage, base = jours_trav * u, f"{jours_trav} jours d'enquêteur travaillés × {fcfa(u)}"
        elif cle in ("formation_enqueteur", "formation_zone"):
            engage, base = (prevu, "formation réalisée") if commencee else (0, "formation à venir")
        elif cle == "supervision_jour":
            part = (jour + jf) / (s["nb_jours"] + jf) if commencee else 0
            engage, base = prevu * part, f"{jour} jours de collecte écoulés sur {s['nb_jours']}"
        elif cle == "controle_rappel":
            n = math.ceil(valides * h.get("part_rappels", 10) / 100)
            engage, base = n * u, f"{n} rappels ({nombre(h.get('part_rappels', 10), 0)} % des questionnaires validés)"
        elif cle == "analyse_jour":
            engage, base = (prevu, "rapport validé") if rapport_fait else (0, "après la collecte")
        else:  # outils, conception et coordination, forfaits ajoutés : engagés avant le terrain
            engage, base = prevu, "engagé avant la collecte"
        lignes.append({"cle": cle, "poste": l["poste"], "prevu": prevu, "engage": round(engage), "reste": round(prevu - engage), "base": base})
    imp = b["imprevus"]
    lignes.append({"cle": "imprevus", "poste": "Imprévus", "prevu": imp, "engage": 0, "reste": imp, "base": "provision non utilisée"})
    engage = sum(l["engage"] for l in lignes)
    a_payer = sum(l["engage"] for l in lignes if l["cle"] in ("remu_questionnaire", "transport_jour", "communication_jour"))
    # projection en fin de collecte au rythme actuel : les forfaits journaliers courent jusqu'au bout, la rémunération suit les validés
    tarif = next((l["unitaire"] for l in b["lignes"] if l["cle"] == "remu_questionnaire"), 0)
    proj_valides = min(s["objectif"], round(valides / jour * s["nb_jours"])) if jour and not finie else valides
    proj_total = b["total"] - (s["objectif"] - proj_valides) * tarif * (1 + b["taux_imprevus"] / 100)
    return {"lignes": lignes, "budget": b["total"], "engage": engage, "reste": b["total"] - engage,
            "proj_valides": proj_valides, "proj_total": round(proj_total),
            "proj_par_questionnaire": round(proj_total / proj_valides) if proj_valides else None,
            "prevu_par_questionnaire": round(b["par_questionnaire"]),
            "taux": round(100 * engage / b["total"], 1) if b["total"] else 0, "a_payer_enqueteurs": a_payer,
            "jour": jour, "nb_jours": s["nb_jours"], "valides": valides, "objectif": s["objectif"], "finie": finie,
            # à ce rythme, la rémunération finale suit le nombre de questionnaires validés atteint en fin de collecte
            "remu_si_objectif": next((l["prevu"] for l in lignes if l["cle"] == "remu_questionnaire"), 0)}


def xlsx(chemin, projet):
    etat = calculer(projet)
    if etat is None:
        return None
    wb = Workbook()
    ws = wb.active
    ws.title = "État de paiement"
    cols = ["ID", "Nom", "Prénom", "Pays", "Rôle", "Questionnaires validés", "Tarif (FCFA)", "Montant questionnaires",
            "Jours travaillés", "Forfait par jour", "Montant forfaits", "Total à payer (FCFA)", "Moyen de paiement", "Numéro de paiement"]
    rangs = [[l["id"], l["nom"], l["prenom"], l["pays"], l["role"], l["valides"], l["tarif"], l["montant_q"],
              l["jours"], l["forfait"], l["montant_j"], l["total"], l["moyen"] or "À compléter", l["numero"] or "À compléter"]
             for l in etat["lignes"]]
    tot = ["Total", "", "", "", "", sum(l["valides"] for l in etat["lignes"]), "", sum(l["montant_q"] for l in etat["lignes"]),
           sum(l["jours"] for l in etat["lignes"]), "", sum(l["montant_j"] for l in etat["lignes"]), etat["total"], "", ""]
    _feuille(ws, cols, rangs + [tot], {"Nom": 18, "Prénom": 16, "Pays": 16, "Moyen de paiement": 18, "Numéro de paiement": 20})
    for c in ws[ws.max_row]:
        c.font = Font(bold=True)
    for row in ws.iter_rows(min_row=2, min_col=6, max_col=12):
        for c in row:
            c.number_format = "# ##0"
    ws2 = wb.create_sheet("Règles")
    _feuille(ws2, ["Règle", "Détail"], [
        ["Questionnaires", "Seuls les questionnaires validés au contrôle qualité sont payés."],
        ["Forfaits", "Transport et communication : par jour avec au moins un questionnaire validé (si ces postes figurent au budget)."],
        ["Réserves", "Une réserve n'apparaît que si elle a été mobilisée (au moins un questionnaire validé)."],
        ["Paiement", "Mobile Money ou virement, sur le moyen et le numéro transmis par les RH."],
    ], {"Règle": 18, "Détail": 90})
    wb.properties.creator = wb.properties.lastModifiedBy = auteur_fichiers()
    wb.save(chemin)
    return chemin
