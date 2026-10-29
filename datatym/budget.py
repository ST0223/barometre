"""Coût de revient d'un baromètre, construit poste par poste : quantité tirée du plan × coût unitaire.

Le même calcul sert trois fois : fourchette au cadrage (hypothèses standards), budget détaillé au plan
de collecte (quotas, enquêteurs et calendrier retenus), bilan prévu contre réalisé à la clôture.
"""
import math

from .banque import decouper
from .config import charger_parametres
from .outils import debut_collecte, jours_collecte

# Coûts unitaires de référence (FCFA), modifiables dans Paramètres puis étude par étude
COUTS_DEFAUT = [
    {"cle": "remu_questionnaire", "libelle": "Rémunération des enquêteurs", "unite": "questionnaire validé", "valeur": 2500},
    {"cle": "transport_jour", "libelle": "Transport des enquêteurs", "unite": "enquêteur et jour", "valeur": 3000},
    {"cle": "communication_jour", "libelle": "Communication (crédit et données)", "unite": "enquêteur et jour", "valeur": 1000},
    {"cle": "formation_enqueteur", "libelle": "Per diem de formation", "unite": "enquêteur et jour de formation", "valeur": 10000},
    {"cle": "formation_zone", "libelle": "Salle et supports de formation", "unite": "zone", "valeur": 50000},
    {"cle": "supervision_jour", "libelle": "Supervision du terrain", "unite": "superviseur et jour", "valeur": 20000},
    {"cle": "controle_rappel", "libelle": "Rappels de contrôle qualité", "unite": "rappel", "valeur": 500},
    {"cle": "outils_forfait", "libelle": "Outil de collecte et matériel", "unite": "forfait", "valeur": 100000},
    {"cle": "preparation_jour", "libelle": "Conception et coordination", "unite": "jour de chef de projet", "valeur": 75000},
    {"cle": "analyse_jour", "libelle": "Traitement, analyse et rapport", "unite": "jour d'analyste", "valeur": 75000},
]

HYPOTHESES_DEFAUT = {
    "jours_formation": 1, "enq_par_superviseur": 8, "part_rappels": 10, "jours_preparation": 5,
    "jours_analyse": 8, "imprevus": 8, "coef_deplacement": 1.0,
}

# Scénarios de la fourchette du cadrage : seules les hypothèses incertaines varient
SCENARIOS = [
    ("bas", "Bas", 8, {"jours_preparation": 4, "jours_analyse": 6, "part_rappels": 10, "imprevus": 5},
     "8 questionnaires par enquêteur et par jour, déplacements courts, 10 jours d'équipe, 5 % d'imprévus"),
    ("central", "Central", 6, {},
     "6 questionnaires par enquêteur et par jour, 13 jours d'équipe, 8 % d'imprévus"),
    ("haut", "Haut", 5, {"coef_deplacement": 1.3, "jours_preparation": 7, "jours_analyse": 10, "part_rappels": 15, "imprevus": 12},
     "5 questionnaires par enquêteur et par jour, zones éloignées (+30 % de transport), 17 jours d'équipe, 15 % de rappels, 12 % d'imprévus"),
]


def couts_reference():
    """Grille Datatym : celle des Paramètres si elle existe, complétée par les valeurs par défaut."""
    perso = {c["cle"]: c for c in charger_parametres().get("couts_unitaires") or [] if isinstance(c, dict) and c.get("cle")}
    return [{**c, "valeur": float(perso.get(c["cle"], {}).get("valeur", c["valeur"]) or 0)} for c in COUTS_DEFAUT]


