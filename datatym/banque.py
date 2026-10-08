"""Banque d'indicateurs de baromètre et règles de construction des questions.

Chaque indicateur porte un « type » qui fixe à la fois la question, les modalités,
la codification et le mode de calcul. C'est ce qui garantit la cohérence
cadrage → questionnaire → dictionnaire → rapport.
"""
import re
import unicodedata

# ----------------------------------------------------------------- utilitaires
def slug(texte, sep="_", maxi=40):
    t = unicodedata.normalize("NFKD", str(texte)).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", sep, t).strip(sep).lower()
    return t[:maxi].strip(sep) or "x"


def decouper(texte):
    """« DG, responsables et vendeurs » -> ['DG', 'responsables', 'vendeurs']"""
    if isinstance(texte, list):
        return [str(x).strip() for x in texte if str(x).strip()]
    morceaux = re.split(r"\s*(?:,|;|/|\bet\b|\n)\s*", str(texte or ""))
    return [m.strip() for m in morceaux if m and m.strip()]


# Champ d'étude habituel de Datatym : pays de l'UEMOA, de la CEMAC, Guinée et RD Congo.
ESPACES = {
    "UEMOA": ["Bénin", "Burkina Faso", "Côte d'Ivoire", "Guinée-Bissau", "Mali", "Niger", "Sénégal", "Togo"],
    "CEMAC": ["Cameroun", "Centrafrique", "Congo", "Gabon", "Guinée équatoriale", "Tchad"],
    "Guinée": ["Guinée"],
    "RD Congo": ["RD Congo"],
}
ESPACE_DU_PAYS = {slug(p): e for e, liste in ESPACES.items() for p in liste}


def sont_des_pays(zones):
    """Vrai si le champ d'étude contient des pays de la liste Datatym (le questionnaire parle alors de pays)."""
    return any(slug(z) in ESPACE_DU_PAYS for z in decouper(zones))


def resume_champ(zones):
    """« UEMOA (8 pays), CEMAC (2 pays), autres : Maroc »"""
    par_espace, autres = {}, []
    for z in decouper(zones):
        e = ESPACE_DU_PAYS.get(slug(z))
        if e and e not in ("Guinée", "RD Congo"):
            par_espace[e] = par_espace.get(e, 0) + 1
        else:
            autres.append(z)
    morceaux = [f"{e} ({n} pays)" for e, n in par_espace.items()] + autres
    return ", ".join(morceaux)


DIRECTION_RE = re.compile(r"\b(dg|pdg|dga|directeur|directrice|direction|dirigeant|responsable|manager|chef|g[ée]rant|cadre|daf|dsi|drh|ceo|patron|propri[ée]taire)", re.I)


def profils_depuis_cible(cible):
    profils = []
    vus = set()
    for lib in decouper(cible):
        code = slug(lib, maxi=20)
        if code in vus:
            continue
        vus.add(code)
        niveau = "direction" if DIRECTION_RE.search(lib) else "operationnel"
        profils.append({"code": code, "libelle": lib[:1].upper() + lib[1:], "niveau": niveau})
    if not profils:
        profils = [{"code": "repondant", "libelle": "Répondant", "niveau": "direction"}]
    return profils


# ----------------------------------------------------------------- types
# Échelles ordinales codées en chiffres, du plus défavorable au plus favorable ; « Ne sait pas » = 99.
NSP_CODE = "99"
NSP = {"code": NSP_CODE, "label": "Ne sait pas"}

