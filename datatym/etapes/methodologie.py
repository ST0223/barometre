"""Étape 4 — Note méthodologique : consolidation automatique des étapes 1 à 3."""
import math
import re
from datetime import date

from .. import deroulement, indice_hc
from ..banque import TYPES, du_barometre, sont_des_pays
from ..charte import liste, p, section, tableau
from ..outils import aujourdhui, date_fr, fmt_marge, nombre

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

    hyp = ech["params"].get("hypotheses") or {}
    en_ligne = hyp.get("formation", "en_ligne") == "en_ligne"
    a_distance = hyp.get("supervision", "distance") == "distance"
    rappels = int(hyp.get("part_rappels", 10))
    zones = ech["zones"]
    pays = sont_des_pays(zones)
    Z = "Pays" if pays else "Zone"
    n_res = len(ech.get("reserves") or []) or sum((ech.get("reserve") or {}).values())
    rec = ech.get("recrutement") or {}
    poids = ech["params"].get("poids_zones") or {}
    egal = len(set(poids.values())) <= 1
    conditionnelles = [x for x in quest["questions_plates"] if x.get("conditions")]
    exclusions = [x for x in quest["questions_plates"] if x.get("exclut")]
    controle = (projet["etapes"]["collecte"].get("data") or {}).get("controle_qualite", True)
    indice_ia = bool(re.search(r"\bIA\b|intelligence artificielle", fiche["theme"], re.I))
    try:
        phases = deroulement.presenter(projet)["phases"]
    except Exception:  # calendrier indicatif seulement : la note reste produite sans lui
        phases = []
    atouts = "; ".join(a.rstrip(".").lower() for a in rec.get("atouts") or [])

    blocs = [
        ("objet", "Objet de la note", [
            p(f"Cette note décrit la méthode {du_barometre(fiche['theme'])} : échantillonnage, constitution de l'équipe d'enquête, "
              "conception du questionnaire, indicateurs, outils, collecte, contrôle qualité, traitement et protection des données. "
              "Elle consolide les décisions validées dans la note de cadrage, le questionnaire et la note d'échantillonnage."),
            p(f"**Objectif de l'étude :** {fiche['objectif']}."),
        ]),
        ("methode", "Méthode retenue", [
            p("Le baromètre repose sur une **enquête quantitative par questionnaire**, selon une méthode d'échantillonnage "
              "**non probabiliste par quotas**. Les quotas croisent la zone d'enquête et le profil du répondant, afin de garantir "
              "une base suffisante pour chaque lecture prévue dans le rapport."),
            p("Cette méthode est adaptée lorsque la base de sondage exhaustive n'est pas disponible. Elle impose une lecture prudente "
              "des écarts entre sous-groupes, présentée avec les marges d'erreur indicatives."),
        ]),
        ("echantillon", "Échantillonnage", [
            tableau(["Élément", "Valeur"], [
                ["Population cible", fiche["cible"]], ["Champ géographique", ", ".join(zones)],
                ["Secteur", fiche.get("secteur") or "Secteur formel"], ["Taille de l'échantillon", f"{n} répondants"],
                ["Répartition entre " + ("pays" if pays else "zones"), "à parts égales" if egal else "pondérée selon les poids retenus"],
                ["Enquêteurs", f"{ech['nb_enqueteurs']} titulaires" + (f" et {n_res} réserves" if n_res else "")],
                ["Productivité retenue", f"{ech['params']['rendement']} questionnaires par enquêteur et par jour"],
                ["Taux de réalisation attendu", f"{round(float(ech['params'].get('marge', 0.9)) * 100)} % (marge pour les refus et rendez-vous manqués)"],
            ], "Paramètres d'échantillonnage", [1.3, 2.5]),
            tableau([Z, "Effectif", "Marge d'erreur (IC 95 %)"],
                    [[z, str(t), fmt_marge(t)] for z, t in ech["tot_zone"].items()], f"Effectifs et précision par {Z.lower()}"),
            tableau(["Profil", "Effectif", "Marge d'erreur (IC 95 %)"],
                    [[lib[c], str(v), fmt_marge(v)] for c, v in tot_prof.items()] + [["Ensemble", str(n), fmt_marge(n)]],
                    "Effectifs et précision par profil"),
        ]),
        ("equipe", "Constitution de l'équipe d'enquête", [
            liste([
                "**Recrutement :** confié au service des ressources humaines, à partir d'une annonce publiée sur un site d'emploi "
                "avec présélection automatique des candidatures (ATS).",
                f"**Profil :** {rec.get('diplome', 'Bac+3')} minimum, {rec.get('experience', '1 an')} d'expérience d'enquête quantitative, "
                "maîtrise d'un outil de collecte mobile" + (f" ; atouts : {atouts}" if atouts else "") + ".",
                f"**Effectifs :** {ech['nb_enqueteurs']} enquêteurs titulaires" + (f" et {n_res} réserves, formées avec l'équipe et mobilisées "
                "seulement pour remplacer un abandon (elles reprennent alors les quotas restants)" if n_res else "") + ".",
                ("**Affectation :** chaque enquêteur travaille dans son pays de résidence et reçoit un identifiant (ENQ, code du pays, numéro) "
                 "qui sert au suivi de ses questionnaires.") if pays else
                "**Affectation :** chaque enquêteur travaille dans sa zone et reçoit un identifiant qui sert au suivi de ses questionnaires.",
                "**Rémunération :** au questionnaire validé ; un questionnaire écarté au contrôle qualité n'est pas payé, "
                "ce qui aligne l'intérêt de l'enquêteur sur la qualité des données.",
            ]),
        ]),
        ("questionnaire", "Conception du questionnaire", [
            liste([
                f"**Structure :** {len(quest['sections'])} sections et {len(quest['questions_plates'])} questions, de l'identification du répondant à la clôture.",
                f"**Deux versions :** terrain (administrée par l'enquêteur, environ {math.ceil(max(quest['duree_terrain'].values()))} minutes) "
                f"et digitale (auto-administrée, environ {math.ceil(max(quest['duree_digital'].values()))} minutes). Plafond : 15 minutes.",
                "**Adaptation au profil :** certaines questions ne sont posées qu'aux profils concernés (filtres automatiques).",
            ] + ([f"**Conditions d'affichage :** {len(conditionnelles)} question(s) ne s'affichent qu'en fonction d'une réponse précédente."]
                 if conditionnelles else [])
              + ([f"**Questions d'éligibilité :** {len(exclusions)} question(s) mettent fin au questionnaire lorsque le répondant est hors cible ; "
                  "ces entretiens ne sont ni comptés ni payés."] if exclusions else []) + [
                "**Formulations :** simples et directes, avec des échelles identiques d'une édition à l'autre pour permettre le suivi.",
                "**Consentement :** message propre au baromètre, mentionnant Datatym comme responsable de l'étude et la durée estimée.",
                "**Dictionnaire :** chaque variable est documentée (nom, libellé, type, modalités, indicateur rattaché).",
            ]),
        ]),
        ("indicateurs", "Indicateurs et mode de calcul", [
            tableau(["Code", "Indicateur", "Questions (variables)", "Mode de calcul"], lignes_ind, "Indicateurs du baromètre", [0.5, 1.6, 1.3, 3], 8.5),
            p("Les soldes d'opinion sont exprimés en points (de −100 à +100). Les taux sont calculés sur les répondants concernés par "
              "la question, hors non-réponses, et arrondis à l'unité.", "note"),
        ]),
    ]
    if indice_ia:
        blocs.append(("indice_hc", "Indice H&C de Maturité IA", [
            p("Chaque entreprise reçoit un score de 0 à 100, moyenne pondérée de cinq piliers. Chaque réponse est convertie en note "
              "selon un barème fixe ; une réponse « Ne sait pas » ou « Non concerné » retire la question du calcul pour cette entreprise "
              "au lieu de compter pour zéro."),
            tableau(["Pilier", "Poids", "Ce qui est mesuré"], [[x["nom"], f"{round(x['w'] * 100)} %", x["d"]] for x in indice_hc.PILIERS],
                    "Piliers de l'indice", [1.4, 0.5, 4], 9),
            tableau(["Niveau", "Score", "Description"],
                    [[f"{k + 1}. {nom}", f"{k * 20} à {(k + 1) * 20}", indice_hc.NIV_DESC[k]] for k, nom in enumerate(indice_hc.NIVEAUX)],
                    "Niveaux de maturité", [1.4, 0.7, 3.8], 9),
        ]))
    blocs += [
        ("outils", "Outils d'enquête et système de suivi", [
            liste([
                f"**Collecte :** {outil}, sur smartphone ou tablette, avec saisie hors ligne et envoi quotidien.",
                ("**Formulaire :** fichier XLSForm pour KoboToolbox, généré depuis le questionnaire validé." if fiche.get("outil") == "kobo"
                 else "**Formulaire :** fichier d'import pour QuestionPro, généré depuis le questionnaire validé ; chaque enquêteur "
                      "diffuse le lien portant son identifiant."),
                "**Suivi :** tableau de bord de la plateforme Datatym, synchronisé avec l'outil de collecte : avancement par enquêteur, "
                f"par {'pays' if pays else 'zone'}, par profil et par quota, carte, écarts au calendrier, indicateurs calculés en direct.",
            ]),
        ]),
        ("collecte", "Déroulement de la collecte", [
            liste([
                f"**Période :** du {date_fr(jours[0])} au {date_fr(jours[-1])} ({len(jours)} jours de collecte"
                + (", hors dimanches" if ech["params"].get("sans_dimanche", True) else "") + ").",
                ("**Formation :** une journée la veille du démarrage, " if float(hyp.get("jours_formation", 1)) == 1
                 else f"**Formation :** {nombre(hyp.get('jours_formation', 1), 0)} jours avant le démarrage, ")
                + (f"en ligne sur Microsoft Teams, pour {'les titulaires et les réserves' if n_res else 'toute l’équipe'} : présentation de l'étude, passation du questionnaire, "
                   "prise en main de l'outil et pré-test." if en_ligne else
                   "en présentiel dans chaque pays : présentation de l'étude, passation du questionnaire, prise en main de l'outil et pré-test."),
                ("**Supervision :** à distance par l'équipe Datatym, à partir du tableau de bord : point quotidien sur le réalisé, relance "
                 "des enquêteurs en retard, réallocation des quotas à mi-parcours si nécessaire.") if a_distance else
                (f"**Supervision :** un superviseur sur le terrain pour {nombre(hyp.get('enq_par_superviseur', 8), 0)} enquêteurs, "
                 "point quotidien sur le réalisé, réallocation des quotas à mi-parcours si nécessaire."),
                "**Remplacement :** un enquêteur qui abandonne est remplacé par une réserve du même pays, qui reprend ses quotas restants."
                if n_res else "**Remplacement :** un enquêteur qui abandonne voit ses quotas répartis entre les enquêteurs de sa zone.",
            ]),
        ] + ([tableau(["Période", "Étape"], [[date_fr(x["debut"]) if x["debut"] == x["fin"] else f"du {date_fr(x['debut'])} au {date_fr(x['fin'])}",
                                              x["nom"]] for x in phases], "Calendrier de l'étude", [2.2, 2.4], 9)] if phases else [])),
        ("qualite", "Contrôle qualité", [
            liste(([
                "**Consentement :** seuls les entretiens où le répondant a accepté de participer sont conservés.",
                "**Éligibilité :** les répondants hors cible (profil ou critère d'exclusion) sont écartés.",
                "**Durée :** un entretien plus court que 40 % de la durée médiane est écarté comme suspect.",
            ] if controle else [
                "**Mode « suivi seul » :** toute réponse avec consentement est comptée ; les règles d'éligibilité et de durée "
                "ne sont pas appliquées automatiquement et font l'objet d'une revue manuelle.",
            ]) + [
                f"**Rappels :** {rappels} % des répondants sont rappelés pour vérifier que l'entretien a bien eu lieu.",
                "**Cohérence :** contrôle des réponses contradictoires et des valeurs aberrantes lors du nettoyage.",
                "**Paiement :** seuls les questionnaires validés à l'issue de ces contrôles sont rémunérés.",
            ]),
        ]),
        ("traitement", "Traitement, analyse et dépôt des données", [
            liste([
                f"**Logiciel :** traitement et analyse sous {data.get('logiciel', 'Python (VS Code)')} ; scripts reproductibles d'une édition à l'autre.",
                "**Nettoyage :** suppression des doublons, des refus et des hors-cible ; application des règles de contrôle qualité.",
                f"**Calcul :** indicateurs selon les modes de calcul ci-dessus, lecture globale, par profil et par {'pays' if pays else 'zone'}.",
                "**Pondération :** aucune ; " + ("les pays ayant le même poids dans l'échantillon, le résultat d'ensemble est la moyenne des répondants "
                                                "et non une estimation régionale." if egal and len(zones) > 1 else
                                                "les résultats d'ensemble reflètent la répartition de l'échantillon."),
                "**Dépôt :** bases nettoyées et dictionnaire des variables déposés sur l'espace DATA du site Datatym.",
            ]),
        ]),
        ("donnees", "Confidentialité et protection des données", [
            liste([
                "Les réponses sont confidentielles et ne sont jamais publiées de façon nominative ; seuls des résultats agrégés sont diffusés.",
                "Aucun résultat n'est publié pour un groupe de moins de 30 répondants.",
                "Les coordonnées des enquêteurs servent uniquement à la gestion de la mission (contrat, suivi, paiement).",
                "À la clôture, livrables, versions validées et base des soumissions sont archivés par Datatym.",
            ]),
        ]),
        ("limites", "Limites", [liste(data.get("limites", []) + ([
            "Les pays ont le même poids dans l'échantillon quelle que soit leur taille : le résultat d'ensemble décrit les répondants, "
            "il n'est pas représentatif de l'ensemble de la région."] if egal and len(zones) > 1 and pays else []))]),
    ]
    sections = [section(cle, f"{k}. {titre}", contenu, source="texte" if cle in ("traitement", "limites") else "auto")
                for k, (cle, titre, contenu) in enumerate(blocs, 1)]
    return {"note_methodologique": {
        "titre": "Note méthodologique", "surtitre": "Baromètre Datatym", "sous_titre": fiche["theme"],
        "meta": [f"{n} répondants · {', '.join(ech['zones'])} · {len(jours)} jours", f"Version du {aujourdhui()}"],
        "en_tete": f"Baromètre {fiche['theme']} — Note méthodologique", "sections": sections,
    }}
