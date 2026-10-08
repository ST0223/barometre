"""Étape 2 — Questionnaire terrain et digital, construit à partir des indicateurs validés du cadrage."""
import math

from ..banque import (NSP_CODE, decouper, du_barometre, modalites, profils_concernes, profils_depuis_cible, slug, sont_des_pays, texte_question)
from ..charte import p, section, tableau, liste
from ..outils import aujourdhui
from .cadrage import indicateurs_actifs

DOCS = {
    "questionnaire_terrain": ("QuestionnaireTerrain", "Questionnaire — version terrain"),
    "questionnaire_digital": ("QuestionnaireDigital", "Questionnaire — version digitale"),
}

TYPE_LIB = {"select_one": "Choix unique", "select_multiple": "Choix multiple", "text": "Texte libre",
            "integer": "Nombre", "note": "Message affiché", "email": "E-mail"}
SECONDES = {"select_one": 13, "select_multiple": 25, "text": 40, "integer": 15, "note": 6, "email": 20}
DUREE_MAX = 15


def nb_enqueteurs_estime(fiche, rendement=6, marge=0.9):
    from ..outils import debut_collecte, jours_collecte
    jours = len(jours_collecte(debut_collecte(fiche), fiche["duree"]))
    return max(1, math.ceil(fiche["taille"] / (rendement * jours * marge)))


def _q(id_, texte, type_, mods=None, **kw):
    q = {"id": id_, "texte": texte, "type": type_, "modalites": mods or [], "profils": None, "obligatoire": True,
         "consigne": "", "indicateur": None, "fixe": False, "modifiee": False}
    q.update(kw)
    return q


def questions_identification(fiche, profils, secteurs, domaine):
    n_enq = nb_enqueteurs_estime(fiche)
    qs = [
        _q("id_enqueteur", "Enquêteur Datatym", "select_one", [{"code": f"enq{k}", "label": f"Enq{k}"} for k in range(1, n_enq + 1)],
           fixe=True, terrain_seul=True, consigne="Rempli par l'enquêteur, ne pas lire. Liste mise à jour à l'étape échantillonnage."),
        _q("id_zone", "Dans quel pays se situe votre structure ?" if sont_des_pays(fiche["zones"]) else "Dans quelle zone se situe votre structure ?",
           "select_one", [{"code": slug(z, maxi=18), "label": z} for z in decouper(fiche["zones"])], fixe=True,
           consigne="Ne pas lire : cocher le pays d'enquête." if sont_des_pays(fiche["zones"]) else "Ne pas lire : cocher la zone d'enquête."),
    ]
    if len(secteurs) > 1:
        qs.append(_q("id_secteur", "Dans quel secteur exerce principalement votre structure ?", "select_one",
                     [{"code": slug(s, maxi=18), "label": s} for s in secteurs], fixe=True))
    qs.append(_q("id_profil", "Quelle fonction occupez-vous ?", "select_one",
                 [{"code": pr["code"], "label": pr["libelle"]} for pr in profils] + [{"code": "autre_hors", "label": "Autre fonction"}],
                 fixe=True))
    qs.append(_q("id_anciennete", "Depuis combien de temps occupez-vous cette fonction ?", "select_one", [
        {"code": "1", "label": "Moins d'1 an"}, {"code": "2", "label": "De 1 à 3 ans"},
        {"code": "3", "label": "De 3 à 5 ans"}, {"code": "4", "label": "Plus de 5 ans"}], fixe=True))
    if domaine == "Climat des affaires":
        qs.append(_q("id_effectif", "Combien de personnes travaillent dans votre structure ?", "select_one", [
            {"code": "1", "label": "Moins de 10"}, {"code": "2", "label": "10 à 49"},
            {"code": "3", "label": "50 à 249"}, {"code": "4", "label": "250 et plus"}], fixe=True))
    return qs


def question_indicateur(ind, profils):
    t = ind["type"]
    type_q = "select_multiple" if t == "multiple" else ("integer" if t == "numerique" else "select_one")
    concernes = profils_concernes(ind, profils)
    q = _q(f"q_{ind['id']}", texte_question(ind), type_q, modalites(ind), indicateur=ind["id"],
           profils=None if len(concernes) == len(profils) else concernes)
    if t == "multiple":
        q["max_choix"] = 3
        q["consigne"] = "Lire les modalités."
    elif t in ("jugement", "satisfaction", "intention", "evolution", "perspective"):
        q["consigne"] = "Lire les modalités sauf « Ne sait pas »."
    return q


