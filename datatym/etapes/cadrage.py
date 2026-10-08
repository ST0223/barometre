"""Étape 1 — Note de cadrage : contexte, objectifs, cible, indicateurs recherchés."""
from datetime import timedelta

from .. import llm
from ..banque import (DOMAINES, TYPES, decouper, definition_auto, indicateurs_par_defaut, profils_concernes,
                      profils_depuis_cible, resume_champ, sont_des_pays)
from ..charte import liste, p, section, tableau, chiffres
from ..outils import date_fr, debut_collecte, fcfa, fmt_marge, repartir, aujourdhui

DOCS = {"note_cadrage": ("NoteCadrage", "Note de cadrage")}


def contexte_regles(fiche, dom):
    theme, objectif = fiche["theme"], fiche["objectif"]
    zones = ", ".join(decouper(fiche["zones"]))
    return [
        f"Datatym lance un baromètre consacré au thème suivant : **{theme}**. L'étude porte sur {zones}"
        + (f", dans le secteur {fiche['secteur']}" if fiche.get("secteur") else "") + ".",
        "Les décideurs disposent rarement de données récentes, comparables et régulièrement mises à jour sur ce sujet. "
        "Les informations disponibles sont souvent partielles, anciennes ou issues de sources hétérogènes, ce qui limite "
        "leur usage pour orienter les décisions.",
        "Le baromètre comble ce manque en mesurant, à intervalles réguliers et selon une méthode constante, la perception "
        "et la situation déclarée des acteurs concernés. Sa reconduction permettra de suivre les évolutions dans le temps "
        "à partir des mêmes indicateurs.",
        f"Mandat de l'équipe Datatym : concevoir l'échantillon et le questionnaire, collecter les {fiche['taille']} réponses "
        f"sur {fiche['duree']} jours, contrôler la qualité des données, calculer les indicateurs et produire le rapport d'analyse.",
    ]


def objectifs_regles(fiche, indicateurs):
    blocs = []
    for i in indicateurs:
        if i.get("actif", True) and i["type"] != "indice" and i.get("bloc") not in blocs:
            blocs.append(i["bloc"])
    spe = [f"Mesurer les indicateurs du bloc « {b} »." for b in blocs]
    spe.insert(0, "Établir une photographie de référence auprès des profils ciblés.")
    spe.append("Calculer un indice synthétique comparable d'une édition à l'autre.")
    spe.append("Comparer les résultats par profil de répondant et par zone d'enquête.")
    return spe


