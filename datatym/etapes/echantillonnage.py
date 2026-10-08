"""Étape 3 — Plan d'échantillonnage, répartition par enquêteur, calendrier, coûts et note de recrutement."""
import math
from datetime import date, timedelta

from ..banque import decouper, du_barometre, nom_barometre, slug, sont_des_pays
from ..charte import liste, p, section, tableau, chiffres
from ..config import charger_parametres
from ..outils import aujourdhui, date_courte, date_fr, debut_collecte, fcfa, fmt_marge, jours_collecte, nombre, repartir

DOCS = {
    "note_echantillonnage": ("NoteEchantillonnage", "Note d'échantillonnage des enquêteurs"),
    "note_recrutement": ("NoteRecrutement", "Note de recrutement des enquêteurs"),
}

POSTES_DEFAUT = [
    ("Rémunération des enquêteurs", 40), ("Supervision et coordination du terrain", 12), ("Formation et pré-test", 5),
    ("Transport et communication", 15), ("Matériel et licences (tablettes, outil de collecte)", 5),
    ("Traitement, analyse et rapport", 15), ("Imprévus", 8),
]


def params_defaut(projet, quest):
    fiche = projet["fiche"]
    zones = decouper(fiche["zones"])
    return {
        "rendement": 6, "marge": 0.9, "sans_dimanche": True,
        "date_debut": debut_collecte(fiche).isoformat(),
        "poids_zones": {z: 1 for z in zones},
        "poids_profils": {pr["code"]: 1 for pr in quest["profils"]},
        "noms_enqueteurs": [], "nb_enqueteurs_force": None,
        "postes": [{"poste": a, "part": b} for a, b in POSTES_DEFAUT],
    }


def recrutement_defaut(projet, n_enq, jours):
    fiche = projet["fiche"]
    params = charger_parametres()
    return {
        "intitule": f"Enquêteurs et enquêtrices — {nom_barometre(fiche['theme'])}",
        "presentation": params.get("presentation_datatym", ""),
        "mission": (f"Dans le cadre {du_barometre(fiche['theme'])}, Datatym recrute {n_enq} enquêteurs et enquêtrices "
                    f"pour administrer un questionnaire auprès de {fiche['cible']}, dans "
                    f"{'les pays suivants' if sont_des_pays(fiche['zones']) else 'les zones suivantes'} : {', '.join(decouper(fiche['zones']))}. "
                    f"La collecte se déroule sur {len(jours)} jours, du {date_fr(jours[0])} au {date_fr(jours[-1])}, "
                    "précédée d'une journée de formation obligatoire."),
        "taches": [
            "Identifier et contacter les répondants éligibles selon les quotas attribués.",
            "Présenter l'étude, recueillir le consentement et administrer le questionnaire sur smartphone ou tablette.",
            "Saisir les réponses avec rigueur et envoyer les formulaires chaque jour.",
            "Respecter le calendrier, les quotas et les consignes du superviseur.",
            "Signaler sans délai toute difficulté rencontrée sur le terrain.",
        ],
        "experience": "1 an", "diplome": "Bac+3",
        "competences": [
            "Expérience d'enquête quantitative, idéalement auprès d'entreprises ou de professionnels.",
            "Maîtrise d'un outil de collecte mobile (KoboCollect, ODK, QuestionPro ou équivalent).",
            "Aisance relationnelle, sens de l'écoute et présentation soignée.",
            "Rigueur, ponctualité et respect de la confidentialité.",
            "Bonne capacité de communication.",
            "Parler et lire couramment le français ; la pratique d'une langue locale est un atout.",
        ],
        "dossier": ["CV à jour", "Lettre de motivation", "Copie du dernier diplôme",
                    "Références de missions d'enquête antérieures (facultatif, constituent un atout)"],
        "date_limite": (jours[0] - timedelta(days=10)).isoformat(),
        "contact": params.get("contact_recrutement", ""),
    }


