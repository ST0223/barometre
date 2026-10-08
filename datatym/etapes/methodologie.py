"""Étape 4 — Note méthodologique : consolidation automatique des étapes 1 à 3."""
import math
from datetime import date

from ..banque import TYPES
from ..charte import liste, p, section, tableau
from ..outils import aujourdhui, date_fr, fmt_marge

DOCS = {"note_methodologique": ("NoteMethodologique", "Note méthodologique")}


def generer(projet, precedent=None):
    prec = precedent or {}
    return {
        "logiciel": prec.get("logiciel", "Python (VS Code)"),
        "limites": prec.get("limites") or [
            "L'échantillon par quotas décrit la population interrogée ; il ne permet pas d'extrapolation statistique stricte à l'ensemble de la population de référence.",
            "Les réponses sont déclaratives : elles traduisent des perceptions, susceptibles d'un biais de désirabilité sociale.",
            "Les résultats par sous-groupe de moins de 30 répondants ne sont pas publiés ; entre 30 et 100, ils sont présentés comme des tendances.",
        ],
    }


def construire_docs(projet, data, cadrage, quest, ech):
    fiche = projet["fiche"]
    outil = "KoboToolbox (application KoboCollect)" if fiche.get("outil") == "kobo" else "QuestionPro (application hors ligne)"
    lib = {pr["code"]: pr["libelle"] for pr in quest["profils"]}
    jours = [date.fromisoformat(j) for j in ech["jours"]]
    n = fiche["taille"]
    inds = [i for i in cadrage["indicateurs"] if i.get("actif", True)]
    noms = {i["id"]: i["libelle"] for i in inds}

    lignes_ind = []
    for i in inds:
        if i["type"] == "indice":
            src = "Composantes : " + ", ".join(i.get("composantes", []))
        else:
            src = ", ".join(f"{q['num']} ({q['var']})" for q in quest["questions_plates"] if q.get("indicateur") == i["id"])
        lignes_ind.append([i["id"], i["libelle"], src, TYPES[i["type"]]["calcul"]])
    q = {(z, c): v for z, c, v in ech["quotas"]}
    tot_prof = {c: sum(q[(z, c)] for z in ech["zones"]) for c in lib}

    sections = [
        section("objet", "1. Objet de la note", [
            p(f"Cette note décrit la méthode du baromètre « {fiche['theme']} » : échantillonnage, conception du questionnaire, "
              "indicateurs, outils d'enquête, collecte, traitement et analyse. Elle consolide les décisions validées dans la note de "
              "cadrage, le questionnaire et la note d'échantillonnage."),
            p(f"**Objectif de l'étude :** {fiche['objectif']}."),
        ], source="auto"),
        section("methode", "2. Méthode retenue", [
            p("Le baromètre repose sur une **enquête quantitative par questionnaire**, selon une méthode d'échantillonnage "
              "**non probabiliste par quotas**. Les quotas croisent la zone d'enquête et le profil du répondant, afin de garantir "
              "une base suffisante pour chaque lecture prévue dans le rapport."),
            p("Cette méthode est adaptée lorsque la base de sondage exhaustive n'est pas disponible. Elle impose une lecture prudente "
              "des écarts entre sous-groupes, présentée avec les marges d'erreur indicatives."),
        ], source="auto"),
        section("echantillon", "3. Échantillonnage", [
            tableau(["Élément", "Valeur"], [
                ["Population cible", fiche["cible"]], ["Champ géographique", ", ".join(ech["zones"])],
                ["Secteur", fiche.get("secteur") or "Secteur formel"], ["Taille de l'échantillon", f"{n} répondants"],
                ["Nombre d'enquêteurs", str(ech["nb_enqueteurs"])],
                ["Productivité retenue", f"{ech['params']['rendement']} questionnaires par enquêteur et par jour"],
            ], "Paramètres d'échantillonnage", [1.3, 2.5]),
            tableau(["Profil", "Effectif", "Marge d'erreur (IC 95 %)"],
                    [[lib[c], str(v), fmt_marge(v)] for c, v in tot_prof.items()] + [["Ensemble", str(n), fmt_marge(n)]],
                    "Effectifs et précision par profil"),
        ], source="auto"),
        section("questionnaire", "4. Conception du questionnaire", [
            liste([
                f"**Structure :** {len(quest['sections'])} sections et {len(quest['questions_plates'])} questions, de l'identification du répondant à la clôture.",
                f"**Deux versions :** terrain (administrée par l'enquêteur, environ {math.ceil(max(quest['duree_terrain'].values()))} minutes) "
                f"et digitale (auto-administrée, environ {math.ceil(max(quest['duree_digital'].values()))} minutes). Plafond : 15 minutes.",
                "**Adaptation au profil :** certaines questions ne sont posées qu'aux profils concernés (filtres automatiques).",
                "**Formulations :** simples et directes, avec des échelles identiques d'une édition à l'autre pour permettre le suivi.",
                "**Consentement :** message propre au baromètre, mentionnant Datatym comme responsable de l'étude et la durée estimée.",
                "**Dictionnaire :** chaque variable est documentée (nom, libellé, type, modalités, indicateur rattaché).",
            ]),
        ], source="auto"),
        section("indicateurs", "5. Indicateurs et mode de calcul", [
            tableau(["Code", "Indicateur", "Questions (variables)", "Mode de calcul"], lignes_ind, "Indicateurs du baromètre", [0.5, 1.6, 1.3, 3], 8.5),
            p("Les soldes d'opinion sont exprimés en points (de −100 à +100). Les taux sont calculés sur les répondants concernés par "
              "la question, hors non-réponses, et arrondis à l'unité.", "note"),
        ], source="auto"),
        section("outils", "6. Outils d'enquête et système de suivi", [
            liste([
                f"**Collecte :** {outil}, sur smartphone ou tablette, avec saisie hors ligne et envoi quotidien.",
                "**Formulaires :** fichier XLSForm pour KoboToolbox et fichier d'import pour QuestionPro, générés depuis le questionnaire validé.",
                "**Suivi :** tableau de bord de la plateforme Datatym, alimenté par les soumissions : avancement par enquêteur, par zone et par quota, écarts au calendrier.",
            ]),
        ], source="auto"),
        section("collecte", "7. Déroulement de la collecte", [
            liste([
                f"**Période :** du {date_fr(jours[0])} au {date_fr(jours[-1])} ({len(jours)} jours de collecte).",
                "**Formation :** une journée de formation et de pré-test la veille du démarrage.",
                "**Supervision :** point quotidien sur le réalisé, réallocation des quotas à mi-parcours si nécessaire.",
                "**Contrôle qualité :** rejet des entretiens d'une durée inférieure à 40 % de la durée médiane, contrôle de cohérence, rappel de 10 % des répondants.",
            ]),
        ], source="auto"),
        section("traitement", "8. Traitement, analyse et dépôt des données", [
            liste([
                f"**Logiciel :** traitement et analyse sous {data.get('logiciel', 'Python (VS Code)')} ; scripts reproductibles d'une édition à l'autre.",
                "**Nettoyage :** suppression des doublons, des refus et des hors-cible ; application des règles de contrôle qualité.",
                "**Calcul :** indicateurs selon les modes de calcul ci-dessus, lecture globale, par profil et par zone.",
                "**Dépôt :** bases nettoyées et dictionnaire des variables déposés sur l'espace DATA du site Datatym.",
            ]),
        ]),
        section("limites", "9. Limites", [liste(data.get("limites", []))]),
    ]
    return {"note_methodologique": {
        "titre": "Note méthodologique", "surtitre": "Baromètre Datatym", "sous_titre": fiche["theme"],
        "meta": [f"{n} répondants · {', '.join(ech['zones'])} · {len(jours)} jours", f"Version du {aujourdhui()}"],
        "en_tete": f"Baromètre {fiche['theme']} — Note méthodologique", "sections": sections,
    }}