def _avec_ia(fiche, dom, indicateurs):
    schema = {
        "type": "object",
        "properties": {
            "contexte": {"type": "array", "items": {"type": "string"}},
            "objectifs_specifiques": {"type": "array", "items": {"type": "string"}},
            "indicateurs": {"type": "array", "items": {
                "type": "object",
                "properties": {
                    "libelle": {"type": "string"},
                    "type": {"type": "string", "enum": ["jugement", "evolution", "perspective", "satisfaction", "intention", "multiple", "unique"]},
                    "objet": {"type": "string"},
                    "question": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}},
                    "bloc": {"type": "string"},
                    "niveau": {"type": "string", "enum": ["tous", "direction", "operationnel"]},
                    "sens": {"type": "string", "enum": ["hausse", "amelioration"]},
                    "definition": {"type": "string"},
                    "dans_indice": {"type": "boolean"},
                },
                "required": ["libelle", "type", "objet", "question", "options", "bloc", "niveau", "sens", "definition", "dans_indice"],
                "additionalProperties": False}},
            "nom_indice": {"type": "string"},
        },
        "required": ["contexte", "objectifs_specifiques", "indicateurs", "nom_indice"],
        "additionalProperties": False,
    }
    exemple = "\n".join(f"- {i['libelle']} ({i['type']})" for i in indicateurs)
    consigne = f"""Prépare la note de cadrage d'un baromètre Datatym.

Fiche d'entrée :
- Thème : {fiche['theme']}
- Objectif : {fiche['objectif']}
- Cible (profils) : {fiche['cible']}
- Champ : zones {fiche['zones']} ; secteur {fiche.get('secteur') or 'non précisé'}
- Taille visée : {fiche['taille']} répondants ; durée de collecte : {fiche['duree']} jours

Produis :
1. « contexte » : 4 paragraphes (contexte, manque de données, apport du baromètre, mandat de Datatym). Mets en **gras** l'essentiel.
2. « objectifs_specifiques » : 5 à 7 objectifs, une phrase chacun.
3. « indicateurs » : 8 à 12 indicateurs adaptés au thème, répartis en 3 ou 4 blocs. Types autorisés :
   jugement (échelle très bon → très mauvais), evolution (6 derniers mois), perspective (6 prochains mois),
   satisfaction (1 à 5), intention (oui certainement → non certainement pas), multiple (3 réponses max, 5 à 8 options), unique.
   « objet » complète la question type (ex. « le niveau d'activité de votre entreprise ») ; pour intention, un verbe à l'infinitif.
   « question » : formulation simple et directe, adaptée à un répondant de la cible ; « options » vide sauf pour multiple/unique.
   « niveau » : direction (dirigeants, responsables) ou operationnel (vendeurs, agents) ou tous. Le questionnaire doit tenir en 15 minutes.
   « dans_indice » : vrai pour 3 à 5 indicateurs de type jugement/evolution/perspective qui composent l'indice synthétique.
4. « nom_indice » : nom court de l'indice synthétique.

Pour repère, la banque Datatym propose pour ce type de thème :
{exemple}"""
    res = llm.generer_json(consigne, schema)
    if not res or not res.get("indicateurs"):
        return None
    inds, composantes = [], []
    for k, it in enumerate(res["indicateurs"], 1):
        ind = {"id": f"I{k:02d}", "actif": True, "libelle": it["libelle"], "type": it["type"], "objet": it["objet"],
               "bloc": it["bloc"], "niveau": it["niveau"], "sens": it["sens"], "definition": it["definition"]}
        if it["type"] in ("multiple", "unique"):
            ind["options"] = it["options"] or ["Autre"]
        if it.get("question"):
            ind["question"] = it["question"]
        if it.get("dans_indice") and it["type"] in ("jugement", "evolution", "perspective", "satisfaction"):
            composantes.append(ind["id"])
        inds.append(ind)
    inds.insert(0, {"id": "I00", "libelle": res["nom_indice"] or "Indice synthétique", "type": "indice", "bloc": "Synthèse",
                    "niveau": "tous", "actif": True, "composantes": composantes, "objet": "", "sens": "",
                    "definition": f"Indicateur synthétique du baromètre, calculé à partir de {len(composantes)} soldes d'opinion."})
    return {"contexte": res["contexte"], "objectifs_specifiques": res["objectifs_specifiques"], "indicateurs": inds, "redaction": "ia"}


def generer(projet):
    fiche = projet["fiche"]
    indicateurs, dom = indicateurs_par_defaut(fiche)
    data = None
    if llm.disponible():
        data = _avec_ia(fiche, dom, indicateurs)
    if not data:
        data = {"contexte": contexte_regles(fiche, dom), "objectifs_specifiques": objectifs_regles(fiche, indicateurs),
                "indicateurs": indicateurs, "redaction": "regles"}
    data["domaine"] = dom["libelle"]
    data["profils"] = profils_depuis_cible(fiche["cible"])
    data["points_a_valider"] = [
        "Liste définitive des indicateurs et composition de l'indice synthétique.",
        "Répartition de l'échantillon entre zones et profils.",
        "Outil de collecte retenu (" + ("KoboToolbox" if fiche.get("outil") == "kobo" else "QuestionPro") + ") et mode de passation dominant.",
        "Calendrier de restitution et diffusion des résultats.",
    ]
    return data


def normaliser(data):
    """Recalcule les éléments dérivés après une édition des paramètres."""
    for k, ind in enumerate(data.get("indicateurs", [])):
        ind.setdefault("id", f"I{k:02d}")
        ind.setdefault("actif", True)
        ind.setdefault("niveau", "tous")
        ind.setdefault("bloc", "Résultats")
        if ind.get("type") not in TYPES:
            ind["type"] = "jugement"
        if not ind.get("definition"):
            ind["definition"] = definition_auto(ind)
    actifs = {i["id"] for i in data.get("indicateurs", []) if i.get("actif", True)}
    for ind in data.get("indicateurs", []):
        if ind["type"] == "indice":
            ind["composantes"] = [c for c in ind.get("composantes", []) if c in actifs]
    return data