def completer(couts, hypotheses):
    """Grille et hypothèses complètes, dans l'ordre de référence (une étude ancienne peut en manquer)."""
    par_cle = {c["cle"]: c for c in couts or []}
    # postes de référence (un poste décoché est exclu du budget), puis postes ajoutés par l'utilisateur (forfaits)
    grille = [{**c, "valeur": float(par_cle.get(c["cle"], c)["valeur"] or 0), "actif": par_cle.get(c["cle"], {}).get("actif", True) is not False}
              for c in couts_reference()]
    grille += [{"cle": c["cle"], "libelle": str(c.get("libelle") or "Autre poste"), "unite": "forfait", "valeur": float(c.get("valeur") or 0),
                "actif": c.get("actif", True) is not False, "perso": True}
               for c in couts or [] if str(c.get("cle", "")).startswith("perso_")]
    hyp = {**HYPOTHESES_DEFAUT, **{k: float(v) for k, v in (hypotheses or {}).items() if k in HYPOTHESES_DEFAUT and v not in (None, "")}}
    return grille, hyp


def calculer(n, n_enq, n_jours, n_zones, couts, hypotheses):
    """Budget poste par poste. Renvoie les lignes, le sous-total, les imprévus et le total."""
    grille, h = completer(couts, hypotheses)
    u = {c["cle"]: c["valeur"] for c in grille}
    lib = {c["cle"]: c["libelle"] for c in grille}
    jf = h["jours_formation"]
    n_sup = max(n_zones, math.ceil(n_enq / max(h["enq_par_superviseur"], 1)))
    rappels = math.ceil(n * h["part_rappels"] / 100)
    ej = n_enq * n_jours

    def ligne(cle, base, quantite, unitaire, terrain=True):
        return {"cle": cle, "poste": lib[cle], "base": base, "quantite": quantite, "unitaire": unitaire,
                "montant": quantite * unitaire, "terrain": terrain}

    lignes = [
        ligne("remu_questionnaire", "questionnaires validés", n, u["remu_questionnaire"]),
        ligne("transport_jour", f"{n_enq} enquêteurs × {n_jours} jours"
              + (f" × {h['coef_deplacement']:.2f}".replace(".", ",") if h["coef_deplacement"] != 1 else ""),
              ej, u["transport_jour"] * h["coef_deplacement"]),
        ligne("communication_jour", f"{n_enq} enquêteurs × {n_jours} jours", ej, u["communication_jour"]),
        ligne("formation_enqueteur", f"{n_enq} enquêteurs × {jf:g} jour(s)", n_enq * jf, u["formation_enqueteur"]),
        ligne("formation_zone", f"{n_zones} zone(s)", n_zones, u["formation_zone"]),
        ligne("supervision_jour", f"{n_sup} superviseur(s) × {n_jours + jf:g} jours", n_sup * (n_jours + jf), u["supervision_jour"]),
        ligne("controle_rappel", f"{h['part_rappels']:g} % des questionnaires rappelés", rappels, u["controle_rappel"]),
        ligne("outils_forfait", "forfait", 1, u["outils_forfait"], False),
        ligne("preparation_jour", f"{h['jours_preparation']:g} jours", h["jours_preparation"], u["preparation_jour"], False),
        ligne("analyse_jour", f"{h['jours_analyse']:g} jours", h["jours_analyse"], u["analyse_jour"], False),
    ] + [ligne(c["cle"], "forfait", 1, c["valeur"], False) for c in grille if c.get("perso")]
    actif = {c["cle"]: c["actif"] for c in grille}
    lignes = [l for l in lignes if actif.get(l["cle"], True)]
    sous_total = sum(l["montant"] for l in lignes)
    imprevus = sous_total * h["imprevus"] / 100
    total = sous_total + imprevus
    terrain = sum(l["montant"] for l in lignes if l["terrain"])
    return {"lignes": lignes, "sous_total": sous_total, "imprevus": imprevus, "taux_imprevus": h["imprevus"],
            "total": total, "par_questionnaire": total / max(n, 1), "part_terrain": 100 * terrain / max(sous_total, 1),
            "n": n, "nb_enqueteurs": n_enq, "nb_superviseurs": n_sup, "nb_jours": n_jours, "nb_zones": n_zones,
            "couts": grille, "hypotheses": h}