TYPES = {
    "jugement": {
        "libelle": "Jugement (échelle 5 niveaux)",
        "calcul": "Solde d'opinion = % de réponses positives (très bon + bon) − % de réponses négatives (mauvais + très mauvais), sur les répondants concernés hors « Ne sait pas ».",
        "modalites": [("1", "Très mauvais(e)"), ("2", "Mauvais(e)"), ("3", "Moyen(ne)"), ("4", "Bon(ne)"), ("5", "Très bon(ne)")],
        "positifs": ["4", "5"], "negatifs": ["1", "2"],
        "secondes": 14,
    },
    "evolution": {
        "libelle": "Évolution passée (6 derniers mois)",
        "calcul": "Solde d'opinion = % « en hausse / amélioration » − % « en baisse / dégradation », hors « Ne sait pas ».",
        "positifs": ["3"], "negatifs": ["1"],
        "secondes": 12,
    },
    "perspective": {
        "libelle": "Perspective (6 prochains mois)",
        "calcul": "Solde d'opinion = % « hausse / amélioration » attendue − % « baisse / dégradation » attendue, hors « Ne sait pas ».",
        "positifs": ["3"], "negatifs": ["1"],
        "secondes": 12,
    },
    "satisfaction": {
        "libelle": "Satisfaction (échelle 1 à 5)",
        "calcul": "Taux de satisfaction = % de notes 4 et 5 ; score moyen sur 5 en complément.",
        "modalites": [("1", "Pas du tout satisfait"), ("2", "Peu satisfait"), ("3", "Moyennement satisfait"), ("4", "Satisfait"), ("5", "Très satisfait")],
        "positifs": ["4", "5"], "negatifs": ["1", "2"],
        "secondes": 12,
    },
    "intention": {
        "libelle": "Intention (4 niveaux)",
        "calcul": "Taux d'intention = % « Oui, certainement » + % « Oui, probablement », sur les répondants concernés.",
        "modalites": [("1", "Non, certainement pas"), ("2", "Non, probablement pas"), ("3", "Oui, probablement"), ("4", "Oui, certainement")],
        "positifs": ["3", "4"], "negatifs": ["1", "2"],
        "secondes": 12,
    },
    "multiple": {
        "libelle": "Choix multiple (3 réponses maximum)",
        "calcul": "Taux de citation de chaque modalité = nombre de répondants l'ayant cochée / répondants concernés. Le total dépasse 100 %.",
        "secondes": 25,
    },
    "unique": {
        "libelle": "Choix unique",
        "calcul": "Répartition en % des répondants concernés pour chaque modalité.",
        "secondes": 14,
    },
    "numerique": {
        "libelle": "Valeur numérique",
        "calcul": "Moyenne et médiane des valeurs déclarées, après exclusion des valeurs aberrantes (au-delà de 3 écarts interquartiles).",
        "secondes": 15,
    },
    "indice": {
        "libelle": "Indice composite (0 à 100)",
        "calcul": "Moyenne des soldes d'opinion des indicateurs composants, ramenée sur une échelle de 0 à 100 : indice = (solde moyen + 100) / 2. Au-dessus de 50 : opinion majoritairement favorable.",
        "secondes": 0,
    },
}

SENS = {
    "hausse": (("1", "En baisse"), ("2", "Stable"), ("3", "En hausse")),
    "amelioration": (("1", "En dégradation"), ("2", "Stable"), ("3", "En amélioration")),
}


def modalites(ind):
    """Modalités (code, libellé) d'un indicateur."""
    t = ind["type"]
    if t in ("jugement", "satisfaction", "intention"):
        mods = [{"code": c, "label": l} for c, l in TYPES[t]["modalites"]]
    elif t in ("evolution", "perspective"):
        mods = [{"code": c, "label": l} for c, l in SENS.get(ind.get("sens", "amelioration"), SENS["amelioration"])]
    elif t in ("multiple", "unique"):
        # choix unique : codes chiffrés 1, 2, 3… ; choix multiple : codes en mots (une colonne 0/1 par modalité)
        mods = []
        for k, o in enumerate(ind.get("options", []), 1):
            label = o.get("label", "") if isinstance(o, dict) else str(o)
            code = (o.get("code") if isinstance(o, dict) else None) or (str(k) if t == "unique" else slug(label, maxi=18))
            mods.append({"code": code, "label": label})
        if t == "multiple" and not any(m["code"] == "autre" for m in mods):
            mods.append({"code": "autre", "label": "Autre (préciser)"})
        return mods
    else:
        return []
    mods.append(dict(NSP))
    return mods