def calculer(projet, quest, params, recrutement=None):
    fiche = projet["fiche"]
    n = fiche["taille"]
    zones = [z for z in params["poids_zones"]] or decouper(fiche["zones"])
    profils = quest["profils"]
    debut = date.fromisoformat(params["date_debut"])
    jours = jours_collecte(debut, fiche["duree"], params.get("sans_dimanche", True))
    rend = max(float(params.get("rendement") or 6), 1)
    marge = min(max(float(params.get("marge") or 0.9), 0.3), 1)
    n_enq = params.get("nb_enqueteurs_force") or math.ceil(n / (rend * len(jours) * marge))
    noms = [x for x in params.get("noms_enqueteurs", []) if str(x).strip()]
    if noms:
        n_enq = len(noms)
    n_enq = max(int(n_enq), len(zones))

    # Quotas zone × profil
    pz = [params["poids_zones"].get(z, 1) for z in zones]
    pp = [params["poids_profils"].get(pr["code"], 1) for pr in profils]
    cellules = repartir(n, [a * b for a in pz for b in pp])
    quotas = {}
    for i, z in enumerate(zones):
        for j, pr in enumerate(profils):
            quotas[(z, pr["code"])] = cellules[i * len(profils) + j]
    tot_zone = {z: sum(quotas[(z, pr["code"])] for pr in profils) for z in zones}

    # Enquêteurs par zone (au moins un par zone)
    enq_zone = repartir(n_enq - len(zones), [tot_zone[z] for z in zones])
    enq_zone = [k + 1 for k in enq_zone]
    enqueteurs, k = [], 0
    for z, nb in zip(zones, enq_zone):
        membres = []
        for _ in range(nb):
            k += 1
            nom = noms[k - 1] if k - 1 < len(noms) else f"Enq{k}"
            membres.append({"code": f"enq{k}", "nom": nom, "zone": z, "par_profil": {}, "objectif": 0})
        for j, pr in enumerate(profils):
            parts = repartir(quotas[(z, pr["code"])], [1] * nb)
            parts = parts[j % nb:] + parts[:j % nb]  # rotation pour équilibrer
            for m, q in zip(membres, parts):
                m["par_profil"][pr["code"]] = q
        for m in membres:
            m["objectif"] = sum(m["par_profil"].values())
            # séquence de profils entrelacés, découpée par jour
            seq, restants = [], dict(m["par_profil"])
            while any(restants.values()):
                for c in list(restants):
                    if restants[c] > 0:
                        seq.append(c)
                        restants[c] -= 1
            par_jour = repartir(m["objectif"], [1] * len(jours))
            m["par_jour"], pos = [], 0
            for nj in par_jour:
                bloc = seq[pos:pos + nj]
                pos += nj
                m["par_jour"].append({c: bloc.count(c) for c in m["par_profil"]})
        enqueteurs += membres

    calendrier = []
    cumul = 0
    for d_i, d in enumerate(jours):
        ligne = {"date": d.isoformat(), "zones": {}, "profils": {}, "total": 0}
        for m in enqueteurs:
            for c, v in m["par_jour"][d_i].items():
                ligne["zones"][m["zone"]] = ligne["zones"].get(m["zone"], 0) + v
                ligne["profils"][c] = ligne["profils"].get(c, 0) + v
                ligne["total"] += v
        cumul += ligne["total"]
        ligne["cumul"] = cumul
        calendrier.append(ligne)

    couts = None
    if fiche.get("cout"):
        c = fiche["cout"]
        tot_parts = sum(float(x["part"] or 0) for x in params["postes"]) or 100
        postes = [{"poste": x["poste"], "part": float(x["part"] or 0), "montant": c * float(x["part"] or 0) / tot_parts} for x in params["postes"]]
        remu = next((x["montant"] for x in postes if "numération" in x["poste"]), 0)
        couts = {"total": c, "postes": postes, "par_enqueteur": remu / n_enq, "par_enqueteur_jour": remu / n_enq / len(jours),
                 "par_questionnaire": c / n, "remu_par_questionnaire": remu / n}

    rec = recrutement or recrutement_defaut(projet, n_enq, jours)
    return {"params": params, "zones": zones, "profils": profils, "jours": [d.isoformat() for d in jours],
            "nb_enqueteurs": n_enq, "quotas": [[z, c, v] for (z, c), v in quotas.items()], "tot_zone": tot_zone,
            "enqueteurs": enqueteurs, "calendrier": calendrier, "couts": couts, "recrutement": rec}


def generer(projet, quest, precedent=None):
    prec = precedent or {}
    params = prec.get("params") or params_defaut(projet, quest)
    # profils et zones peuvent avoir changé en amont
    params["poids_profils"] = {pr["code"]: params.get("poids_profils", {}).get(pr["code"], 1) for pr in quest["profils"]}
    zones = decouper(projet["fiche"]["zones"])
    params["poids_zones"] = {z: params.get("poids_zones", {}).get(z, 1) for z in zones}
    return calculer(projet, quest, params, prec.get("recrutement"))


