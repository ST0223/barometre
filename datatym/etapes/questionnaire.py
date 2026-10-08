"""Étape 2 — Questionnaire terrain et digital, construit à partir des indicateurs validés du cadrage."""
import math
import re

from ..banque import (TYPES, decouper, modalites, profils_concernes, profils_depuis_cible, slug, sont_des_pays, texte_question)
from ..charte import p, section, tableau, liste
from ..outils import aujourdhui, repartir
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
                 fixe=True, consigne="Si « Autre fonction » : hors cible, remercier et arrêter l'entretien."))
    qs.append(_q("id_anciennete", "Depuis combien de temps occupez-vous cette fonction ?", "select_one", [
        {"code": "moins1", "label": "Moins d'1 an"}, {"code": "1_3", "label": "De 1 à 3 ans"},
        {"code": "3_5", "label": "De 3 à 5 ans"}, {"code": "plus5", "label": "Plus de 5 ans"}], fixe=True))
    if domaine == "Climat des affaires":
        qs.append(_q("id_effectif", "Combien de personnes travaillent dans votre structure ?", "select_one", [
            {"code": "moins10", "label": "Moins de 10"}, {"code": "10_49", "label": "10 à 49"},
            {"code": "50_249", "label": "50 à 249"}, {"code": "250plus", "label": "250 et plus"}], fixe=True))
    return qs