def texte_question(ind, mode="terrain"):
    """Formulation simple de la question selon le type."""
    if ind.get("question"):
        return ind["question"]
    t, objet = ind["type"], ind.get("objet", ind.get("libelle", "").lower())
    vous = "votre" if mode == "digital" else "votre"
    if t == "jugement":
        return f"Comment jugez-vous actuellement {objet} ?"
    if t == "evolution":
        return f"Au cours des 6 derniers mois, comment a évolué {objet} ?"
    if t == "perspective":
        return f"Au cours des 6 prochains mois, comment pensez-vous que {objet} va évoluer ?"
    if t == "satisfaction":
        return f"Quel est {vous} niveau de satisfaction concernant {objet} ?"
    if t == "intention":
        return f"Envisagez-vous de {objet} au cours des 12 prochains mois ?"
    if t == "numerique":
        return f"{objet[:1].upper() + objet[1:]} ?"
    return ind.get("libelle", "") + " ?"


# ----------------------------------------------------------------- domaines
def _i(libelle, type_, objet="", bloc="", niveau="tous", sens="amelioration", options=None, question="", definition=""):
    d = {"libelle": libelle, "type": type_, "objet": objet, "bloc": bloc, "niveau": niveau, "sens": sens, "definition": definition}
    if options:
        d["options"] = options
    if question:
        d["question"] = question
    return d