def normaliser(projet, quest, data):
    return calculer(projet, quest, data["params"], data.get("recrutement"))


def construire_docs(projet, data, quest):
    fiche = projet["fiche"]
    lib = {pr["code"]: pr["libelle"] for pr in data["profils"]}
    codes = [pr["code"] for pr in data["profils"]]
    jours = [date.fromisoformat(j) for j in data["jours"]]
    n = fiche["taille"]
    q = {(z, c): v for z, c, v in data["quotas"]}
    Z = "Pays" if sont_des_pays(data["zones"]) else "Zone"

    lignes_quotas = [[z] + [str(q[(z, c)]) for c in codes] + [str(data["tot_zone"][z])] for z in data["zones"]]
    lignes_quotas.append(["**Total**"] + [f"**{sum(q[(z, c)] for z in data['zones'])}**" for c in codes] + [f"**{n}**"])
    lignes_enq = [[m["nom"], m["zone"]] + [str(m["par_profil"][c]) for c in codes] + [str(m["objectif"]), nombre(m["objectif"] / len(jours), 1)]
                  for m in data["enqueteurs"]]
    # au-delà de 6 pays, les colonnes par pays ne tiennent plus sur la page : le détail reste dans l'Excel
    zones_cal = data["zones"] if len(data["zones"]) <= 6 else []
    cal = [[date_courte(l["date"])] + [str(l["zones"].get(z, 0)) for z in zones_cal] + [str(l["profils"].get(c, 0)) for c in codes]
           + [str(l["total"]), str(l["cumul"])] for l in data["calendrier"]]

    sections = [
        section("synthese", "1. Synthèse du plan d'échantillonnage", [
            chiffres([{"valeur": str(n), "libelle": "questionnaires visés"}, {"valeur": str(data["nb_enqueteurs"]), "libelle": "enquêteurs"},
                      {"valeur": str(len(jours)), "libelle": "jours de collecte"}, {"valeur": nombre(n / len(jours), 0), "libelle": "questionnaires par jour"}]),
            p(f"La méthode retenue est un **échantillonnage non probabiliste par quotas**, croisant la zone d'enquête et le profil du répondant. "
              f"Le nombre d'enquêteurs est calculé pour une productivité de {nombre(data['params']['rendement'], 0)} questionnaires par enquêteur et par jour, "
              f"avec une marge de sécurité de {int(round((1 - float(data['params']['marge'])) * 100))} % pour absorber les refus et les rendez-vous manqués."),
            p(f"La collecte se déroule du {date_fr(jours[0], True)} au {date_fr(jours[-1], True)}"
              + (", hors dimanches" if data["params"].get("sans_dimanche", True) else "") + "."),
        ], source="auto"),
        section("quotas", "2. Quotas par zone et par profil", [
            tableau([Z] + [lib[c] for c in codes] + ["Total"], lignes_quotas, f"Quotas {Z.lower()} × profil"),
            tableau(["Niveau de lecture", "Effectif", "Marge d'erreur (IC 95 %)"],
                    [["Global", str(n), fmt_marge(n)]] + [[f"{Z} : {z}", str(t), fmt_marge(t)] for z, t in data["tot_zone"].items()]
                    + [[f"Profil : {lib[c]}", str(sum(q[(z, c)] for z in data['zones'])), fmt_marge(sum(q[(z, c)] for z in data['zones']))] for c in codes],
                    "Précision attendue"),
        ], source="auto"),
        section("repartition", "3. Répartition par enquêteur", [
            p("Les enquêteurs sont désignés Enq1, Enq2… tant que la liste nominative n'est pas chargée. Chaque enquêteur reçoit un objectif par profil."),
            tableau(["Enquêteur", Z] + [lib[c] for c in codes] + ["Objectif", "Par jour"], lignes_enq, "Objectifs par enquêteur"),
        ], source="auto"),
        section("calendrier", "4. Calendrier de collecte", [
            p("Objectifs quotidiens par " + ("zone et par profil" if zones_cal else "profil") + ". Le détail par "
              + ("" if zones_cal else "pays, ") + "enquêteur et jour figure dans le fichier Excel du calendrier."),
            tableau(["Jour"] + zones_cal + [lib[c] for c in codes] + ["Total", "Cumul"], cal, "Quotas journaliers", taille=8.5),
            tableau(["Moment", "Activité"], [
                [date_fr(jours[0] - timedelta(days=1), True), "Formation des enquêteurs, prise en main de l'outil et pré-test"],
                [date_fr(jours[0], True), "Démarrage de la collecte"],
                ["Chaque soir", "Envoi des formulaires, point de suivi avec le superviseur, ajustement des quotas"],
                [date_fr(jours[len(jours) // 2], True), "Bilan à mi-parcours, réallocation éventuelle des quotas"],
                [date_fr(jours[-1], True), "Clôture de la collecte et contrôle final"],
            ], "Jalons de la collecte"),
        ], source="auto"),
    ]
    if data.get("couts"):
        c = data["couts"]
        sections.append(section("couts", "5. Répartition du coût d'enquête", [
            tableau(["Poste", "Part", "Montant"], [[x["poste"], f"{nombre(x['part'], 0)} %", fcfa(x["montant"])] for x in c["postes"]]
                    + [["**Total**", "**100 %**", f"**{fcfa(c['total'])}**"]], "Répartition budgétaire", [3, 0.8, 1.4]),
            chiffres([{"valeur": fcfa(c["par_enqueteur"]), "libelle": "rémunération par enquêteur"},
                      {"valeur": fcfa(c["par_enqueteur_jour"]), "libelle": "par enquêteur et par jour"},
                      {"valeur": fcfa(c["par_questionnaire"]), "libelle": "coût total par questionnaire"}]),
        ], source="auto"))
    rec = data["recrutement"]
    sections.append(section("profils_enq", f"{len(sections) + 1}. Profils d'enquêteurs à rechercher", [
        liste([f"Diplôme minimum : {rec['diplome']}.", f"Expérience d'enquête : {rec['experience']} minimum."] + rec["competences"]),
        p("La note de recrutement jointe reprend ces critères pour diffusion."),
    ]))
    note = {
        "titre": "Note d'échantillonnage des enquêteurs", "surtitre": "Baromètre Datatym", "sous_titre": fiche["theme"],
        "meta": [f"{n} questionnaires · {data['nb_enqueteurs']} enquêteurs · {len(jours)} jours", f"Version du {aujourdhui()}"],
        "en_tete": f"Baromètre {fiche['theme']} — Note d'échantillonnage", "sections": sections,
    }
    recrut = {
        "titre": "Note de recrutement", "surtitre": "Datatym recrute", "sous_titre": rec["intitule"],
        "meta": [f"Date limite de candidature : {date_fr(rec['date_limite'])}", f"Candidature : {rec['contact']}"],
        "en_tete": "Datatym — Note de recrutement",
        "sections": [
            section("datatym", "À propos de Datatym", [p(rec["presentation"])]),
            section("mission", "La mission", [p(rec["mission"]), p("Tâches principales :"), liste(rec["taches"])]),
            section("profil", "Le profil recherché", [liste([f"Diplôme : {rec['diplome']} minimum.", f"Expérience d'enquête : {rec['experience']} minimum."] + rec["competences"])]),
            section("conditions", "Conditions", [liste([
                f"Nombre de postes : {data['nb_enqueteurs']}.", f"Zones : {', '.join(data['zones'])}.",
                f"Période : du {date_fr(jours[0])} au {date_fr(jours[-1])}, formation la veille du démarrage."])]),
            section("candidature", "Comment postuler", [liste(rec["dossier"]),
                    p(f"Candidatures à déposer sur **{rec['contact']}** au plus tard le **{date_fr(rec['date_limite'])}**, en précisant « {rec['intitule']} ».")]),
        ],
    }
    return {"note_echantillonnage": note, "note_recrutement": recrut}


def calendrier_xlsx(chemin, data):
    from ..formulaires import _feuille
    from openpyxl import Workbook
    lib = {pr["code"]: pr["libelle"] for pr in data["profils"]}
    wb = Workbook()
    ws = wb.active
    ws.title = "Quotas journaliers"
    lignes = []
    for m in data["enqueteurs"]:
        for d, jour in zip(data["jours"], m["par_jour"]):
            for c, v in jour.items():
                if v:
                    lignes.append([d, m["nom"], m["zone"], lib.get(c, c), v])
    _feuille(ws, ["date", "enquêteur", "zone", "profil", "objectif"], lignes)
    ws2 = wb.create_sheet("Enquêteurs")
    _feuille(ws2, ["code", "nom", "zone", "objectif total"] + [lib[c] for c in lib],
             [[m["code"], m["nom"], m["zone"], m["objectif"]] + [m["par_profil"].get(c, 0) for c in lib] for m in data["enqueteurs"]])
    wb.properties.creator = wb.properties.lastModifiedBy = "DATATYM"
    wb.save(chemin)
    return chemin
