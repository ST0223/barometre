"""Étape 1 — Note de cadrage : contexte, objectifs, cible, indicateurs recherchés."""
from datetime import timedelta

from .. import budget, llm
from ..banque import (DOMAINES, ESPACE_DU_PAYS, TYPES, decouper, slug, definition_auto, indicateurs_par_defaut, poids_profil, profils_concernes,
                      profils_depuis_cible, resume_champ, sont_des_pays)
from ..charte import liste, p, section, tableau, chiffres
from ..outils import date_fr, debut_collecte, fcfa, fmt_marge, nombre, repartir, aujourdhui

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
    data["theme_ref"] = [fiche["theme"], fiche["objectif"]]
    data["profils"] = profils_depuis_cible(fiche["cible"])
    data["points_a_valider"] = generer_points(fiche)
    return data


def generer_points(fiche):
    return [
        "Liste définitive des indicateurs et composition de l'indice synthétique.",
        "Répartition de l'échantillon entre zones et profils.",
        "Outil de collecte retenu (" + ("KoboToolbox" if fiche.get("outil") == "kobo" else "QuestionPro") + ") et mode de passation dominant.",
        "Calendrier de restitution et diffusion des résultats.",
    ]


def actualiser(projet, data):
    """Mise à jour après une modification de la fiche : les textes tirés du thème suivent toujours ;
    les indicateurs ne sont remplacés que si le domaine du baromètre a changé (sinon les retouches restent)."""
    fiche = projet["fiche"]
    ref = (fiche["theme"], fiche["objectif"])
    if tuple(data.get("theme_ref") or ()) == ref:
        return data, False
    if data.get("redaction") == "importee" or data.get("domaine") == "Importé":
        # étude lancée depuis une note fournie : indicateurs, contexte et objectifs viennent de la note, jamais remplacés
        data["theme_ref"] = list(ref)
        return data, False
    inds, dom = indicateurs_par_defaut(fiche)
    change_domaine = dom["libelle"] != data.get("domaine")
    if change_domaine:
        data["indicateurs"], data["domaine"] = inds, dom["libelle"]
    data["contexte"] = contexte_regles(fiche, dom)
    data["objectifs_specifiques"] = objectifs_regles(fiche, data["indicateurs"])
    data["redaction"] = "regles"
    data["theme_ref"] = list(ref)
    return data, change_domaine


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


def _sous_titre(texte):
    return {"type": "titre", "texte": texte, "niveau": 2}


def _champ_par_espace(zones, par_zone):
    """Lignes « Zone | Pays | Répondants » : pays regroupés par espace (UEMOA, CEMAC…)."""
    groupes = {}
    for z, k in zip(zones, par_zone):
        groupes.setdefault(ESPACE_DU_PAYS.get(slug(z), "Autres pays"), []).append((z, k))
    lignes = []
    for esp, l in groupes.items():
        effectifs = {k for _, k in l}
        total = sum(k for _, k in l)
        lignes.append([esp, ", ".join(z for z, _ in l),
                       f"{len(l)} × {nombre(l[0][1], 0)} = {nombre(total, 0)}" if len(effectifs) == 1 and len(l) > 1 else nombre(total, 0)])
    return lignes