def construire_questions(projet, cadrage, precedentes=None):
    fiche = projet["fiche"]
    profils = cadrage.get("profils") or profils_depuis_cible(fiche["cible"])
    secteurs = decouper(fiche.get("secteur", ""))
    anciennes = {q["id"]: q for q in (precedentes or [])}
    inds = [i for i in indicateurs_actifs(cadrage) if i["type"] != "indice"]

    def garder(q):
        a = anciennes.get(q["id"])
        if a and a.get("modifiee"):
            a = dict(a)
            if q.get("indicateur"):
                a["indicateur"] = q["indicateur"]
            return a
        return q

    sections = [{"lettre": "A", "titre": "Identification du répondant", "ids": []}]
    for q in questions_identification(fiche, profils, secteurs, cadrage.get("domaine", "")):
        sections[0]["ids"].append(garder(q))
    blocs = []
    for i in inds:
        if i["bloc"] not in blocs:
            blocs.append(i["bloc"])
    lettres = "BCDEFGHIJKLMNOPQRSTUVWXY"
    for k, bloc in enumerate(blocs):
        qs = [garder(question_indicateur(i, profils)) for i in inds if i["bloc"] == bloc]
        qs += [a for a in anciennes.values() if a.get("ajoutee") and a.get("bloc") == bloc]
        sections.append({"lettre": lettres[k], "titre": bloc, "ids": qs})
    sections.append({"lettre": lettres[len(blocs)], "titre": "Clôture", "ids": [
        garder(_q("cl_resultats", "Souhaitez-vous recevoir les principaux résultats du baromètre ?", "select_one",
                  [{"code": "oui", "label": "Oui"}, {"code": "non", "label": "Non"}], fixe=True)),
        garder(_q("cl_email", "Adresse e-mail pour recevoir les résultats", "email", fixe=True, obligatoire=True,
                  condition_sur=("cl_resultats", "oui"))),
        garder(_q("cl_commentaire", "Avez-vous une remarque ou une suggestion à formuler ?", "text", fixe=True, obligatoire=False)),
    ]})
    return profils, sections


def numeroter(sections, profils):
    """Attribue N°, variables, conditions lisibles et expressions XLSForm."""
    toutes = []
    var_de = {}
    for s in sections:
        n = 0
        for q in s["ids"]:
            n += 1
            q["num"] = f"{s['lettre']}{n}"
            q["var"] = f"{s['lettre'].lower()}{n}"
            q["section"] = s["lettre"]
            var_de[q["id"]] = q["var"]
            toutes.append(q)
    var_profil = var_de.get("id_profil", "a3")
    lib_profil = {pr["code"]: pr["libelle"] for pr in profils}
    num_de = {q["id"]: q["num"] for q in toutes}
    for q in toutes:
        conds, rel = [], []
        if q.get("profils"):
            conds.append("Si fonction = " + " ou ".join(lib_profil.get(c, c) for c in q["profils"]))
            rel.append("(" + " or ".join(f"${{{var_profil}}} = '{c}'" for c in q["profils"]) + ")")
        if q.get("condition_sur"):
            cible_id, valeur = q["condition_sur"]
            if cible_id in var_de:
                conds.append(f"Si {num_de[cible_id]} = {valeur}")
                rel.append(f"${{{var_de[cible_id]}}} = '{valeur}'")
        q["condition"] = " et ".join(conds)
        q["relevant"] = " and ".join(rel)
    return toutes


def duree_estimee(toutes, profils, mode):
    """Durée en minutes par profil (mode terrain : lecture des modalités, +30 %)."""
    res = {}
    for pr in profils:
        s = 45  # accueil et consentement
        for q in toutes:
            if q.get("terrain_seul") and mode == "digital":
                continue
            if q.get("profils") and pr["code"] not in q["profils"]:
                continue
            s += SECONDES.get(q["type"], 15)
            if q["type"] == "select_multiple":
                s += 20  # précision « Autre »
        res[pr["code"]] = round(s * (1.3 if mode == "terrain" else 1.0) / 60, 1)
    return res


def consentement(fiche, minutes):
    return (f"Bonjour. Datatym, cabinet d'études et de données, réalise {du_barometre(fiche['theme'], 'le')}. "
            f"Ce questionnaire dure environ {math.ceil(minutes)} minutes. Vos réponses sont strictement confidentielles et "
            "seront uniquement exploitées de façon statistique : aucun résultat nominatif ne sera publié. Votre participation "
            "est volontaire et vous pouvez l'interrompre à tout moment. Datatym est responsable de cette étude.")