DOMAINES = {
    "affaires": {
        "mots": r"affaires|entreprise|commerce|conjoncture|[ée]conom|march[ée]|secteur priv|pme|industri|investiss|exportat|activit",
        "libelle": "Climat des affaires",
        "blocs": ["Situation actuelle", "Évolution récente", "Perspectives", "Contraintes et attentes"],
        "indicateurs": [
            _i("Jugement sur le niveau d'activité actuel", "jugement", "le niveau d'activité de votre entreprise", "Situation actuelle"),
            _i("Jugement sur la situation de trésorerie", "jugement", "la situation de trésorerie de votre entreprise", "Situation actuelle", niveau="direction"),
            _i("Évolution du chiffre d'affaires (6 derniers mois)", "evolution", "le chiffre d'affaires de votre entreprise", "Évolution récente", sens="hausse"),
            _i("Évolution de la fréquentation de la clientèle", "evolution", "la fréquentation de votre clientèle", "Évolution récente", niveau="operationnel", sens="hausse"),
            _i("Évolution des prix de vente", "evolution", "le niveau de vos prix de vente", "Évolution récente", sens="hausse"),
            _i("Perspectives d'activité (6 prochains mois)", "perspective", "l'activité de votre entreprise", "Perspectives", sens="hausse"),
            _i("Perspectives d'emploi (6 prochains mois)", "perspective", "les effectifs de votre entreprise", "Perspectives", niveau="direction", sens="hausse"),
            _i("Intention d'investir (12 prochains mois)", "intention", "réaliser un investissement (équipement, extension, stock)", "Perspectives", niveau="direction"),
            _i("Principales contraintes rencontrées", "multiple", bloc="Contraintes et attentes",
               question="Quelles sont les principales difficultés que rencontre votre entreprise ? (3 réponses maximum)",
               options=["Baisse de la demande", "Concurrence informelle", "Coût et accès au financement", "Fiscalité et taxes", "Coût de l'énergie et coupures", "Hausse des coûts d'approvisionnement", "Lenteurs administratives", "Délais de paiement des clients"]),
            _i("Attentes prioritaires envers les pouvoirs publics", "multiple", bloc="Contraintes et attentes", niveau="direction",
               question="Quelles mesures attendez-vous en priorité des pouvoirs publics ? (3 réponses maximum)",
               options=["Allègement fiscal", "Lutte contre l'informel", "Accès au crédit", "Simplification administrative", "Paiement de la dette intérieure", "Stabilité de l'énergie", "Formation de la main-d'œuvre"]),
        ],
        "indice": ("Indice de confiance", ["Jugement sur le niveau d'activité actuel", "Évolution du chiffre d'affaires (6 derniers mois)", "Perspectives d'activité (6 prochains mois)", "Perspectives d'emploi (6 prochains mois)"]),
    },
    "numerique": {
        "mots": r"\bia\b|intelligence artificielle|digital|num[ée]rique|technolog|automatis|transformation|cyber|donn[ée]es",
        "libelle": "Transformation numérique",
        "blocs": ["Usages actuels", "Équipement et maturité", "Perspectives", "Freins et attentes"],
        "indicateurs": [
            _i("Fréquence d'usage des outils numériques / IA", "unique", bloc="Usages actuels",
               question="À quelle fréquence utilisez-vous des outils d'intelligence artificielle dans votre travail ?",
               options=["Tous les jours", "Plusieurs fois par semaine", "Plusieurs fois par mois", "Rarement", "Jamais"]),
            _i("Jugement sur le niveau de digitalisation", "jugement", "le niveau de digitalisation de votre organisation", "Équipement et maturité"),
            _i("Satisfaction vis-à-vis des outils en place", "satisfaction", "les outils numériques mis à votre disposition", "Équipement et maturité"),
            _i("Évolution de l'usage du numérique (6 derniers mois)", "evolution", "l'usage du numérique dans votre activité", "Équipement et maturité", sens="hausse"),
            _i("Perspectives d'adoption (6 prochains mois)", "perspective", "l'usage de l'IA dans votre organisation", "Perspectives", sens="hausse"),
            _i("Intention d'investir dans le numérique", "intention", "investir dans de nouveaux outils numériques ou d'IA", "Perspectives", niveau="direction"),
            _i("Principaux freins à l'adoption", "multiple", bloc="Freins et attentes",
               question="Quels sont les principaux freins à l'adoption de l'IA dans votre organisation ? (3 réponses maximum)",
               options=["Coût des solutions", "Manque de compétences", "Sécurité des données", "Qualité des données", "Manque de cas d'usage clairs", "Résistance au changement", "Connexion internet insuffisante"]),
            _i("Besoins prioritaires d'accompagnement", "multiple", bloc="Freins et attentes",
               question="De quel accompagnement auriez-vous le plus besoin ? (3 réponses maximum)",
               options=["Formation des équipes", "Conseil et diagnostic", "Financement", "Solutions clés en main", "Partage d'expériences entre pairs"]),
        ],
        "indice": ("Indice de maturité numérique", ["Jugement sur le niveau de digitalisation", "Évolution de l'usage du numérique (6 derniers mois)", "Perspectives d'adoption (6 prochains mois)"]),
    },
    "emploi": {
        "mots": r"talent|emploi|rh\b|ressources humaines|jeune|gen ?z|salari|travail|recrutement|engagement",
        "libelle": "Emploi et talents",
        "blocs": ["Situation actuelle", "Relation employeur", "Perspectives", "Attentes"],
        "indicateurs": [
            _i("Satisfaction au travail", "satisfaction", "votre emploi actuel", "Situation actuelle"),
            _i("Jugement sur les conditions de travail", "jugement", "vos conditions de travail", "Situation actuelle"),
            _i("Jugement sur la reconnaissance", "jugement", "la reconnaissance de votre travail par votre employeur", "Relation employeur"),
            _i("Évolution du pouvoir d'achat (6 derniers mois)", "evolution", "votre pouvoir d'achat", "Situation actuelle"),
            _i("Perspectives professionnelles (6 prochains mois)", "perspective", "votre situation professionnelle", "Perspectives"),
            _i("Intention de changer d'employeur", "intention", "changer d'employeur", "Perspectives"),
            _i("Attentes prioritaires envers l'employeur", "multiple", bloc="Attentes",
               question="Qu'attendez-vous en priorité de votre employeur ? (3 réponses maximum)",
               options=["Meilleure rémunération", "Formation", "Évolution de carrière", "Flexibilité", "Reconnaissance", "Sens et impact du travail", "Bonne ambiance"]),
        ],
        "indice": ("Indice de confiance des actifs", ["Jugement sur les conditions de travail", "Jugement sur la reconnaissance", "Évolution du pouvoir d'achat (6 derniers mois)", "Perspectives professionnelles (6 prochains mois)"]),
    },
    "generique": {
        "mots": r"",
        "libelle": "Baromètre d'opinion",
        "blocs": ["Situation actuelle", "Évolution récente", "Perspectives", "Attentes"],
        "indicateurs": [
            _i("Jugement sur la situation actuelle", "jugement", "la situation actuelle dans votre domaine", "Situation actuelle"),
            _i("Satisfaction générale", "satisfaction", "la situation actuelle dans votre domaine", "Situation actuelle"),
            _i("Évolution perçue (6 derniers mois)", "evolution", "la situation dans votre domaine", "Évolution récente"),
            _i("Perspectives (6 prochains mois)", "perspective", "la situation dans votre domaine", "Perspectives"),
            _i("Intention d'agir", "intention", "engager de nouvelles actions dans ce domaine", "Perspectives", niveau="direction"),
            _i("Principales difficultés", "multiple", bloc="Attentes",
               question="Quelles sont les principales difficultés que vous rencontrez ? (3 réponses maximum)",
               options=["Manque de moyens financiers", "Cadre réglementaire", "Manque de compétences", "Accès à l'information", "Concurrence", "Infrastructures"]),
            _i("Attentes prioritaires", "multiple", bloc="Attentes",
               question="Quelles sont vos attentes prioritaires ? (3 réponses maximum)",
               options=["Accompagnement financier", "Formation", "Simplification des démarches", "Meilleure information", "Concertation avec les autorités"]),
        ],
        "indice": ("Indice synthétique", ["Jugement sur la situation actuelle", "Évolution perçue (6 derniers mois)", "Perspectives (6 prochains mois)"]),
    },
}