def question_indicateur(ind, profils):
    t = ind["type"]
    type_q = "select_multiple" if t == "multiple" else ("integer" if t == "numerique" else "select_one")
    concernes = profils_concernes(ind, profils)
    q = _q(f"q_{ind['id']}", texte_question(ind), type_q, modalites(ind), indicateur=ind["id"],
           profils=None if len(concernes) == len(profils) else concernes)
    if t == "multiple":
        q["max_choix"] = 3
        q["consigne"] = "Lire les modalités. 3 réponses maximum."
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
    return (f"Bonjour. Datatym, cabinet d'études et de données, réalise le baromètre « {fiche['theme']} ». "
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


def construire_docs(projet, data, cadrage):
    fiche = projet["fiche"]
    profils = data["profils"]
    noms_ind = {i["id"]: i["libelle"] for i in cadrage.get("indicateurs", [])}
    dt, dd = data["duree_terrain"], data["duree_digital"]
    lib = {pr["code"]: pr["libelle"] for pr in profils}

    conv = section("conventions", "Conventions", [
        liste([
            "**N°** : numéro de la question. **Variable** : nom de la colonne dans la base de données (lettre de la section et numéro).",
            "**Modalités** : code enregistré = libellé affiché. Toutes les questions sont obligatoires sauf mention « Facultatif ».",
            "**Condition** : la question n'apparaît que si la condition est remplie (profil du répondant, réponse précédente).",
            "**Indicateur** : code de l'indicateur de la note de cadrage alimenté par la question.",
            "Durée estimée (version terrain) : " + " ; ".join(f"{lib[c]} {str(v).replace('.', ',')} min" for c, v in dt.items()) + f". Plafond : {DUREE_MAX} minutes.",
        ]),
    ], source="auto")
    accueil = section("accueil", "Accueil et consentement", [
        p(data["consentement"], "encadre"),
        tableau(["N°", "Variable", "Question", "Modalités", "Consigne"], [
            ["", "consentement", "Acceptez-vous de participer à cette étude ?", "oui = Oui\nnon = Non", "Si Non : remercier et arrêter."]],
            largeurs=[0.5, 1, 3, 1.5, 2.4], taille=9),
    ], source="auto")
    secs_t = [conv, accueil]
    for s in data["sections"]:
        lignes = []
        for q in s["ids"]:
            ctrl = [] if q.get("obligatoire", True) else ["Facultatif"]
            if q.get("max_choix"):
                ctrl.append(f"{q['max_choix']} réponses max.")
            consigne = "\n".join([x for x in [q.get("consigne", ""), q.get("condition", "")] + ctrl if x])
            lignes.append([q["num"], q["var"], q["texte"], _mods_txt(q), TYPE_LIB.get(q["type"], q["type"]),
                           consigne, q.get("indicateur") or ""])
        secs_t.append(section(f"sec_{s['lettre']}", f"Section {s['lettre']} : {s['titre']}", [
            tableau(["N°", "Variable", "Question", "Modalités (code = libellé)", "Type", "Consigne / condition", "Ind."], lignes,
                    largeurs=[0.45, 0.6, 2.6, 2.3, 0.9, 2.2, 0.45], taille=8.5)], source="auto"))
    secs_t.append(section("annexe_ind", "Annexe : indicateurs et questions correspondantes", [
        tableau(["Indicateur", "Questions", "Variables"], [
            [f"{iid} — {noms_ind.get(iid, '')}", ", ".join(q["num"] for q in data["questions_plates"] if q.get("indicateur") == iid),
             ", ".join(q["var"] for q in data["questions_plates"] if q.get("indicateur") == iid)]
            for iid in dict.fromkeys(q["indicateur"] for q in data["questions_plates"] if q.get("indicateur"))],
            largeurs=[3, 1, 1], taille=9)], source="auto"))

    terrain = {
        "titre": "Questionnaire — version terrain", "surtitre": "Baromètre Datatym", "sous_titre": fiche["theme"],
        "meta": ["Questionnaire administré par l'enquêteur", f"Version du {aujourdhui()}"],
        "en_tete": f"Baromètre {fiche['theme']} — Questionnaire terrain", "paysage": True, "sections": secs_t,
    }

    # Version digitale : présentation lisible par le répondant
    secs_d = [section("intro", "", [
        p(re.sub(r"environ \d+ minutes", f"environ {math.ceil(max(dd.values()))} minutes", data["consentement"]).replace("Bonjour. ", "Madame, Monsieur, "), "encadre"),
        p(f"Durée estimée : environ {math.ceil(max(dd.values()))} minutes. Cochez la ou les cases correspondant à votre réponse.", "note"),
        p("☐ J'accepte de participer à cette étude.     ☐ Je ne souhaite pas participer."),
    ], source="auto")]
    for s in data["sections"]:
        blocs = []
        for q in s["ids"]:
            if q.get("terrain_seul"):
                continue
            titre = f"**{q['num']}. {q['texte']}**"
            precisions = []
            if q.get("profils"):
                precisions.append("Question réservée aux : " + ", ".join(lib.get(c, c) for c in q["profils"]))
            if q.get("max_choix"):
                precisions.append(f"{q['max_choix']} réponses au maximum")
            if q.get("condition_sur"):
                precisions.append(q.get("condition", ""))
            if not q.get("obligatoire", True):
                precisions.append("facultatif")
            if precisions:
                titre += f" ({' ; '.join(precisions)})"
            blocs.append(p(titre))
            if q["type"] in ("select_one", "select_multiple"):
                case = "☐" if q["type"] == "select_multiple" else "○"
                blocs.append(p("     ".join(f"{case} {m['label']}" for m in q["modalites"])))
                if any(m["code"] == "autre" for m in q["modalites"]):
                    blocs.append(p("Si autre, préciser : ………………………………………………"))
            else:
                blocs.append(p("……………………………………………………………………………………………"))
        secs_d.append(section(f"sec_{s['lettre']}", f"{s['lettre']}. {s['titre']}", blocs, source="auto"))
    secs_d.append(section("merci", "", [p("**Merci pour votre participation.** Vos réponses contribuent à éclairer les décisions sur ce sujet.")], source="texte"))
    digital = {
        "titre": "Questionnaire — version digitale", "surtitre": "Baromètre Datatym", "sous_titre": fiche["theme"],
        "meta": ["Questionnaire auto-administré", f"Version du {aujourdhui()}"],
        "en_tete": f"Baromètre {fiche['theme']} — Questionnaire digital", "sections": secs_d,
    }
    return {"questionnaire_terrain": terrain, "questionnaire_digital": digital}