def generer(projet, cadrage, precedent=None):
    prec = (precedent or {}).get("questions_plates")
    profils, sections = construire_questions(projet, cadrage, prec)
    return finaliser(projet, {"profils": profils, "sections": sections})


def finaliser(projet, data):
    profils, sections = data["profils"], data["sections"]
    toutes = numeroter(sections, profils)
    data["questions_plates"] = toutes
    data["duree_terrain"] = duree_estimee(toutes, profils, "terrain")
    data["duree_digital"] = duree_estimee(toutes, profils, "digital")
    maxi = max(list(data["duree_terrain"].values()) + [1])
    data["duree_max"] = maxi
    data["alerte_duree"] = maxi > DUREE_MAX
    data["consentement"] = data.get("consentement_modifie") or consentement(projet["fiche"], min(maxi, DUREE_MAX))
    return data


def normaliser(projet, data):
    """Après édition : reconstruit les sections à partir des questions (ordre conservé)."""
    return finaliser(projet, data)


def _mods_txt(q):
    if q["type"] in ("select_one", "select_multiple"):
        return "\n".join(f"{m['code']} = {m['label']}" for m in q["modalites"])
    return ""


def _controle(q, mode):
    c = ["Obligatoire" if q.get("obligatoire", True) else "Facultatif"]
    if q.get("terrain_seul") and mode == "digital":
        c = ["Facultatif", "Présélectionné par le lien de l'enquêteur"]
    if q.get("max_choix"):
        c.append(f"{q['max_choix']} réponses au maximum")
    if q["type"] == "select_multiple" and any(m["code"] == NSP_CODE for m in q.get("modalites", [])):
        c.append("« Ne sait pas » exclut les autres réponses")
    if q["type"] == "email":
        c.append("Format e-mail valide")
    return "\n".join(c)


