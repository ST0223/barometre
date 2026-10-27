"""Indice H&C de Maturité IA & Automatisation : score de 0 à 100 par entreprise, 5 piliers pondérés, 5 niveaux.

Barème validé sur la plateforme de pilotage du Baromètre IA, appliqué aux réponses brutes de l'enquête QuestionPro
(version courte) : chaque liste donne la note des réponses 1, 2, 3… dans l'ordre du formulaire ; None = « Ne sait pas »
ou « Non concerné », la question est alors retirée du calcul pour cette entreprise (elle ne vaut pas 0).
"""
import json
import re

from .store import dossier

SC = {"b1": [100, 75, 50, 25, 0], "b2": [100, 67, 33, 0], "c2": [100, 75, 50, 25, 0], "c3": [100, 50, 0, None],
      "c4": [100, 67, 33, 0, None], "d2": [100, 75, 50, 25, 0], "d3": [100, 75, 50, 25, 0], "d5": [0, 25, 50, 75, 100],
      "d6": [0, 25, 50, 75, 100, None], "d7": [100, 50, 25, 0, None], "f4": [100, 67, 33, 0], "f5": [0, 25, 50, 75, 100, None],
      "g1": [100, 67, 33, 0, None], "g2": [100, 67, 33, 0, None], "i3": [100, 67, 33, 0], "h1": [100, 50, 0, None],
      "h2": [100, 50, 0, None], "i1": [100, 75, 50, 25, 0], "d4": [0, 33, 67, 100, None], "d8": [100, 67, 33, 0],
      "c6": [100, 50, 0, None]}

PILIERS = [
    {"k": "usage", "nom": "Usage et compétences", "w": .20, "q": ["b1", "b2", "b4", "c1", "c2"],
     "d": "Le dirigeant utilise-t-il l'IA et y est-il formé ? L'entreprise forme-t-elle ses équipes et leur fournit-elle des outils d'IA ?"},
    {"k": "digit", "nom": "Digitalisation", "w": .30, "q": ["d1", "d2", "d3", "d4", "d5", "d8"],
     "d": "Logiciels de gestion en place, part du travail encore manuel, données retraitées dans Excel, fiabilité et usage réel des outils, dématérialisation."},
    {"k": "client", "nom": "Relation client", "w": .15, "q": ["d6", "d7", "f4", "f5"],
     "d": "Clients sur les canaux digitaux, application mobile, chatbot et sa capacité à répondre seul."},
    {"k": "data", "nom": "Data et agents IA", "w": .20, "q": ["c4", "c6", "g1", "g2"],
     "d": "Agents IA déployés et connectés aux logiciels, entrepôt de données, IA capable d'interroger les documents internes."},
    {"k": "engag", "nom": "Engagement et gouvernance", "w": .15, "q": ["c3", "i3"], "qi": ["h1", "h2", "i1"],
     "d": "Charte d'usage de l'IA et des données, préparation de l'entreprise à la généralisation de l'IA."},
]

# Niveaux 1 et 5 : noms de la note de cadrage ; niveaux 2 à 4 : proposition affichée comme telle, à valider par l'équipe
NIVEAUX = ["Manuel", "Exploratoire", "En structuration", "Intégré", "Augmenté par l'IA"]
NIV_DESC = ["Processus essentiellement manuels, IA quasi absente.",
            "Premiers usages individuels de l'IA ; outils de gestion partiels, beaucoup de ressaisies.",
            "Outils de gestion en place, usages de l'IA qui s'organisent, premiers projets d'automatisation.",
            "IA et automatisation intégrées aux processus, données exploitées, équipes formées.",
            "IA au cœur de l'activité : agents connectés aux systèmes, données maîtrisées, gouvernance en place."]

# formation organisée par l'entreprise (c1, réponses 1 à 5) : comité de direction, managers, ensemble, prévue 2027, non
C1_NOTE = {3: 100, 2: 75, 1: 50, 4: 25, 5: 0}