def arrondi(x, pas=100000):
    return int(round(x / pas) * pas) if x >= pas else int(round(x))


def estimer_cadrage(fiche):
    """Fourchette d'ordre de grandeur à partir de la seule fiche d'entrée."""
    n = int(fiche.get("taille") or 0) or 1
    zones = decouper(fiche.get("zones", "")) or [""]
    jours = len(jours_collecte(debut_collecte(fiche), fiche.get("duree") or 1))
    scenarios = []
    for cle, nom, rendement, hyp, texte in SCENARIOS:
        n_enq = max(len(zones), math.ceil(n / (rendement * jours * 0.9)))
        b = calculer(n, n_enq, jours, len(zones), couts_reference(), hyp)
        scenarios.append({"cle": cle, "nom": nom, "hypothese": texte, "nb_enqueteurs": n_enq,
                          "total": arrondi(b["total"]), "par_questionnaire": arrondi(b["total"] / n, 50)})
    s = {x["cle"]: x for x in scenarios}
    plafond = fiche.get("cout")
    return {"bas": s["bas"]["total"], "central": s["central"]["total"], "haut": s["haut"]["total"],
            "par_questionnaire": s["central"]["par_questionnaire"], "scenarios": scenarios, "jours": jours,
            "plafond": plafond, "dans_plafond": None if not plafond else s["haut"]["total"] <= plafond,
            "plafond_court": None if not plafond else plafond < s["bas"]["total"]}


def marginal(n, n_enq, n_jours, n_zones, couts, hypotheses, ajout=100):
    """Coût de questionnaires supplémentaires, les enquêteurs augmentant en proportion."""
    base = calculer(n, n_enq, n_jours, n_zones, couts, hypotheses)["total"]
    plus = calculer(n + ajout, math.ceil(n_enq * (n + ajout) / max(n, 1)), n_jours, n_zones, couts, hypotheses)["total"]
    return plus - base


def bilan(budget, depenses, stats):
    """Prévu contre réalisé, poste par poste ; seuls les postes saisis entrent dans le réalisé."""
    if not budget:
        return None
    depenses = {k: float(v) for k, v in (depenses or {}).items() if v not in (None, "")}
    lignes = []
    for l in budget["lignes"] + [{"cle": "imprevus", "poste": "Imprévus", "montant": budget["imprevus"], "terrain": False}]:
        reel = depenses.get(l["cle"])
        lignes.append({"cle": l["cle"], "poste": l["poste"], "prevu": l["montant"], "reel": reel,
                       "ecart": None if reel is None else reel - l["montant"], "terrain": l.get("terrain")})
    saisis = [l for l in lignes if l["reel"] is not None]
    if not saisis:
        return {"lignes": lignes, "complet": False, "saisi": False}
    complet = len(saisis) == len(lignes)
    prevu_saisis = sum(l["prevu"] for l in saisis)
    reel = sum(l["reel"] for l in saisis)
    valides = (stats or {}).get("realise") or 0
    ecartes = ((stats or {}).get("rapides") or 0) + ((stats or {}).get("hors_cible") or 0)
    brut_utile = valides + ecartes
    terrain_reel = sum(l["reel"] for l in saisis if l["terrain"] and l["cle"] != "remu_questionnaire")
    return {
        "lignes": lignes, "saisi": True, "complet": complet,
        "prevu": budget["total"], "prevu_saisis": prevu_saisis, "reel": reel, "ecart": reel - prevu_saisis,
        "par_questionnaire_prevu": budget["par_questionnaire"],
        # un coût unitaire calculé sur une partie des postes serait trompeur
        "par_questionnaire_reel": reel / valides if valides and complet else None, "valides": valides, "ecartes": ecartes,
        # questionnaires écartés : ils ont mobilisé transport, communication et supervision sans être retenus
        "non_qualite": terrain_reel * ecartes / brut_utile if brut_utile else 0,
    }