def _version(projet, data, cadrage, mode):
    """Questionnaire au format de l'exemplaire Datatym : un tableau par section, avec sauts et contrôles."""
    fiche = projet["fiche"]
    terrain = mode == "terrain"
    noms_ind = {i["id"]: i["libelle"] for i in cadrage.get("indicateurs", [])}
    durees = data["duree_terrain"] if terrain else data["duree_digital"]
    lib = {pr["code"]: pr["libelle"] for pr in data["profils"]}
    outil = "KoboToolbox" if fiche.get("outil") == "kobo" else "QuestionPro"
    q_profil = next((q for q in data["questions_plates"] if q["id"] == "id_profil"), None)
    colonnes = ["N°", "Variable", "Question", "Modalités (code = libellé)", "Type", "Condition d'affichage", "Contrôle"]
    largeurs = [0.55, 0.65, 2.6, 2.2, 0.85, 1.6, 1.1]
    if terrain:
        colonnes.append("Consigne enquêteur")
        largeurs = [0.55, 0.6, 2.3, 2.0, 0.8, 1.45, 1.0, 1.5]

    def ligne(num, var, texte, mods, type_, condition, controle, consigne=""):
        l = [num, var, texte, mods, type_, condition, controle]
        return l + [consigne] if terrain else l

    intro = (f"Questionnaire aligné sur le formulaire {outil} (XLSForm), version du {aujourdhui()}. "
             + ("L'enquêteur lit chaque question et ses modalités telles qu'elles sont écrites, puis saisit la réponse. " if terrain else
                "Le répondant remplit lui-même le questionnaire, section par section, à partir du lien ou du code QR de son enquêteur. ")
             + f"Durée estimée : environ {math.ceil(max(durees.values()))} minutes ("
             + " ; ".join(f"{lib[c]} {str(v).replace('.', ',')} min" for c, v in durees.items()) + f"), plafonnée à {DUREE_MAX} minutes.")
    sections = [
        section("intro", "", [p(intro)], source="auto"),
        section("conventions", "Conventions", [liste([
            "**N°** : numéro affiché au répondant. Les sections vont de A à " + data["sections"][-1]["lettre"]
            + " ; la page d'accueil (message et consentement) n'est pas numérotée.",
            "**Variable** : nom de la colonne dans la base. Les noms suivent la numérotation affichée : lettre de la section en minuscule et "
            "numéro de la question (A2 est enregistrée dans a2).",
            "**Modalités** : code enregistré = libellé affiché. Les échelles ordinales sont codées en chiffres, de la modalité la plus "
            f"défavorable à la plus favorable ; « Ne sait pas » est codé {NSP_CODE}.",
            "**Condition d'affichage** : la question n'apparaît que si la condition est remplie ; la condition de la section s'ajoute "
            "à celle de la question.",
            "Toutes les questions sont obligatoires sauf mention **Facultatif**.",
            "Champs automatiques, non affichés : start, end, today, enqueteur, duree_minutes (annexe A).",
        ])], source="auto"),
        section("accueil", "Accueil et consentement", [tableau(colonnes, [
            ligne("", "message", data["consentement"], "", "Message affiché", "", "", "Lire le message en entier" if terrain else ""),
            ligne("Consentement", "consentement", "Acceptez-vous de participer à cette étude ?", "oui = Oui\nnon = Non", "Choix unique", "",
                  "Obligatoire", "Sans « Oui », l'entretien s'arrête" if terrain else ""),
            ligne("", "consentement_fin", "Merci de votre attention.", "", "Message affiché", "Si Consentement = Non", ""),
        ], largeurs=largeurs, taille=8.5)], source="auto"),
    ]
    for k, sec in enumerate(data["sections"]):
        cond_sec = "Si Consentement = Oui" + (f" et {q_profil['num']} ≠ Autre fonction" if k and q_profil else "")
        lignes = []
        for q in sec["ids"]:
            lignes.append(ligne(q["num"], q["var"], q["texte"], _mods_txt(q), TYPE_LIB.get(q["type"], q["type"]),
                                q.get("condition", ""), _controle(q, mode), q.get("consigne", "")))
            if q["type"] == "select_multiple" and any(m["code"] == "autre" for m in q["modalites"]):
                lignes.append(ligne(f"{q['num']} (préciser)", f"{q['var']}_autre_txt", "Préciser Autre", "", "Texte libre",
                                    f"Si Autre coché en {q['num']}", "Obligatoire", "Noter les mots du répondant"))
            if q["id"] == "id_profil":
                lignes.append(ligne("", "hors_cible", "Ce baromètre ne concerne pas votre fonction. Merci de votre attention.", "",
                                    "Message affiché", f"Si {q['num']} = Autre fonction", "", "Remercier et arrêter l'entretien"))
        if k == len(data["sections"]) - 1:
            lignes.append(ligne("", "merci", "Merci pour votre participation.", "", "Message affiché", "", ""))
        sections.append(section(f"sec_{sec['lettre']}", f"Section {sec['lettre']} : {sec['titre']}", [
            p(f"Condition de la section : {cond_sec}"),
            tableau(colonnes, lignes, largeurs=largeurs, taille=8.5)], source="auto"))
    champs = [["start", "Début de l'entretien (horodatage)"], ["end", "Fin de l'entretien (horodatage)"],
              ["today", "Date de l'entretien"], ["enqueteur", "Code de l'enquêteur (copie de la question d'identification)"],
              ["duree_minutes", "Durée de l'entretien en minutes, calculée à partir de start et end"]]
    sections.append(section("annexe_a", "Annexe A : champs calculés", [
        p("Calculés automatiquement par le formulaire, invisibles pour le répondant, enregistrés dans la base."),
        tableau(["Variable", "Signification"], champs, largeurs=[1, 4], taille=9)], source="auto"))
    sections.append(section("annexe_b", "Annexe B : indicateurs de la note de cadrage et questions correspondantes", [
        tableau(["Indicateur", "Questions", "Variables"], [
            [f"{iid} — {noms_ind.get(iid, '')}", ", ".join(q["num"] for q in data["questions_plates"] if q.get("indicateur") == iid),
             ", ".join(q["var"] for q in data["questions_plates"] if q.get("indicateur") == iid)]
            for iid in dict.fromkeys(q["indicateur"] for q in data["questions_plates"] if q.get("indicateur"))],
            largeurs=[3, 1, 1], taille=9)], source="auto"))
    return {"titre": fiche["theme"], "sous_titre": "", "surtitre": "", "meta": [f"Version du {aujourdhui()}"],
            "en_tete": "", "paysage": True, "sections": sections}


CONSIGNE_TYPE = {"select_one": "Choix unique", "select_multiple": "Choix multiple", "text": "Texte libre",
                 "integer": "Nombre", "email": "Texte court (e-mail)", "note": "Message affiché"}