def chemin_reponses(projet):
    return dossier(projet["slug"]) / "donnees" / "questionpro_reponses.json"


def enregistrer_reponses(projet, reponses, questions):
    """Positions des réponses par code de question (ex. {"b1": [1], "c1": [2, 3], "d8_1": [2]}) et options de d1."""
    d1 = next((q for q in questions if str(q.get("code") or "").lower() == "d1"), {})
    options_d1 = [re.sub(r"<[^>]+>", "", str(a.get("text") or "")).strip() for a in d1.get("answers") or d1.get("answerList") or []]
    lignes = []
    for r in reponses:
        codes = {}
        for it in r.get("responseSet") or []:
            c = str(it.get("questionCode") or "").strip().lower()
            ords = [v.get("value", {}).get("ord") for v in it.get("answerValues") or []]
            ords = [int(o) for o in ords if isinstance(o, (int, float)) or str(o).isdigit()]
            if c and ords:
                codes[c] = ords
        lignes.append({"id": str(r.get("responseID", "")), "codes": codes})
    f = chemin_reponses(projet)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"options_d1": options_d1, "reponses": lignes}, ensure_ascii=False), encoding="utf-8")


def lire_reponses(projet):
    f = chemin_reponses(projet)
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def niveau(score):
    return None if score is None else min(5, int(score // 20) + 1)


def note(codes, q, options_d1, c6zero=True):
    """Note de 0 à 100 d'une question pour une entreprise, ou None si elle est retirée du calcul."""
    un = lambda c: (codes.get(c) or [None])[0]
    tab = lambda k, o: None if o is None or not 1 <= o <= len(SC[k]) else SC[k][o - 1]

    def grille(k):
        notes = [tab(k, v[0]) for c, v in codes.items() if re.fullmatch(rf"{k}_\d+", c)]
        notes = [n for n in notes if n is not None]
        return sum(notes) / len(notes) if notes else None

    if q == "b4":
        if un("b1") == 5:
            return 0  # n'utilise jamais l'IA
        o = [v[0] for c, v in codes.items() if re.fullmatch(r"b4_\d+", c)]
        if not o:
            return None
        return 100 if 2 in o else 50 if 1 in o else 25 if 3 in o else 0
    if q == "c1":
        o = codes.get("c1")
        return max(C1_NOTE.get(x, 0) for x in o) if o else None
    if q == "d1":
        o = codes.get("d1")
        if not o:
            return None
        aucun = [i + 1 for i, t in enumerate(options_d1) if t.lower().startswith("aucun")]
        if any(x in aucun for x in o):
            return 0
        outils = [i + 1 for i, t in enumerate(options_d1) if not re.match(r"(aucun|autre)", t, re.I)] or list(range(1, 13))
        return round(100 * sum(1 for x in o if x in outils) / len(outils))
    if q in ("d4", "d8"):
        return grille(q)
    if q == "c6":
        if c6zero and un("c4") == 4:
            return 0  # pas d'agent IA : aucune connexion possible
        return grille("c6")
    if q == "f5":
        return tab("f5", un("f5")) if un("f4") in (1, 2) else None
    return tab(q, un(q))


def score(codes, options_d1, intentions=False, c6zero=True):
    """Indice d'une entreprise : moyenne des questions de chaque pilier (au moins la moitié répondues),
    puis moyenne pondérée des piliers disponibles."""
    pil, sw, ss = {}, 0, 0
    for p in PILIERS:
        qs = p["q"] + (p.get("qi", []) if intentions else [])
        notes = [n for n in (note(codes, q, options_d1, c6zero) for q in qs) if n is not None]
        s = sum(notes) / len(notes) if notes and len(notes) * 2 >= len(qs) else None
        pil[p["k"]] = s
        if s is not None:
            sw += p["w"]
            ss += p["w"] * s
    indice = ss / sw if sw else None
    return {"indice": indice, "niveau": niveau(indice), "piliers": pil}