def detecter_domaine(theme, objectif=""):
    texte = f"{theme} {objectif}"
    for cle in ("numerique", "emploi", "affaires"):
        if re.search(DOMAINES[cle]["mots"], texte, re.I):
            return cle
    return "generique"


def indicateurs_par_defaut(fiche):
    """Liste d'indicateurs numérotés pour une fiche, avec l'indice composite."""
    dom = DOMAINES[detecter_domaine(fiche.get("theme", ""), fiche.get("objectif", ""))]
    inds = []
    for k, base in enumerate(dom["indicateurs"], 1):
        ind = dict(base)
        ind["id"] = f"I{k:02d}"
        ind["actif"] = True
        if not ind.get("definition"):
            ind["definition"] = definition_auto(ind)
        inds.append(ind)
    nom_indice, composants = dom["indice"]
    ids = [i["id"] for i in inds if i["libelle"] in composants]
    inds.insert(0, {
        "id": "I00", "libelle": nom_indice, "type": "indice", "bloc": "Synthèse", "niveau": "tous", "actif": True,
        "composantes": ids, "objet": "", "sens": "",
        "definition": f"Indicateur synthétique du baromètre, calculé à partir de {len(ids)} soldes d'opinion.",
    })
    return inds, dom


def definition_auto(ind):
    t = ind["type"]
    objet = ind.get("objet") or ind.get("libelle", "").lower()
    return {
        "jugement": f"Appréciation de {objet} au moment de l'enquête.",
        "evolution": f"Perception de l'évolution de {objet} au cours des 6 derniers mois.",
        "perspective": f"Anticipation de l'évolution de {objet} au cours des 6 prochains mois.",
        "satisfaction": f"Niveau de satisfaction concernant {objet}.",
        "intention": f"Part des répondants qui envisagent de {objet}.",
        "multiple": "Fréquence de citation de chaque modalité proposée.",
        "unique": "Répartition des réponses entre les modalités proposées.",
        "numerique": f"Valeur moyenne déclarée pour {objet}.",
    }.get(t, ind.get("libelle", ""))


def profils_concernes(ind, profils):
    """Codes des profils qui reçoivent la question de l'indicateur."""
    niveau = ind.get("niveau", "tous")
    if niveau in ("", "tous", None):
        return [p["code"] for p in profils]
    if isinstance(niveau, list):
        return [c for c in niveau if c in {p["code"] for p in profils}] or [p["code"] for p in profils]
    codes = [p["code"] for p in profils if p["niveau"] == niveau]
    return codes or [p["code"] for p in profils]
