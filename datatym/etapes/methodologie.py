"""Étape 4 — Note méthodologique : consolidation automatique des étapes 1 à 3."""
import math
import re
from datetime import date

from .. import deroulement, indice_hc, pretest
from ..banque import TYPES, du_barometre, sont_des_pays
from ..charte import liste, p, section, tableau
from ..outils import aujourdhui, date_fr, fmt_marge, nombre

DOCS = {"note_methodologique": ("NoteMethodologique", "Note méthodologique")}


def generer(projet, precedent=None):
    prec = precedent or {}
    return {
        "sections_importees": prec.get("sections_importees") or {},  # sections reprises d'une note fournie
        "logiciel": prec.get("logiciel", "Python (VS Code)"),
        "limites": prec.get("limites") or [
            "L'échantillon par quotas décrit la population interrogée ; il ne permet pas d'extrapolation statistique stricte à l'ensemble de la population de référence.",
            "Les réponses sont déclaratives : elles traduisent des perceptions, susceptibles d'un biais de désirabilité sociale.",
            "Les résultats par sous-groupe de moins de 30 répondants ne sont pas publiés ; entre 30 et 100, ils sont présentés comme des tendances.",
        ],
    }


def _st(texte):
    return {"type": "titre", "texte": texte, "niveau": 2}