def construire_docs(projet, data):
    """Note de cadrage : contexte, objectifs, périmètre et cible (pays, effectifs, éligibilité, précision), principes
    méthodologiques, indicateurs et questionnaire, livrables, gouvernance, planning, budget, cadre éthique, risques,
    décisions à prendre. Une section reprise d'une note fournie (data « sections_importees ») remplace le texte par défaut."""
    fiche = projet["fiche"]
    profils = data.get("profils") or profils_depuis_cible(fiche["cible"])
    inds = indicateurs_actifs(data)
    zones = decouper(fiche["zones"])
    n = fiche["taille"]
    pays = sont_des_pays(zones)
    mot = "pays" if pays else "zone"
    # poids de chaque profil (parts de l'échantillon, ex. 70 / 20 / 10) ; à parts égales par défaut
    par_profil = repartir(n, [poids_profil(p_) for p_ in profils])
    par_zone = repartir(n, [1] * len(zones)) if zones else []
    lib_profil = {p_["code"]: p_["libelle"] for p_ in profils}
    importees = data.get("sections_importees") or {}
    comm = (fiche.get("commanditaire") or "").strip() or "Commanditaire"
    outil = "KoboToolbox" if fiche.get("outil") == "kobo" else "QuestionPro"

    lignes_ind = []
    for i in inds:
        profs = "Tous" if i["type"] == "indice" else ", ".join(lib_profil[c] for c in profils_concernes(i, profils))
        code = f"{i['id']} ({i['code_origine']})" if i.get("code_origine") else i["id"]
        lignes_ind.append([code, i["libelle"], i.get("definition", ""), TYPES[i["type"]]["libelle"], profs])
    indice = next((i for i in inds if i["type"] == "indice"), None)
    noms = {i["id"]: i["libelle"] for i in inds}
    blocs_q = {}
    for i in inds:
        if i["type"] != "indice":
            blocs_q.setdefault(i["bloc"], []).append(i["libelle"])

    precision = [["Global", nombre(n, 0), fmt_marge(n)]]
    if len(zones) > 1:
        precision.append([f"Par {mot} (moyenne)", nombre(n // len(zones), 0), fmt_marge(n // len(zones))])
    for p_, k in zip(profils, par_profil):
        precision.append([f"Profil : {p_['libelle']}", nombre(k, 0), fmt_marge(k)])
        if len(zones) > 1 and len(profils) > 1 and k // len(zones):
            precision.append([f"{p_['libelle']} d'un même {mot} (moyenne)", nombre(k // len(zones), 0), fmt_marge(k // len(zones))])

    # 3.3 éligibilité : les réponses qui mettent fin au questionnaire
    eligibilite = []
    for i in inds:
        if i.get("exclut"):
            libs = {str(o.get("code")): o.get("label") for o in i.get("options", []) if isinstance(o, dict)}
            if not libs:
                libs = {str(k): (o if isinstance(o, str) else o.get("label")) for k, o in enumerate(i.get("options", []), 1)}
            exclus = " ou ".join(f"« {libs.get(str(c), c)} »" for c in i["exclut"])
            eligibilite.append(f"**{i['libelle']}** : le questionnaire s'arrête si la réponse est {exclus}.")
    eligibilite = eligibilite or [f"Appartenir à l'un des profils de la cible : {', '.join(p_['libelle'] for p_ in profils)}."]

    marges = f"environ {fmt_marge(n)} au global" + (f", {fmt_marge(n // len(zones))} par {mot}" if len(zones) > 1 else "")
    defaut = {
        "principes": [
            liste([
                f"**Collecte :** un questionnaire unique pour l'ensemble des profils, avec des parcours filtrés selon le profil et les réponses ; "
                f"formulaire {outil}, en version terrain (administrée par un enquêteur) et en version digitale (auto-administrée).",
                f"**Échantillon par quotas** croisant le {mot} et le profil du répondant ; les quotas sont suivis chaque jour sur le tableau de bord.",
                "**Bases minimales :** aucun résultat n'est publié sur moins de 30 répondants ; entre 30 et 100, il est présenté comme une tendance.",
                "**Contrôle qualité continu :** questionnaires trop rapides, doublons, cohérence des réponses, rappels de contrôle.",
                "**Traitement sous contrôle humain :** nettoyage, calcul des indicateurs et rédaction sont vérifiés par un analyste ; "
                "chaque correction est consignée dans un journal.",
            ]),
            p(f"**À retenir :** l'échantillon n'est pas probabiliste. Les marges d'erreur sont donc indicatives : {marges}. "
              "Elles sont publiées avec chaque résultat.", "encadre"),
        ],
        "livrables": [
            tableau(["Livrable", "Contenu"], [
                ["Note de cadrage", "Le présent document, validé avant le questionnaire"],
                ["Questionnaire", "Versions terrain et digitale, dictionnaire des variables, "
                                  + ("formulaire XLSForm pour KoboToolbox" if fiche.get("outil") == "kobo" else "fichier d'import QuestionPro")],
                ["Note d'échantillonnage", "Quotas, répartition par enquêteur, calendrier, annonce de recrutement, demande aux RH, formation"],
                ["Note méthodologique", "Échantillonnage, collecte, précision, indicateurs, contrôle qualité, protection des données, limites"],
                ["Base de données apurée", "Base finale figée, dictionnaire des variables, journal des corrections"],
                ["Tableau de bord et note de suivi", "Suivi de la collecte, réalisé contre prévu, qualité des données"],
                ["Rapport d'analyse et restitution", "Résultats par indicateur, lecture par profil et par " + mot + ", synthèse, présentation"],
            ], "Livrables de l'étude", [1.3, 3]),
        ],
        "gouvernance": [
            tableau(["Instance ou rôle", "Responsabilités"], [
                [comm, "Valide le cadrage, le questionnaire, les règles de publication et les messages publiés"],
                ["Chef de projet Datatym", "Planning, quotas, qualité ; point hebdomadaire avec le commanditaire"],
                ["Superviseurs" + (" pays" if pays else ""), "Équipes d'enquête, diffusion des liens, contrôle de terrain"],
                ["Analystes Datatym", "Nettoyage, indicateurs, analyses, rédaction"],
            ], "Gouvernance de l'étude", [1.3, 3]),
            p("**Règle d'indépendance :** Datatym est seul responsable des calculs. Le commanditaire valide la présentation et les "
              "messages, mais ne modifie pas les résultats."),
        ],
        "ethique": [
            liste([
                "Consentement explicite recueilli avant toute question ; le refus met fin à l'entretien.",
                "Aucune donnée nominative publiée ; les coordonnées laissées en fin de questionnaire servent seulement aux rappels "
                "de contrôle et à l'envoi des résultats, puis sont supprimées.",
                "Données pseudonymisées avant tout traitement par un outil d'intelligence artificielle.",
                "Respect de la loi sur la protection des données personnelles de chaque " + mot + " d'enquête.",
            ]),
        ],
        "risques": [
            tableau(["Risque", "Parade"], [
                ["Quotas non atteints dans un " + mot + " ou un profil", "Suivi quotidien des quotas, réallocation à mi-parcours, réserves d'enquêteurs"],
                ["Questionnaires de mauvaise qualité", "Contrôle de durée, de cohérence et des doublons ; rappels de contrôle ; paiement au questionnaire validé"],
                ["Faible participation de certains profils", "Relances ciblées, rendez-vous, prolongation limitée de la collecte"],
                ["Retard du terrain", "Calendrier suivi chaque jour, renfort par les réserves, priorisation des quotas en retard"],
            ], "Risques et parades", [1.6, 2.6]),
        ],
        "decisions": [
            tableau(["Décision", "Qui décide", "Échéance"],
                    [[x, comm, "Avant le terrain"] for x in data.get("points_a_valider", [])] or [["Validation de la note de cadrage", comm, "Avant le questionnaire"]],
                    "Décisions à prendre", [3, 1.2, 1.1]),
        ],
    }

    est = data.get("estimation") or budget.estimer_cadrage(fiche)
    blocs_budget = [
        p(f"Sur la base des paramètres de la fiche et des coûts unitaires de référence de Datatym, le coût de revient du baromètre "
          f"est estimé **entre {fcfa(est['bas'])} et {fcfa(est['haut'])}**, pour une estimation centrale de **{fcfa(est['central'])}**, "
          f"soit environ {fcfa(est['par_questionnaire'])} par questionnaire validé."),
        tableau(["Scénario", "Hypothèse de terrain", "Enquêteurs", "Coût total", "Par questionnaire"],
                [[s["nom"], s["hypothese"], str(s["nb_enqueteurs"]), fcfa(s["total"]), fcfa(s["par_questionnaire"])] for s in est["scenarios"]],
                "Estimation préliminaire du coût de revient", [0.8, 2.6, 0.9, 1.3, 1.2], 9.5),
    ]
    if est.get("plafond"):
        blocs_budget.append(p(
            f"Le plafond budgétaire fixé ({fcfa(est['plafond'])}) "
            + ("couvre l'ensemble de la fourchette." if est["dans_plafond"]
               else "est inférieur à l'estimation basse : le plan devra être revu (zones, taille ou durée) avant le lancement."
               if est["plafond_court"] else "couvre le scénario central mais pas le scénario haut : le plan de collecte devra le confirmer."),
            "encadre"))
    blocs_budget.append(p("Ordre de grandeur : chaque scénario repose sur les hypothèses indiquées. Le budget détaillé est établi avec le plan de collecte, "
                          "à partir des quotas, du nombre d'enquêteurs et du calendrier retenus ; le coût réel est arrêté à la clôture.", "note"))

    def contenu(cle, blocs_auto):
        """Section reprise de la note fournie si elle existe ; le budget et le planning gardent en plus le calcul de la plateforme."""
        if cle in importees:
            return importees[cle] + (blocs_budget if cle == "budget" else []), "texte"
        return blocs_auto, ("auto" if cle in ("budget", "planning") else "texte")

    plan = [
        ("contexte", "Contexte et justification", [p(t) for t in data.get("contexte", [])], "texte"),
        ("objectifs", "Objectifs", [
            p(f"**Objectif général.** {fiche['objectif'].rstrip('.')}."),
            p("**Objectifs spécifiques.**"),
            liste(data.get("objectifs_specifiques", [])),
        ], "texte"),
        ("perimetre", "Périmètre et cible", [
            _sous_titre(f"{{n}}.1 {'Pays' if pays else 'Zones d’enquête'}"),
            tableau(["Zone" if pays else "Ensemble", "Pays" if pays else "Zones", "Répondants"],
                    _champ_par_espace(zones, par_zone) if pays else [["Champ", ", ".join(zones), nombre(n, 0)]], f"Champ géographique"),
            _sous_titre("{n}.2 Population cible et effectifs"),
            tableau(["Profil", "Niveau", f"Par {mot} (moyenne)" if len(zones) > 1 else "Effectif", "Total"],
                    [[p_["libelle"], "Direction" if p_["niveau"] == "direction" else "Opérationnel",
                      nombre(k // max(len(zones), 1), 0), nombre(k, 0)] for p_, k in zip(profils, par_profil)]
                    + [["Total", "", nombre(n // max(len(zones), 1), 0), nombre(n, 0)]], "Population cible et effectifs", [2.6, 1, 1, 0.8]),
            _sous_titre("{n}.3 Critères d'éligibilité"),
            liste(eligibilite),
            _sous_titre("{n}.4 Précision attendue"),
            tableau(["Niveau de lecture", "Effectif", "Marge d'erreur (IC 95 %)"], precision, "Précision statistique attendue", [3, 0.8, 1.2]),
        ], "auto"),
        ("principes", "Principes méthodologiques", defaut["principes"], None),
        ("indicateurs", "Indicateurs et questionnaire", [
            p("Les indicateurs ci-dessous constituent la base de l'ensemble des livrables : chacun est rattaché à une ou plusieurs questions, "
              "à des variables du dictionnaire et à un mode de calcul. Retirer un indicateur le retire du questionnaire et du dictionnaire."),
            tableau(["Code", "Indicateur", "Définition", "Type de mesure", "Profils interrogés"], lignes_ind,
                    "Liste des indicateurs recherchés", [0.8, 2, 3, 1.5, 1.4], 9),
        ] + ([p(f"**{indice['libelle']}** : " + (TYPES['indice']['calcul'] + " Composantes : "
                + "; ".join(noms.get(c, c) for c in indice["composantes"]) + "." if indice.get("composantes")
                else indice.get("definition", "")), "encadre")] if indice else []) + [
            _sous_titre("{n}.1 Architecture du questionnaire"),
            p("Le questionnaire est organisé en blocs thématiques, précédés d'un bloc d'identification et suivis d'une clôture. "
              "Deux versions sont produites : terrain (administrée par l'enquêteur) et digitale (remplie par le répondant)."),
            tableau(["Bloc", "Indicateurs mesurés", "Nombre"], [[b, "\n".join(l), str(len(l))] for b, l in blocs_q.items()],
                    "Blocs du questionnaire", [1.2, 3, 0.6]),
        ], "auto"),
        ("livrables", "Livrables", defaut["livrables"], None),
        ("gouvernance", "Gouvernance", defaut["gouvernance"], None),
        ("planning", "Planning", [tableau(["Phase", "Période", "Résultat attendu"], calendrier_indicatif(fiche), "Calendrier indicatif", [1.3, 1.8, 2])], None),
        ("budget", "Budget", blocs_budget, None),
        ("ethique", "Cadre éthique et légal", defaut["ethique"], None),
        ("risques", "Risques et parades", defaut["risques"], None),
        ("decisions", "Décisions à prendre", defaut["decisions"], None),
    ]
    sections = []
    for k, (cle, titre, blocs_auto, source) in enumerate(plan, 1):
        blocs, src = (blocs_auto, source) if source else contenu(cle, blocs_auto)
        blocs = [dict(b, texte=b["texte"].replace("{n}", str(k))) if b.get("type") == "titre" else b for b in blocs]
        sections.append(section(cle, f"{k}. {titre}", blocs, source=src))
    modele = {
        "titre": "Note de cadrage", "sous_titre": fiche["theme"],
        "meta": [f"{n} répondants · {', '.join(zones)} · {fiche['duree']} jours de collecte", f"Version du {aujourdhui()} — document de travail"],
        "en_tete": f"Baromètre {fiche['theme']} — Note de cadrage", "sections": sections,
    }
    return {"note_cadrage": modele}
