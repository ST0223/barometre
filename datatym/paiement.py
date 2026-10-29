"""État de paiement des enquêteurs en fin de collecte : questionnaires validés × tarif, plus les forfaits journaliers
du budget (transport, communication) pour chaque jour travaillé, avec le moyen et le numéro de paiement donnés par les RH.
"""
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font

from .etapes import collecte
from .formulaires import _feuille
from .config import auteur_fichiers


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