def construire_docs(projet, data, cadrage, quest, ech):
    """Note méthodologique : population, plan d'échantillonnage, collecte, précision, pondération, indicateurs, contrôle
    qualité, traitement et usage de l'IA, protection des données, limites. Une section reprise d'une note fournie
    (data « sections_importees ») remplace le texte par défaut ; les tableaux calculés (quotas, indicateurs) restent joints."""
    fiche = projet["fiche"]
    outil = "KoboToolbox (application KoboCollect)" if fiche.get("outil") == "kobo" else "QuestionPro (application hors ligne)"
    lib = {pr["code"]: pr["libelle"] for pr in quest["profils"]}
    jours = [date.fromisoformat(j) for j in ech["jours"]]
    n = fiche["taille"]
    inds = [i for i in cadrage["indicateurs"] if i.get("actif", True)]
    importees = data.get("sections_importees") or {}

    lignes_ind = []
    for i in inds:
        if i["type"] == "indice":
            src = "Composantes : " + ", ".join(i.get("composantes", []))
        else:
            src = ", ".join(f"{q['num']} ({q['var']})" for q in quest["questions_plates"] if q.get("indicateur") == i["id"])
        code = f"{i['id']} ({i['code_origine']})" if i.get("code_origine") else i["id"]
        lignes_ind.append([code, i["libelle"], src, TYPES[i["type"]]["calcul"]])
    q = {(z, c): v for z, c, v in ech["quotas"]}
    tot_prof = {c: sum(q[(z, c)] for z in ech["zones"]) for c in lib}

    hyp = ech["params"].get("hypotheses") or {}
    en_ligne = hyp.get("formation", "en_ligne") == "en_ligne"
    a_distance = hyp.get("supervision", "distance") == "distance"
    rappels = int(hyp.get("part_rappels", 10))
    zones = ech["zones"]
    pays = sont_des_pays(zones)
    Z = "Pays" if pays else "Zone"
    mot = "pays" if pays else "zone"
    n_res = len(ech.get("reserves") or []) or sum((ech.get("reserve") or {}).values())
    rec = ech.get("recrutement") or {}
    poids = ech["params"].get("poids_zones") or {}
    egal = len(set(poids.values())) <= 1
    poids_prof = ech["params"].get("poids_profils") or {}
    egal_prof = len(set(poids_prof.values())) <= 1
    detail = lambda d, noms=None: ", ".join(f"{(noms or {}).get(k, k)} {nombre(v, 0) if float(v).is_integer() else nombre(v, 1)}" for k, v in d.items())
    conditionnelles = [x for x in quest["questions_plates"] if x.get("conditions")]
    exclusions = [x for x in quest["questions_plates"] if x.get("exclut")]
    controle = (projet["etapes"]["collecte"].get("data") or {}).get("controle_qualite", True)
    indice_ia = bool(re.search(r"\bIA\b|intelligence artificielle", fiche["theme"], re.I))
    try:
        phases = deroulement.presenter(projet)["phases"]
    except Exception:  # calendrier indicatif seulement : la note reste produite sans lui
        phases = []
    atouts = "; ".join(a.rstrip(".").lower() for a in rec.get("atouts") or [])
    nz = max(len(zones), 1)

    # 1. population
    eligibilite = ["Avoir donné son consentement explicite à participer."]
    for x in exclusions:
        libs = {m["code"]: m["label"] for m in x.get("modalites") or []}
        eligibilite.append(f"{x['texte'].rstrip(' ?')} : exclusion si « {' » ou « '.join(libs.get(c, c) for c in x['exclut'])} ».")
    population = [
        p(f"La population cible regroupe les profils suivants : {', '.join(lib.values())}, dans {len(zones)} {mot}{'s' if not pays and len(zones) > 1 else ''} "
          f"({', '.join(zones)})."),
        p("**Critères d'éligibilité :**"),
        liste(eligibilite),
        p("L'unité d'observation est le répondant : il répond pour lui-même ou, s'il représente une structure, pour elle. "
          "Les résultats sont présentés par profil et par " + mot + "."),
    ]
    # 2. plan d'échantillonnage
    tableaux_quotas = [
        tableau(["Profil", f"Par {mot} (moyenne)", "Total", "Poids"],
                [[lib[c], nombre(v // nz, 0), nombre(v, 0), nombre(poids_prof.get(c, 1), 0) if float(poids_prof.get(c, 1)).is_integer() else nombre(poids_prof.get(c, 1), 1)]
                 for c, v in tot_prof.items()] + [["Total", nombre(n // nz, 0), nombre(n, 0), ""]], "Allocation de l'échantillon", [2.6, 1, 0.8, 0.6]),
        tableau([Z, "Effectif", "Marge d'erreur (IC 95 %)"],
                [[z, nombre(t, 0), fmt_marge(t)] for z, t in ech["tot_zone"].items()], f"Effectifs et précision par {mot}"),
    ]
    echantillon = [
        _st("{n}.1 Allocation"),
        p(f"{nombre(n, 0)} répondants au total, " + ("répartis à parts égales entre les " + mot + "s" if egal and len(zones) > 1 else
                                                    f"répartis selon les poids retenus ({detail(poids)})") +
          (" et entre les profils." if egal_prof else f" ; entre profils, selon les poids fixés au cadrage ({detail(poids_prof, lib)}).")),
        *tableaux_quotas,
        _st("{n}.2 Calcul des quotas"),
        p(f"Le quota d'une case {mot} × profil est proportionnel au produit des deux poids : un poids de 2 donne deux fois plus de "
          "questionnaires qu'un poids de 1. Les quotas sont arrondis à l'unité par la méthode du plus fort reste, de sorte que leur "
          f"somme est exactement égale à la taille de l'échantillon ({nombre(n, 0)}). Ces poids servent à répartir la collecte ; "
          "ils ne sont pas appliqués aux résultats."),
        tableau(["Élément", "Valeur"], [
            ["Enquêteurs", f"{ech['nb_enqueteurs']} titulaires" + (f" et {n_res} réserves" if n_res else "")],
            ["Productivité retenue", f"{ech['params']['rendement']} questionnaires par enquêteur et par jour"],
            ["Taux de réalisation attendu", f"{round(float(ech['params'].get('marge', 0.9)) * 100)} % (marge pour les refus et rendez-vous manqués)"],
        ], "Paramètres du plan de collecte", [1.3, 2.5]),
    ]
    # 3. collecte
    collecte = [
        _st("{n}.1 Outil et formulaire"),
        liste([
            f"**Outil :** {outil}, sur smartphone ou tablette, avec saisie hors ligne ; version digitale auto-administrée.",
            ("**Formulaire :** fichier XLSForm pour KoboToolbox, généré depuis le questionnaire validé." if fiche.get("outil") == "kobo"
             else "**Formulaire :** fichier d'import pour QuestionPro, généré depuis le questionnaire validé ; chaque enquêteur "
                  "diffuse le lien portant son identifiant."),
            f"**Questionnaire :** {len(quest['sections'])} sections et {len(quest['questions_plates'])} questions ; version terrain "
            f"(environ {math.ceil(max(quest['duree_terrain'].values()))} minutes) et digitale (environ {math.ceil(max(quest['duree_digital'].values()))} minutes)."
            + (f" {len(conditionnelles)} question(s) ne s'affichent qu'en fonction d'une réponse précédente." if conditionnelles else "")
            + (f" {len(exclusions)} question(s) mettent fin au questionnaire lorsque le répondant est hors cible." if exclusions else ""),
            "**Suivi :** tableau de bord de la plateforme BAROMAKER de Datatym, synchronisé avec l'outil de collecte : avancement par "
            f"enquêteur, par {mot}, par profil et par quota, indicateurs calculés en direct.",
        ] + ([pretest.pour_methodologie(projet)] if pretest.pour_methodologie(projet) else [])),
        _st("{n}.2 Équipe d'enquête"),
        liste([
            "**Recrutement :** confié au service des ressources humaines, à partir d'une annonce publiée sur un site d'emploi "
            "avec présélection automatique des candidatures (ATS).",
            f"**Profil :** {rec.get('diplome', 'Bac+3')} minimum, {rec.get('experience', '1 an')} d'expérience d'enquête quantitative, "
            "maîtrise d'un outil de collecte mobile" + (f" ; atouts : {atouts}" if atouts else "") + ".",
            f"**Effectifs :** {ech['nb_enqueteurs']} enquêteurs titulaires" + (f" et {n_res} réserves, formées avec l'équipe et mobilisées "
            "seulement pour remplacer un abandon" if n_res else "") + ".",
            "**Rémunération :** au questionnaire validé ; un questionnaire écarté au contrôle qualité n'est pas payé.",
        ]),
        _st("{n}.3 Déroulement"),
        liste([
            f"**Période :** du {date_fr(jours[0])} au {date_fr(jours[-1])} ({len(jours)} jours de collecte"
            + (", hors dimanches" if ech["params"].get("sans_dimanche", True) else "") + ").",
            ("**Formation :** une journée la veille du démarrage, " if float(hyp.get("jours_formation", 1)) == 1
             else f"**Formation :** {nombre(hyp.get('jours_formation', 1), 0)} jours avant le démarrage, ")
            + ("en ligne sur Microsoft Teams : présentation de l'étude, passation du questionnaire, prise en main de l'outil et pré-test."
               if en_ligne else "en présentiel : présentation de l'étude, passation du questionnaire, prise en main de l'outil et pré-test."),
            ("**Supervision :** à distance par l'équipe Datatym, à partir du tableau de bord : point quotidien sur le réalisé, relance "
             "des enquêteurs en retard, réallocation des quotas à mi-parcours si nécessaire.") if a_distance else
            (f"**Supervision :** un superviseur sur le terrain pour {nombre(hyp.get('enq_par_superviseur', 8), 0)} enquêteurs, "
             "point quotidien sur le réalisé, réallocation des quotas à mi-parcours si nécessaire."),
            "**Remplacement :** un enquêteur qui abandonne est remplacé par une réserve du même " + mot + ", qui reprend ses quotas restants."
            if n_res else "**Remplacement :** un enquêteur qui abandonne voit ses quotas répartis entre les enquêteurs de son " + mot + ".",
        ]),
    ] + ([tableau(["Période", "Étape"], [[date_fr(x["debut"]) if x["debut"] == x["fin"] else f"du {date_fr(x['debut'])} au {date_fr(x['fin'])}",
                                          x["nom"]] for x in phases], "Calendrier de l'étude", [2.2, 2.4], 9)] if phases else [])
    # 4. précision
    lignes_prec = [["Global", nombre(n, 0), fmt_marge(n)]]
    if len(zones) > 1:
        lignes_prec.append([f"Par {mot} (moyenne)", nombre(n // nz, 0), fmt_marge(n // nz)])
    for c, v in tot_prof.items():
        lignes_prec.append([f"Profil : {lib[c]}", nombre(v, 0), fmt_marge(v)])
        if len(zones) > 1 and len(tot_prof) > 1 and v // nz:
            lignes_prec.append([f"{lib[c]} d'un même {mot}", nombre(v // nz, 0), fmt_marge(v // nz)])
    precision = [
        tableau(["Niveau de lecture", "Effectif", "Marge d'erreur (95 %, p = 50 %)"], lignes_prec, "Précision des résultats", [3, 0.8, 1.3]),
        p("Ces marges supposent un tirage aléatoire simple. L'échantillon étant constitué par quotas, elles sont indicatives ; "
          "elles sont publiées avec chaque résultat."),
    ]
    ponderation = [p(
        "Aucune pondération n'est appliquée aux résultats : " + ("les " + mot + "s ayant le même poids dans l'échantillon, le résultat d'ensemble "
        "est la moyenne des répondants et non une estimation régionale." if egal and len(zones) > 1 else
        "les résultats d'ensemble reflètent la répartition de l'échantillon.")
        + (" Les profils n'ayant pas le même poids, les résultats sont présentés par profil, sans indicateur « tous profils »." if not egal_prof else ""))]
    indicateurs = [
        tableau(["Code", "Indicateur", "Questions (variables)", "Mode de calcul"], lignes_ind, "Indicateurs de l'étude", [0.7, 1.6, 1.3, 3], 8.5),
        p("Les soldes d'opinion sont exprimés en points (de −100 à +100). Les taux sont calculés sur les répondants concernés par "
          "la question, hors non-réponses, et arrondis à l'unité.", "note"),
    ]
    if indice_ia:
        indicateurs += [
            _st("{n}.1 Indice H&C de Maturité IA"),
            p("Chaque entreprise reçoit un score de 0 à 100, moyenne pondérée de cinq piliers. Chaque réponse est convertie en note "
              "selon un barème fixe ; une réponse « Ne sait pas » ou « Non concerné » retire la question du calcul pour cette entreprise "
              "au lieu de compter pour zéro."),
            tableau(["Pilier", "Poids", "Ce qui est mesuré"], [[x["nom"], f"{round(x['w'] * 100)} %", x["d"]] for x in indice_hc.PILIERS],
                    "Piliers de l'indice", [1.4, 0.5, 4], 9),
            tableau(["Niveau", "Score", "Description"],
                    [[f"{k + 1}. {nom}", f"{k * 20} à {(k + 1) * 20}", indice_hc.NIV_DESC[k]] for k, nom in enumerate(indice_hc.NIVEAUX)],
                    "Niveaux de maturité", [1.4, 0.7, 3.8], 9),
        ]
    qualite = [liste(([
        "**Consentement :** seuls les entretiens où le répondant a accepté de participer sont conservés.",
        "**Éligibilité :** les répondants hors cible (profil ou critère d'exclusion) sont écartés.",
        "**Durée :** un entretien plus court que 40 % de la durée médiane est écarté comme suspect.",
    ] if controle else [
        "**Mode « suivi seul » :** toute réponse avec consentement est comptée ; les règles d'éligibilité et de durée "
        "ne sont pas appliquées automatiquement et font l'objet d'une revue manuelle.",
    ]) + [
        f"**Rappels :** {rappels} % des répondants sont rappelés pour vérifier que l'entretien a bien eu lieu.",
        "**Doublons :** même numéro de téléphone, même entreprise et fonction, ou réponses identiques.",
        "**Cohérence :** contrôle des réponses contradictoires et des valeurs aberrantes lors du nettoyage.",
        "**Paiement :** seuls les questionnaires validés à l'issue de ces contrôles sont rémunérés.",
    ]), p("Chaque exclusion est consignée dans un journal (identifiant, motif, date), conservé avec la base.")]
    traitement = [liste([
        f"**Logiciel :** traitement et analyse sous {data.get('logiciel', 'Python (VS Code)')} ; scripts reproductibles d'une édition à l'autre.",
        "**Contrôles :** valeurs inhabituelles, réponses données à une question qui ne concernait pas le répondant, questions obligatoires "
        "restées vides et questionnaires renseignés à moins de 80 % ; les valeurs manquantes ne sont pas remplacées.",
        "**Apurement :** chaque correction est tracée dans un journal avec son motif ; les réponses « Autre (préciser) » sont recodées "
        "lorsqu'elles correspondent à une modalité existante ; la base finale est figée et datée.",
        f"**Calcul :** indicateurs selon les modes de calcul ci-dessus, lecture par profil et par {mot}.",
        "**Intelligence artificielle :** appui à la rédaction et à la codification sous contrôle d'un analyste ; aucune donnée "
        "personnelle n'est transmise, les données étant pseudonymisées au préalable.",
    ])]
    donnees = [liste([
        "Consentement explicite au début du questionnaire ; le refus met fin à l'enquête.",
        "Les réponses ne sont jamais publiées de façon nominative ; aucun résultat n'est publié pour un groupe de moins de 30 répondants.",
        "Les coordonnées laissées en fin de questionnaire servent seulement aux rappels de contrôle et à l'envoi des résultats, puis sont supprimées.",
        "Les coordonnées des enquêteurs servent uniquement à la gestion de la mission (contrat, suivi, paiement).",
        "À la clôture, livrables, versions validées et base des soumissions sont archivés par Datatym.",
    ])]
    limites = [liste(data.get("limites", []) + ([
        f"Les {mot}s ont le même poids dans l'échantillon quelle que soit leur taille : le résultat d'ensemble décrit les répondants, "
        "il n'est pas représentatif de l'ensemble de la région."] if egal and len(zones) > 1 and pays else []))]

    plan = [
        ("population", "Population et unités d'observation", population),
        ("echantillonnage", "Plan d'échantillonnage", echantillon),
        ("collecte", "Collecte", collecte),
        ("precision", "Précision des résultats", precision),
        ("ponderation", "Pondération", ponderation),
        ("indicateurs", "Indicateurs et mode de calcul", indicateurs),
        ("qualite", "Contrôle qualité", qualite),
        ("traitement", "Traitement des données et usage de l'intelligence artificielle", traitement),
        ("donnees", "Protection des données", donnees),
        ("limites", "Limites", limites),
    ]
    # tableaux calculés joints à la section reprise d'une note fournie
    joints = {"echantillonnage": [_st("{n}.9 Quotas calculés par la plateforme")] + tableaux_quotas, "indicateurs": indicateurs[:2]}
    sections = []
    for k, (cle, titre, blocs) in enumerate(plan, 1):
        if cle in importees:
            blocs, src = importees[cle] + joints.get(cle, []), "texte"
        else:
            src = "texte" if cle in ("ponderation", "traitement", "limites") else "auto"
        blocs = [dict(b, texte=b["texte"].replace("{n}", str(k))) if b.get("type") == "titre" else b for b in blocs]
        sections.append(section(cle, f"{k}. {titre}", blocs, source=src))
    return {"note_methodologique": {
        "titre": "Note méthodologique", "sous_titre": fiche["theme"],
        "meta": [f"{n} répondants · {', '.join(ech['zones'])} · {len(jours)} jours", f"Version du {aujourdhui()}"],
        "en_tete": f"Baromètre {fiche['theme']} — Note méthodologique", "sections": sections,
    }}