def _version_terrain(projet, data, cadrage):
    """Version enquêteur au format « version longue » : Code | Question | Consigne | Réponses, sauts en clair."""
    fiche = projet["fiche"]
    outil = "KoboToolbox" if fiche.get("outil") == "kobo" else "QuestionPro"
    toutes = data["questions_plates"]
    par_id = {q["id"]: q for q in toutes}
    lib_profil = {pr["code"]: pr["libelle"] for pr in data["profils"]}
    q_profil = par_id.get("id_profil")

    def libelle(q, code):
        return next((m["label"] for m in q.get("modalites", []) if m["code"] == code), code)

    # sauts déclenchés par chaque question (lecture côté question parente)
    declenche = {}
    for q in toutes:
        if q.get("condition_sur"):
            parent = par_id.get(q["condition_sur"][0])
            if parent:
                declenche.setdefault(parent["id"], []).append(
                    f"Si « {libelle(parent, q['condition_sur'][1])} » : poser {q['var']}.")

    def consigne(q):
        lignes = [CONSIGNE_TYPE.get(q["type"], q["type"])]
        if q.get("terrain_seul"):
            lignes.append("Facultatif. Rempli par l'enquêteur, ne pas lire.")
        elif not q.get("obligatoire", True):
            lignes.append("Facultatif.")
        if q.get("max_choix"):
            lignes.append(f"{q['max_choix']} réponses au maximum.")
        if q["type"] == "select_multiple" and any(m["code"] == NSP_CODE for m in q.get("modalites", [])):
            lignes.append("« Ne sait pas » ne se coche pas avec une autre réponse.")
        if q.get("profils") and q_profil:
            lignes.append(f"Poser seulement si {q_profil['var']} est "
                          + " ou ".join(f"« {lib_profil.get(c, c)} »" for c in q["profils"]) + ".")
        if q.get("condition_sur") and q["condition_sur"][0] in par_id:
            parent = par_id[q["condition_sur"][0]]
            lignes.append(f"Poser seulement si {parent['var']} est « {libelle(parent, q['condition_sur'][1])} ».")
        if q["id"] == "id_profil":
            lignes.append("Si « Autre fonction » : remercier et terminer.")
        lignes += declenche.get(q["id"], [])
        if q["type"] == "text":
            lignes.append("Noter la réponse mot pour mot.")
        if q.get("consigne") and not q.get("terrain_seul"):
            lignes.append(q["consigne"])
        return "\n".join(lignes)

    def reponses(q):
        return "\n".join(f"• {m['label']}" for m in q.get("modalites", [])) if q["type"] in ("select_one", "select_multiple") else ""

    colonnes, largeurs = ["Code", "Question", "Consigne", "Réponses"], [3, 9.2, 5.2, 8.7]
    n_questions = len(toutes)
    derniere = data["sections"][-1]["lettre"]
    sections = [
        section("intro", "", [p(
            f"Version longue du questionnaire, à administrer par l'enquêteur. Elle reprend toutes les questions du formulaire {outil} "
            f"du {aujourdhui()}, dans le même ordre, avec les mêmes codes, libellés et réponses.")], source="auto"),
        section("mode_emploi", "Mode d'emploi", [liste([
            f"Le questionnaire compte {n_questions} questions, réparties en {len(data['sections'])} sections de A à {derniere}, après l'accueil.",
            "L'enquêteur lit la question en gras, puis les réponses.",
            "La colonne Consigne indique le type de question, les sauts et les limites de réponses. Elle ne se lit pas au répondant.",
            "Sauf mention « Facultatif », toutes les questions sont obligatoires.",
        ])], source="auto"),
        section("accueil", "Accueil et consentement", [tableau(colonnes, [[
            "consentement", f"{data['consentement']}\n**Acceptez-vous de participer à cette étude ?**",
            "Choix unique\nSi « Non » : remercier et terminer.", "• Oui\n• Non"]], largeurs=largeurs, taille=10.5)], source="auto"),
    ]
    for sec in data["sections"]:
        lignes = []
        for q in sec["ids"]:
            lignes.append([q["var"], f"**{q['texte']}**", consigne(q), reponses(q)])
            if q["type"] == "select_multiple" and any(m["code"] == "autre" for m in q["modalites"]):
                lignes.append([f"{q['var']}_autre_txt", "**Préciser « Autre »**",
                               f"Texte libre\nPoser seulement si « Autre » est coché en {q['var']}. Noter la réponse mot pour mot.", ""])
        sections.append(section(f"sec_{sec['lettre']}", f"Section {sec['lettre']} : {sec['titre']}", [
            tableau(colonnes, lignes, largeurs=largeurs, taille=10.5)], source="auto"))
    return {"titre": fiche["theme"], "sous_titre": "", "surtitre": "", "meta": [f"Version du {aujourdhui()}"],
            "en_tete": "", "paysage": True, "sections": sections}


def construire_docs(projet, data, cadrage):
    return {"questionnaire_terrain": _version_terrain(projet, data, cadrage),
            "questionnaire_digital": _version(projet, data, cadrage, "digital")}