def indicateurs_actifs(data):
    return [i for i in data.get("indicateurs", []) if i.get("actif", True)]


def calendrier_indicatif(fiche):
    d = debut_collecte(fiche)
    fin = d + timedelta(days=int(fiche["duree"]) - 1)
    return [
        ["Cadrage et questionnaire", f"jusqu'au {date_fr(d - timedelta(days=10))}", "Note de cadrage, questionnaire, formulaires validés"],
        ["Recrutement et formation", f"{date_fr(d - timedelta(days=9))} – {date_fr(d - timedelta(days=1))}", "Enquêteurs recrutés et formés, pré-test"],
        ["Collecte", f"{date_fr(d)} – {date_fr(fin)}", f"{fiche['taille']} questionnaires, suivi quotidien"],
        ["Traitement et analyse", f"{date_fr(fin + timedelta(days=1))} – {date_fr(fin + timedelta(days=10))}", "Base nettoyée, indicateurs calculés"],
        ["Rapport et restitution", f"{date_fr(fin + timedelta(days=11))} – {date_fr(fin + timedelta(days=17))}", "Rapport d'analyse, note de suivi"],
    ]


def construire_docs(projet, data):
    fiche = projet["fiche"]
    profils = data.get("profils") or profils_depuis_cible(fiche["cible"])
    inds = indicateurs_actifs(data)
    zones = decouper(fiche["zones"])
    n = fiche["taille"]
    par_profil = repartir(n, [1] * len(profils))
    par_zone = repartir(n, [1] * len(zones)) if zones else []
    lib_profil = {p_["code"]: p_["libelle"] for p_ in profils}

    lignes_ind = []
    for i in inds:
        profs = "Tous" if i["type"] == "indice" else ", ".join(lib_profil[c] for c in profils_concernes(i, profils))
        lignes_ind.append([i["id"], i["libelle"], i.get("definition", ""), TYPES[i["type"]]["libelle"], profs])
    indice = next((i for i in inds if i["type"] == "indice"), None)
    noms = {i["id"]: i["libelle"] for i in inds}

    blocs_q = {}
    for i in inds:
        if i["type"] != "indice":
            blocs_q.setdefault(i["bloc"], []).append(i["libelle"])

    precision = [["Global", str(n), fmt_marge(n)]]
    for p_, k in zip(profils, par_profil):
        precision.append([f"Profil : {p_['libelle']}", str(k), fmt_marge(k)])
    if len(zones) > 1:
        precision.append([f"Par {'pays' if sont_des_pays(zones) else 'zone'} (moyenne)", str(n // len(zones)), fmt_marge(n // len(zones))])

    sections = [
        section("contexte", "1. Contexte et justification", [p(t) for t in data.get("contexte", [])]),
        section("objectifs", "2. Objectifs de l'étude", [
            p(f"**Objectif général :** {fiche['objectif']}."),
            p("Objectifs spécifiques :"),
            liste(data.get("objectifs_specifiques", [])),
        ]),
        section("cible", "3. Cible, champ et taille de l'échantillon", [
            tableau(["Paramètre", "Valeur retenue"], [
                ["Thème", fiche["theme"]], ["Objectif", fiche["objectif"]], ["Cible", fiche["cible"]],
                ["Champ géographique", f"{resume_champ(zones)} : {', '.join(zones)}" if sont_des_pays(zones) else ", ".join(zones)],
                ["Secteur", fiche.get("secteur") or "Secteur formel"],
                ["Taille visée", f"{n} répondants"], ["Durée de collecte", f"{fiche['duree']} jours"],
            ], "Paramètres du baromètre", [1, 2.4]),
            tableau(["Profil", "Niveau", "Effectif indicatif"],
                    [[p_["libelle"], "Direction" if p_["niveau"] == "direction" else "Opérationnel", str(k)] for p_, k in zip(profils, par_profil)],
                    "Profils de répondants et répartition indicative"),
            tableau(["Niveau de lecture", "Effectif", "Marge d'erreur (IC 95 %)"], precision, "Précision statistique attendue"),
        ], source="auto"),
        section("indicateurs", "4. Indicateurs recherchés", [
            p("Les indicateurs ci-dessous constituent la base de l'ensemble des livrables : chacun est rattaché à une ou plusieurs questions, "
              "à des variables du dictionnaire et à un mode de calcul. Retirer un indicateur le retire du questionnaire et du dictionnaire."),
            tableau(["Code", "Indicateur", "Définition", "Type de mesure", "Profils interrogés"], lignes_ind,
                    "Liste des indicateurs recherchés", [0.6, 2, 3, 1.6, 1.4], 9),
        ] + ([p(f"**{indice['libelle']}** : " + TYPES['indice']['calcul'] + " Composantes : "
                + "; ".join(noms.get(c, c) for c in indice.get("composantes", [])) + ".", "encadre")] if indice else []),
            source="auto"),
        section("architecture", "5. Architecture du questionnaire", [
            p("Le questionnaire est organisé en blocs thématiques, précédés d'un bloc d'identification (zone, profil) et suivis d'une clôture. "
              "Les formulations sont simples ; la durée de remplissage est plafonnée à 15 minutes. Deux versions sont produites : "
              "terrain (administrée par l'enquêteur) et digitale (remplie par le répondant)."),
            tableau(["Bloc", "Indicateurs mesurés", "Nombre"], [[b, "\n".join(l), str(len(l))] for b, l in blocs_q.items()],
                    "Blocs du questionnaire", [1.2, 3, 0.6]),
        ], source="auto"),
        section("methode", "6. Méthode de collecte et de contrôle", [
            liste([
                "**Méthode :** échantillonnage non probabiliste par quotas (zone × profil).",
                f"**Outil :** formulaire {'KoboToolbox' if fiche.get('outil') == 'kobo' else 'QuestionPro'} sur smartphone ou tablette, avec mode hors ligne ; version digitale en auto-administration.",
                "**Suivi :** tableau de bord Datatym mis à jour à partir des soumissions (avancement par enquêteur, zone et quota).",
                "**Contrôle qualité :** rejet des questionnaires trop rapides, contrôle de cohérence, rappel de vérification sur 10 % des répondants.",
                "**Traitement :** nettoyage et calcul des indicateurs sous Python, R ou Stata ; dépôt des bases nettoyées sur l'espace DATA de Datatym.",
                "**Éthique :** consentement explicite, confidentialité des réponses, aucun résultat nominatif publié.",
            ]),
        ]),
        section("livrables", "7. Livrables et calendrier indicatif", [
            tableau(["Livrable", "Contenu"], [
                ["Note de cadrage", "Le présent document, validé avant le questionnaire"],
                ["Questionnaire", "Versions terrain et digitale, dictionnaire des variables, XLSForm Kobo, import QuestionPro"],
                ["Note d'échantillonnage", "Quotas, répartition par enquêteur, calendrier, coûts, note de recrutement, formation"],
                ["Note méthodologique", "Synthèse de la méthode, des outils et du calcul des indicateurs"],
                ["Tableau de bord et note de suivi", "Suivi de la collecte, réalisé contre prévu, qualité des données"],
                ["Rapport d'analyse", "Résultats par indicateur, graphiques, lecture par profil, enseignements"],
            ], "Livrables du baromètre", [1.2, 3]),
            tableau(["Phase", "Période", "Résultat attendu"], calendrier_indicatif(fiche), "Calendrier indicatif", [1.3, 1.8, 2]),
        ], source="auto"),
    ]
    if fiche.get("cout"):
        c = fiche["cout"]
        sections.append(section("budget", "8. Enveloppe budgétaire", [
            p(f"L'enveloppe estimée s'élève à **{fcfa(c)}**, soit environ {fcfa(c / max(n, 1))} par questionnaire réalisé. "
              "Sa répartition détaillée figure dans la note d'échantillonnage."),
        ], source="auto"))
    sections.append(section("points", f"{len(sections) + 1}. Points à valider", [liste(["☐ " + x for x in data.get("points_a_valider", [])])]))

    modele = {
        "titre": "Note de cadrage", "surtitre": "Baromètre Datatym", "sous_titre": fiche["theme"],
        "meta": [f"{n} répondants · {', '.join(zones)} · {fiche['duree']} jours de collecte",
                 f"Version du {aujourdhui()} — document de travail"],
        "en_tete": f"Baromètre {fiche['theme']} — Note de cadrage", "sections": sections,
    }
    return {"note_cadrage": modele}
