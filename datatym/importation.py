"""Import d'une note de cadrage déjà rédigée (Word), avec ou sans son questionnaire, pour lancer une étude.

La note fournit la fiche (thème, objectif, cible, pays, secteurs, taille, durée), le contexte, les objectifs et, si elle
en a un, le tableau des indicateurs. Le questionnaire, s'il est joint, fournit les indicateurs (une question = un
indicateur) avec leurs codes, leurs modalités et leurs conditions ; ses questions d'identification précisent les pays,
les secteurs et les fonctions. Deux formats de questionnaire sont lus : « technique » (N°, Variable, Question,
Modalités, Type, Condition) et « terrain » (Code, Question, Consigne, Réponses).
"""
import re
import unicodedata

import docx
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from .banque import ESPACES, TYPES, slug

PAYS_CONNUS = sorted({p for l in ESPACES.values() for p in l} | {"Ghana", "Nigeria", "Liberia", "Sierra Leone", "Gambie", "Mauritanie",
                                                               "Cap-Vert", "Maroc", "Tunisie", "Algérie", "Madagascar", "Rwanda", "Burundi",
                                                               "Kenya", "Tanzanie", "Ouganda", "Éthiopie", "Afrique du Sud"}, key=len, reverse=True)


# ------------------------------------------------------------------ lecture du document
def lire(chemin):
    """Suite des blocs du document, dans l'ordre : paragraphes (texte, titre, liste, taille) et tableaux (lignes de cellules)."""
    d = docx.Document(chemin)
    blocs = []
    for el in d.element.body.iterchildren():
        if el.tag == qn("w:p"):
            p = Paragraph(el, d)
            t = " ".join(p.text.split())
            if not t:
                continue
            style = (p.style.name if p.style is not None else "") or ""
            niveau = int(m.group(1)) if (m := re.search(r"(?:Heading|Titre)\s*(\d)", style)) else 0
            taille = max([r.font.size.pt for r in p.runs if r.font.size] or [0])
            blocs.append({"type": "p", "texte": t, "titre": niveau, "liste": el.find(".//" + qn("w:numPr")) is not None or "List" in style,
                          "taille": taille})
        elif el.tag == qn("w:tbl"):
            t = Table(el, d)
            lignes = []
            for r in t.rows:
                cellules = []
                for c in r.cells:
                    cellules.append([" ".join(p.text.split()) for p in c.paragraphs if p.text.strip()])
                lignes.append(cellules)
            blocs.append({"type": "t", "lignes": lignes})
    return blocs


def _txt(cellule):
    return " ".join(cellule).strip()


def _sans_accents(t):
    return slug(t or "", " ", 400)


def _sections(blocs):
    """Découpe en sections par titre de niveau 1 (ou paragraphe numéroté « 3. … » en gras)."""
    res, cour = [], {"titre": "", "blocs": []}
    for b in blocs:
        if b["type"] == "p" and (b["titre"] == 1 or (b["titre"] == 0 and re.match(r"^\d{1,2}\.\s+\S", b["texte"]) and len(b["texte"]) < 90 and not b["liste"])):
            res.append(cour)
            cour = {"titre": b["texte"], "blocs": []}
        else:
            cour["blocs"].append(b)
    res.append(cour)
    return res


def _nettoyer_liste(libelle):
    """Libellé utilisable dans une liste de la fiche (les virgules, « / » et « et » y séparent les éléments)."""
    t = re.sub(r"\s*/\s*", " – ", libelle)
    t = re.sub(r"\s*,\s*", " – ", t)
    t = re.sub(r"\s+et\s+", " – ", t)
    return re.sub(r"\s*\((.*?)\)", lambda m: f" ({m.group(1)})", t).strip(" –")


# ------------------------------------------------------------------ note rédigée librement (brief)
def _bas(t):
    """Minuscules sans accents, ponctuation conservée (traits d'union, apostrophes droites)."""
    t = (t or "").replace("’", "'").replace("‘", "'").replace("‑", "-")
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", t).strip().lower()


_INTERROGATIFS = r"^(quel|quelle|quels|quelles|qu'|que |quoi|combien|comment|ou |pourquoi|a quel|de quel|dans quel|entre |parmi|au bout|lequel|laquelle)"
_INTERTITRE_OBJECTIFS = r"\b(objectifs?|permettre|finalite|servir a|servira a|a quoi sert|but de l)"
_INTERTITRE_HYPOTHESES = r"\b(insights?|hypotheses?|resultats? attendus?|constats? attendus?|exemples? de (resultats|constats|chiffres))"
_PROFIL = r"\b(en tant que|vous etes|je suis|j'ai entre|votre age|quel age|tranche d'age|sexe|genre)\b"


def _type_question(texte, options):
    """Type d'indicateur d'une question écrite en clair, et ses modalités si elles se déduisent du libellé."""
    b = _bas(texte)
    if options:
        multiple = re.search(r"\b(quel(le)?s sont|lesquel(le)?s|plusieurs|toutes? les|cochez)\b", b) or re.search(r"\bparmi les\b.*\bquel(le)?s\b", b)
        return ("multiple" if multiple else "unique"), options
    if re.search(r"\b(combien|nombre de|quel montant|quelle somme)\b", b):
        return "numerique", []
    inversion = re.search(r"\b[a-z]+-(t-)?(vous|ils?|elles?|on|tu)\b", b)
    if inversion and not re.match(_INTERROGATIFS, b):
        if re.search(r",[^,?]*\bou\b", b[inversion.end():].split("?")[0]):  # « arrêté, moins ou toujours ? » : réponses à écrire
            return "unique", []
        return "unique", ["Oui", "Non"]
    return "unique", []  # choix à compléter (liste de banques, d'opérateurs…)


def lire_brief(blocs, theme=""):
    """Lit une note sans titres ni tableaux : un paragraphe d'introduction suivi de puces forme un groupe.

    Les intertitres d'objectifs et d'hypothèses donnent les objectifs et les constats à vérifier ; les paragraphes
    qui posent une question (avec leurs puces comme réponses) donnent des questions ; une question de profil
    « en tant que » donne la cible."""
    groupes = []
    for b in blocs:
        if b["type"] != "p":
            continue
        if b["liste"] and groupes:
            groupes[-1]["puces"].append(b["texte"])
        elif not b["liste"]:
            groupes.append({"tete": b["texte"], "puces": []})
    res = {"objectifs": [], "hypotheses": [], "cible": [], "contexte": [], "questions": []}
    vus, n = set(), 0
    for g in groupes:
        tete, puces, bas = g["tete"], g["puces"], _bas(g["tete"])
        if theme and bas == _bas(theme):
            continue
        sujet_etude = re.search(r"\b(enquete|etude|barometre|sondage)\b", bas)
        if re.search(_INTERTITRE_OBJECTIFS, bas) and (sujet_etude or not bas.endswith("?")) and puces:
            res["objectifs"] += [p.rstrip(" .…") for p in puces]
            continue
        if re.search(_INTERTITRE_HYPOTHESES, bas) and puces:
            res["hypotheses"] += puces
            continue
        profil = bool(puces and re.search(_PROFIL, bas))  # question de profil : toujours avec ses réponses en puces
        question = tete.rstrip().endswith("?") or profil or (tete.rstrip().endswith(":") and puces)
        if not question:
            if len(tete) > 150 and not puces:
                res["contexte"].append(tete)
            continue
        texte = tete.rstrip(" :")
        options = list(puces)
        if not options and (m := re.search(r"\?\s*\(([^()]+,[^()]+)\)\s*$", texte)):  # « … ? (2, 5, 10) »
            options = [x.strip() for x in m.group(1).split(",") if x.strip()]
            texte = texte[:m.start()].rstrip() + " ?"
        cle = re.sub(r"[^a-z0-9]+", "", _bas(texte))
        if cle in vus:
            continue
        vus.add(cle)
        type_, mods = _type_question(texte, options)
        n += 1
        role = "fonction" if profil and re.search(r"\b(en tant que|vous etes|je suis)\b", bas) else _role(texte)
        if role == "fonction" and mods and not res["cible"]:
            res["cible"] = [o for o in mods if not o.lower().startswith("autre")]
        res["questions"].append({"num": f"Q{n}", "texte": texte, "section": "A" if profil else "B",
                                 "bloc": "Profil du répondant" if profil else "Questions de l'étude", "condition_texte": "",
                                 "facultatif": False, "role": role, "type": type_,
                                 "modalites": [{"code": None, "label": m} for m in mods]})
    return res


# ------------------------------------------------------------------ note de cadrage
def analyser_note(blocs):
    sections = _sections(blocs)
    tete = sections[0]["blocs"]
    prop, notes = {"fiche": {}, "contexte": [], "objectifs": [], "indicateurs": []}, []

    # thème : le plus grand texte de la page de garde, hors « Note de cadrage », logos et mentions
    candidats = [b for b in tete if b["type"] == "p" and len(b["texte"]) < 120
                 and not re.search(r"note de cadrage|version du|auteur|·|executive education", b["texte"], re.I)]
    if candidats:
        prop["fiche"]["theme"] = max(candidats, key=lambda b: (b["taille"], -tete.index(b)))["texte"]

    tout = [b for s in sections for b in s["blocs"]]
    texte_tout = " ".join(b["texte"] for b in tout if b["type"] == "p")

    # tableau « Paramètre / Valeur retenue » des notes de la plateforme
    for b in tout:
        if b["type"] == "t" and b["lignes"] and _sans_accents(_txt(b["lignes"][0][0])).startswith("parametre"):
            for l in b["lignes"][1:]:
                cle, val = _sans_accents(_txt(l[0])), _txt(l[-1])
                if cle.startswith("theme"):
                    prop["fiche"]["theme"] = val
                elif cle.startswith("objectif"):
                    prop["fiche"]["objectif"] = val
                elif cle.startswith("cible"):
                    prop["fiche"]["cible"] = val
                elif cle.startswith("champ"):
                    prop["fiche"]["zones"] = val.split(":", 1)[-1].strip()
                elif cle.startswith("secteur"):
                    prop["fiche"]["secteur"] = val
                elif cle.startswith("taille") and (m := re.search(r"\d[\d\s]*", val)):
                    prop["fiche"]["taille"] = int(m.group(0).replace(" ", ""))
                elif cle.startswith("duree") and (m := re.search(r"\d+", val)):
                    prop["fiche"]["duree"] = int(m.group(0))

    for s in sections:
        t = _sans_accents(s["titre"])
        paras = [b for b in s["blocs"] if b["type"] == "p"]
        if "contexte" in t:
            prop["contexte"] = [b["texte"] for b in paras if not b["titre"]]
        if "objectif" in t:
            for b in paras:
                if (m := re.match(r"objectif g[ée]n[ée]ral\s*[:.]\s*(.+)", b["texte"], re.I)):
                    prop["fiche"].setdefault("objectif", m.group(1).rstrip("."))
            debut = False
            for b in paras:
                if b["liste"]:
                    debut = True
                    prop["objectifs"].append(b["texte"])
                elif debut:
                    break  # fin de la première liste (« À qui l'étude sert » ne fait pas partie des objectifs)

    # pays, secteurs et fonctions dans les tableaux
    pays, secteurs, fonctions = [], [], []
    for b in tout:
        if b["type"] != "t" or not b["lignes"]:
            continue
        entete = [_sans_accents(_txt(c)) for c in b["lignes"][0]]
        for k, e in enumerate(entete):
            valeurs = [_txt(l[k]) for l in b["lignes"][1:] if k < len(l) and _txt(l[k])]
            if e == "pays":
                pays += [x.strip() for v in valeurs for x in v.split(",") if x.strip()]
            elif e == "secteur":
                secteurs += valeurs
            elif e in ("fonction", "profil") and k == 0:
                fonctions += [v for v in valeurs if not v.lower().startswith("total")]
        # tableau des indicateurs des notes de la plateforme
        if entete[:2] == ["code", "indicateur"]:
            types = {_sans_accents(v["libelle"]): k for k, v in TYPES.items()}
            for l in b["lignes"][1:]:
                lib_type = _sans_accents(_txt(l[3])) if len(l) > 3 else ""
                prop["indicateurs"].append({"code": _txt(l[0]), "libelle": _txt(l[1]), "definition": _txt(l[2]) if len(l) > 2 else "",
                                            "type": types.get(lib_type, "jugement")})
    # indicateurs du tableau de la note : bloc d'après le tableau « Blocs du questionnaire », champs complets
    blocs_de = {}
    for b in tout:
        if b["type"] == "t" and b["lignes"] and _sans_accents(_txt(b["lignes"][0][0])) == "bloc" and len(b["lignes"][0]) > 1:
            for l in b["lignes"][1:]:
                for lib in (l[1] if len(l) > 1 else []):
                    blocs_de[_sans_accents(lib)] = _txt(l[0])
    complets = []
    for k, i in enumerate(prop["indicateurs"]):
        ind = {"id": i["code"] if re.match(r"^I\d+$", i["code"]) else f"I{k:02d}", "libelle": i["libelle"], "type": i["type"],
               "definition": i["definition"], "niveau": "tous", "actif": True, "objet": "",
               "bloc": blocs_de.get(_sans_accents(i["libelle"]), "Synthèse" if i["type"] == "indice" else "Résultats"),
               "sens": "amelioration" if i["type"] in ("evolution", "perspective") else ""}
        if i["type"] == "indice":
            ind["composantes"] = []
        complets.append(ind)
    prop["indicateurs"] = complets
    if pays and "zones" not in prop["fiche"]:
        prop["fiche"]["zones"] = ", ".join(dict.fromkeys(pays))
    if not pays and "zones" not in prop["fiche"]:
        trouves = [p for p in PAYS_CONNUS if re.search(rf"\b{re.escape(p)}\b", texte_tout)]
        if trouves:
            prop["fiche"]["zones"] = ", ".join(trouves)
    if secteurs and "secteur" not in prop["fiche"]:
        prop["fiche"]["secteur"] = ", ".join(_nettoyer_liste(s) for s in dict.fromkeys(secteurs))
    if fonctions and "cible" not in prop["fiche"]:
        prop["fiche"]["cible"] = ", ".join(_nettoyer_liste(f) for f in dict.fromkeys(fonctions))
    if "taille" not in prop["fiche"] and (m := re.search(r"\b(\d[\d\s]{1,5})\s+(?:dirigeants|répondants|entreprises|questionnaires|personnes|ménages|clients|entretiens)", texte_tout)):
        prop["fiche"]["taille"] = int(m.group(1).replace(" ", ""))
    if "duree" not in prop["fiche"]:
        # seulement une durée rattachée au terrain (« 15 jours de collecte », « terrain de 40 jours »)
        if (m := re.search(r"(?:terrain|collecte|enqu[êe]te)[^.]{0,60}?\b(\d{1,3})\s+jours\b|\b(\d{1,3})\s+jours\s+de\s+(?:terrain|collecte)", texte_tout, re.I)):
            prop["fiche"]["duree"] = int(m.group(1) or m.group(2))
        elif (m := re.search(r"\b(\d{1,2})\s+semaines\b", texte_tout)):
            prop["fiche"]["duree"] = 7 * int(m.group(1))
            notes.append(f"Durée déduite de « {m.group(0)} » : à vérifier, c'est peut-être la durée totale de l'étude et non celle du terrain.")
    # note rédigée librement (brief) : intertitres suivis de puces, questions écrites en paragraphes
    brief = lire_brief(tout, prop["fiche"].get("theme", ""))
    if not prop["objectifs"] and brief["objectifs"]:
        prop["objectifs"] = brief["objectifs"]
    if brief["objectifs"] and not prop["fiche"].get("objectif"):
        prop["fiche"]["objectif"] = brief["objectifs"][0].rstrip(" .…")
    if brief["hypotheses"]:
        # ajoutées au contexte rédigé (celui de la note, sinon celui de la plateforme), sans le remplacer
        prop.setdefault("complement_contexte", []).append("Constats que l'étude devra vérifier, cités à titre d'exemple dans la demande : "
                                + " ; ".join(h.rstrip(" .") for h in brief["hypotheses"]) + ".")
    if brief["cible"] and not prop["fiche"].get("cible"):
        prop["fiche"]["cible"] = ", ".join(_nettoyer_liste(c) for c in brief["cible"])
    if not prop["contexte"] and brief["contexte"]:
        prop["contexte"] = brief["contexte"]
    prop["questions_note"] = brief["questions"]
    for cle, lib in (("theme", "le thème"), ("objectif", "l'objectif"), ("cible", "la cible"), ("zones", "les pays"), ("taille", "la taille"), ("duree", "la durée")):
        if not prop["fiche"].get(cle):
            notes.append(f"La note ne précise pas {lib} de façon reconnaissable : à compléter.")
    return prop, notes


# ------------------------------------------------------------------ questionnaire
def _section_nom(texte):
    m = re.match(r"section\s+([A-Z])\s*[:–-]\s*(.+)", texte, re.I)
    return (m.group(1).upper(), m.group(2).strip()) if m else None


def _modalites(lignes):
    """« code = libellé » par ligne (format technique) ou « • libellé » (format terrain)."""
    mods = []
    for l in lignes:
        if (m := re.match(r"^([\w\-+.]+)\s*=\s*(.+)$", l)):
            mods.append({"code": m.group(1), "label": m.group(2).strip()})
        elif l.startswith(("•", "-", "–")):
            mods.append({"code": None, "label": l.lstrip("•-– ").strip()})
    return mods


def _grille(lignes):
    """Grille : « Lignes : » puis « code : libellé », « Colonnes : » puis « code = libellé »."""
    rangs, cols, zone = [], [], None
    for l in lignes:
        if re.match(r"^lignes?\s*:", l, re.I):
            zone = "l"
        elif re.match(r"^colonnes?\s*:", l, re.I):
            zone = "c"
        elif zone == "l" and (m := re.match(r"^([\w*]+)\s*:\s*(.+)$", l)):
            rangs.append((m.group(1), re.sub(r"\s*\(facultatif\)", "", m.group(2)).strip()))
        elif zone == "c" and (m := re.match(r"^([\w\-+.]+)\s*=\s*(.+)$", l)):
            cols.append({"code": m.group(1), "label": m.group(2).strip()})
    return rangs, cols


def _role(question):
    q = _sans_accents(question)
    if "enqueteur" in q:
        return "enqueteur"
    if re.search(r"\bquel pays\b", q) or "dans quelle zone" in q:
        return "pays"
    if "secteur" in q and "exerce" in q or q.startswith("dans quel secteur"):
        return "secteur"
    if "quelle fonction" in q or "quel poste occupez" in q:
        return "fonction"
    if re.search(r"(recevoir|envoyer).*(rapport|resultats)", q) or "e mail" in q or "email" in q:
        return "restitution"
    return None


def analyser_questionnaire(blocs):
    questions, notes = [], []
    section = ("A", "Identification")
    format_ = None
    for b in blocs:
        if b["type"] == "p":
            if (s := _section_nom(b["texte"])):
                section = s
            elif re.match(r"^(accueil|consentement)", b["texte"], re.I):
                section = ("0", "Accueil")
            continue
        entete = [_sans_accents(_txt(c)) for c in b["lignes"][0]]
        if "question" not in entete:
            continue
        col = {nom: entete.index(nom) for nom in entete}
        for prefixe in ("modalit", "condition", "controle", "type", "reponse", "consigne", "variable", "code"):
            k = next((i for i, e in enumerate(entete) if e.startswith(prefixe)), None)
            if k is not None:
                col.setdefault(prefixe, k)
        col.setdefault("num", 0)
        technique = "variable" in col
        format_ = format_ or ("technique" if technique else "terrain")
        for l in b["lignes"][1:]:
            val = lambda nom: l[col[nom]] if nom in col and col[nom] < len(l) else []
            texte = _txt(val("question"))
            if section[0] == "0" or not texte or re.match(r"^pr[ée]ciser", texte, re.I):
                continue
            if technique:
                num = _txt(val("num"))
                type_lib = _sans_accents(_txt(val("type")))
                if "message" in type_lib:
                    # message de fin : la condition désigne une réponse d'exclusion (ex. « Si A6 = Moins de 2 Md FCFA »)
                    if (m := re.match(r"si\s+([A-Z]\d+)\s*=\s*(.+)$", _txt(val("condition")), re.I)):
                        questions.append({"exclusion_de": m.group(1).upper(), "libelle_exclu": m.group(2).strip()})
                    continue
                mods_brut = val("modalit")
                condition = _txt(val("condition"))
                controle = _txt(val("controle"))
            else:
                num = _txt(val("code")).upper()
                consigne = val("consigne")
                type_lib = _sans_accents(consigne[0]) if consigne else ""
                mods_brut = val("reponse")
                condition = " ".join(consigne[1:])
                controle = condition
            if not num or not re.match(r"^[A-Z]\d+", num, re.I):
                continue
            q = {"num": num.upper(), "texte": texte, "section": section[0], "bloc": section[1], "condition_texte": condition,
                 "facultatif": "facultatif" in _sans_accents(controle), "role": _role(texte)}
            if "grille" in type_lib:
                rangs, cols = _grille(mods_brut)
                for k, (code_l, lib_l) in enumerate(rangs, 1):
                    questions.append({**q, "num": f"{q['num']}.{k}", "texte": f"{texte.rstrip(' ?')} — {lib_l}", "type": "unique",
                                      "modalites": cols, "libelle": f"{lib_l} ({q['num']})"})
                continue
            if "multiple" in type_lib:
                q["type"] = "multiple"
            elif "unique" in type_lib or "deroulante" in type_lib:
                q["type"] = "unique"
            else:
                continue  # texte libre, e-mail, nombre : pas un indicateur à choix
            q["modalites"] = _modalites(mods_brut)
            if (m := re.search(r"(\d+)\s+r[ée]ponses?\s+au\s+maximum", controle, re.I)):
                q["max_choix"] = int(m.group(1))
            questions.append(q)
    if not questions:
        # pas de question dans les tableaux (ou seulement des annexes) : questionnaire rédigé en paragraphes numérotés
        redigees, n_r = _questionnaire_redige(blocs)
        if redigees:
            return redigees, "redige", n_r
    exclusions = [x for x in questions if "exclusion_de" in x]
    questions = [x for x in questions if "exclusion_de" not in x]
    par_num = {x["num"]: x for x in questions}
    for e in exclusions:
        cible = par_num.get(e["exclusion_de"])
        if cible:
            code = next((m["code"] for m in cible["modalites"] if _sans_accents(m["label"]) == _sans_accents(e["libelle_exclu"])), None)
            if code:
                cible["exclut"] = [code]
    if format_ == "terrain" and any(x["condition_texte"] for x in questions):
        notes.append("Questionnaire au format terrain : les conditions d'affichage sont écrites en phrases et ne sont pas reprises. "
                     "Ajoutez-les dans l'outil de collecte ou vérifiez-les dans l'étape Questionnaire.")
    return questions, format_, notes


# ------------------------------------------------------------------ questionnaire rédigé (paragraphes numérotés)
_Q_NUM = re.compile(r"^([A-Z]\d{1,2}[a-z]?)\.\s+(.+)$")
_TYPE_REDIGE = re.compile(r"^(choix unique|choix multiple|grille|echelle|ouverte)")
_ETIQUETTES = re.compile(r"\s+(NOUVEAU|MODIFI[ÉE]|[ÀA] VALIDER|SUPPRIM[ÉE])\s*$")
_REF = r"(?:profil_final|[A-Z]\d{1,2}[a-z]?)"


def _bloc_redige(titre):
    """Intertitre de bloc : « Bloc A — Portefeuille » ; introduction, profil, clôture ; pages d'aide ignorées."""
    bas = _bas(titre)
    tag = (m.group(1) if (m := re.search(r"\[([^\]]+)\]", titre)) else "")
    nom = re.sub(r"\s*\[[^\]]+\]\s*", " ", titre).strip()
    if (m := re.match(r"^bloc\s+([0-9A-Z])\s*[—–:-]\s*(.+)$", nom, re.I)):
        lettre, nom = m.group(1).upper(), m.group(2).strip()
    else:
        lettre = None
    if re.search(r"mode d'emploi|correspondance|conventions|annexe|sommaire|lexique|changements par rapport", bas):
        genre = "ignore"
    elif re.search(r"donnees de collecte|non lues? au repondant|metadonnees", bas):
        genre = "collecte"
    elif re.search(r"introduction|consentement|accueil", bas):
        genre = "intro"
    elif re.search(r"\bcloture\b|\bfin de l'entretien\b|remerciements", bas):
        genre = "cloture"
    elif lettre == "0" or re.search(r"\bprofil\b|identification|signaletique", _bas(nom)):
        genre = "profil"
    else:
        genre = "theme"
    return {"lettre": lettre, "nom": nom, "tag": tag, "genre": genre}


def _hors_parentheses(t):
    return re.sub(r"\([^()]*\)", "", t)


def _decouper_puce(p):
    """Une puce qui énumère plusieurs réponses (« 0 · 1 · 2 », « Sénégal, Mali, Niger ») en donne plusieurs."""
    if " · " in p:
        return [x.strip() for x in p.split(" · ") if x.strip()]
    if _hors_parentheses(p).count(",") >= 2:
        return [x.strip() for x in re.split(r",\s*(?![^()]*\))", p) if x.strip()]
    return [p]


def _condition_puce(p):
    """Puce « Avec mon opérateur (ligne affichée si A7 ≠ Aucun) » : libellé nettoyé et condition propre à la ligne."""
    cond = None
    if (m := re.search(r"\s*\((?:ligne affich[ée]e si|affich[ée]e? si|si)\s+([^()]*)\)", p, re.I)):
        cond, p = m.group(1).strip(), p[:m.start()] + p[m.end():]
    p = re.sub(r"\s*\((?:masqu[ée]e? si|r[ée]ponse exclusive)[^()]*\)", "", p, flags=re.I)
    p = re.sub(r"\s*·\s*toujours affich[ée]e?\s*$", "", p, flags=re.I)
    return p.strip(), cond


def _codes(labels, type_):
    """Codes des réponses : 1, 2, 3… en choix unique (« Ne sait pas » = 99), mots en choix multiple."""
    mods, vus = [], set()
    for k, l in enumerate(labels, 1):
        if type_ == "multiple":
            base = slug(l, maxi=18) or f"r{k}"
            code, n = base, 2
            while code in vus:
                code, n = f"{base[:15]}_{n}", n + 1
        elif re.match(r"ne (sait|sais) pas", _bas(l)):
            code = "99"
        elif re.match(r"autre\b(?! (pays|ville|fonction))", _bas(l)) and "autre" not in vus:
            code = "autre"  # le formulaire ajoute le champ « préciser »
        else:
            code = str(k)
        vus.add(code)
        mods.append({"code": code, "label": l})
    return mods


def _proche(valeur, libelle):
    """Une valeur citée dans une condition (« Oui », « Aucun », « Conseiller attitré ») désigne-t-elle ce libellé ?"""
    v, l = _bas(valeur).strip(" .«»\"'"), _bas(libelle)
    if not v:
        return 0
    if v == l:
        return 3
    if l.startswith(v) or v.startswith(l):
        return 2
    mots_v = {w for w in re.findall(r"[a-z0-9]+", v) if len(w) > 2 or w.isdigit()}
    mots_l = set(re.findall(r"[a-z0-9]+", l))
    commun = mots_v & mots_l
    return 1 if mots_v and len(commun) >= max(1, (len(mots_v) + 1) // 2) else 0


def _choisir(valeur, modalites):
    notes = [(_proche(valeur, m["label"]), k) for k, m in enumerate(modalites)]
    meilleur = max(notes, default=(0, None))
    return modalites[meilleur[1]] if meilleur[0] else None


def _questionnaire_redige(blocs):
    """Questionnaire rédigé : intertitres de blocs, questions « A1. … », ligne de type (« Choix unique · filtre »),
    réponses en puces avec renvois (« Oui → A5 », « Non → fin (hors cible) »), conditions « Posée si : … »,
    lignes de grille conditionnelles, listes propres à un profil (« Liste pour les entreprises : »), consignes."""
    items, section = [], None
    for b in blocs:
        if b["type"] == "t":
            # grille présentée en tableau (« N° | Critère | Ligne affichée si (B0) »)
            if items and items[-1]["section"] is section and _bas(items[-1]["type_ligne"]).startswith("grille") and not items[-1].get("table"):
                items[-1]["table"] = [[_txt(c) for c in l] for l in b["lignes"]]
            continue
        t = b["texte"]
        if b["titre"] == 1:
            section = _bloc_redige(t)
            continue
        if section is None or section["genre"] == "ignore":
            continue
        if not b["liste"] and (m := _Q_NUM.match(t)):
            items.append({"num": m.group(1)[0].upper() + m.group(1)[1:], "texte": _ETIQUETTES.sub("", m.group(2)).strip(),
                          "type_ligne": "", "puces": [], "groupes": [], "section": section, "consignes": [], "posee_si": [], "sinon": []})
            continue
        if not items or items[-1]["section"] is not section:
            continue
        q = items[-1]
        bas = _bas(t)
        if b["liste"]:
            (q["groupes"][-1]["puces"] if q["groupes"] else q["puces"]).append(t)
        elif not q["type_ligne"] and _TYPE_REDIGE.match(bas):
            q["type_ligne"] = t
        elif (m := re.match(r"^pos[ée]e si\s*:\s*(.+)$", t, re.I)):
            q["posee_si"].append(m.group(1).strip())
        elif (m := re.match(r"^sinon\s*:\s*(.+)$", t, re.I)):
            q["sinon"].append(m.group(1).strip())
        elif (m := re.match(r"^consigne\s*:\s*(.+)$", t, re.I)):
            q["consignes"].append(m.group(1).strip())
        elif (m := re.match(r"^liste pour (?:les )?(.+?)\s*:\s*$", t, re.I)):
            q["groupes"].append({"tag": m.group(1), "puces": []})
    notes = []
    if len(items) < 3:
        return [], notes
    ouvertes, a_completer, controles, copies, non_lues, auto = [], [], [], [], [], []
    developpees = []  # questions telles que la plateforme les reprend (une ligne de grille = une question)
    for it in items:
        s, tl = it["section"], _bas(it["type_ligne"])
        tags = re.findall(r"\[([^\]]+)\]", it["texte"])
        texte = re.sub(r"\s*\[[^\]]+\]\s*", " ", it["texte"]).strip()
        if s["genre"] == "intro" and (not tl or re.search(r"accept\S* de participer|consent", _bas(texte))):
            continue  # texte d'introduction et consentement : pris en charge par le formulaire
        if not tl:
            continue
        identification = s["genre"] in ("intro", "profil", "collecte")
        # « A » désigne l'identification dans la plateforme : un « Bloc A » thématique reçoit une clé à part
        base = {"texte": texte, "section": "A" if identification else f"bloc_{s['lettre'] or s['nom']}",
                "bloc": "Profil du répondant" if identification else s["nom"], "condition_texte": "",
                "facultatif": False, "niveau_tag": " / ".join([s["tag"]] + tags).strip(" /"), "base": it["num"],
                "consigne": " ".join(it["consignes"]), "posee_si": " ; ".join(it["posee_si"])}
        if it["sinon"]:
            auto.append(it["num"])
        if tl.startswith("ouverte"):
            if s["genre"] == "cloture" or re.search(r"telephone|e-?mail|coordonnees", _bas(texte)):
                continue  # coordonnées : la clôture de la plateforme les recueille déjà
            ouvertes.append({**base, "num": it["num"], "type": "ouverte", "facultatif": "facultati" in tl,
                             "apres": developpees[-1]["num"] if developpees else None})
            continue
        type_ = "multiple" if tl.startswith("choix multiple") else "unique"
        if "[liste pays" in tl or any(p.strip().startswith("[") for p in it["puces"]):
            a_completer.append(it["num"])
        if tl.startswith("grille"):
            rangs, cols, extra = [], [], []  # rangs : (numéro, libellé, condition, réponse propre à la ligne)
            if it.get("table"):
                tete = [_bas(c) for c in it["table"][0]]
                k_lib = next((k for k, c in enumerate(tete) if re.search(r"crit|ligne$|libell|item", c) and "si" not in c.split()), 1)
                k_cond = next((k for k, c in enumerate(tete) if "si" in c.split() or "affich" in c), None)
                # en-tête « Ligne affichée si (B0) » : chaque cellule est une réponse de cette question
                ref_cond = (m.group(1) if k_cond is not None and (m := re.search(r"\(([A-Z]\d{1,2}[a-z]?)\)", it["table"][0][k_cond])) else None)
                for l in it["table"][1:]:
                    n, lib = (l[0] if l else ""), (l[k_lib] if k_lib < len(l) else "")
                    if not lib:
                        continue
                    if not re.match(r"^\d+$", n.strip()):
                        controles.append(it["num"])
                        continue
                    propre = None
                    if (m := re.search(r"\s*·\s*modalit[ée]\s*«\s*([^»]+?)\s*»", lib)):
                        propre, lib = m.group(1), lib[:m.start()] + lib[m.end():]
                    cond = l[k_cond].strip() if k_cond is not None and k_cond < len(l) else ""
                    if ref_cond and cond and not re.match(rf"^{_REF}\b", cond):
                        cond = f"{ref_cond} = {cond}"
                    rangs.append((n.strip(), lib.strip(), None if re.match(r"(?i)^(\S+ = )?toujours$|^$", cond) else cond, propre))
            for p in it["puces"]:
                if (m := re.match(r"^lignes?\s*:\s*(.+)$", p, re.I)):
                    rangs += [(None, *_condition_puce(x), None) for x in _decouper_puce(m.group(1))]
                elif (m := re.match(r"^colonnes?\s*:\s*(.+)$", p, re.I)):
                    cols += _decouper_puce(m.group(1))
                elif re.match(r"contr[ôo]le d'attention|ligne de contr[ôo]le", _bas(p)):
                    controles.append(it["num"])
                else:
                    rangs.append((None, *_condition_puce(p), None))
            if not cols:
                if (m := re.search(r"(\d+)\s*=\s*([^,·«]+?)\s*,\s*(\d+)\s*=\s*([^,·«]+)", it["type_ligne"])):
                    lo, hi = int(m.group(1)), int(m.group(3))
                    cols = [f"{v} – {m.group(2).strip()}" if v == lo else f"{v} – {m.group(4).strip()}" if v == hi else str(v) for v in range(lo, hi + 1)]
                    extra = re.findall(r"«\s*([^»]+?)\s*»", it["type_ligne"])
                elif "oui / non" in tl or "oui/non" in tl:
                    cols = ["Oui", "Non"]
            mods = [{"code": c.split(" – ")[0] if re.match(r"^\d+( – |$)", c) else str(k), "label": c} for k, c in enumerate(cols, 1)]
            mods += [{"code": str(98 - k), "label": e} for k, e in enumerate(extra)]
            for k, (n, r, cond, propre) in enumerate(rangs, 1):
                m_r = mods + ([{"code": "97", "label": propre}] if propre else [])
                developpees.append({**base, "num": f"{it['num']}_{n or k}", "texte": f"{texte.rstrip(' ?:')} — {r}", "type": "unique",
                                    "modalites": m_r, "libelle": f"{r} ({it['num']})", "routes": [], "posee_si_ligne": cond})
            continue
        groupes = [g for g in it["groupes"] if g["puces"]] or [{"tag": "", "puces": it["puces"]}]
        for g_k, g in enumerate(groupes):
            labels, routes = [], []
            for p in (it["puces"] + g["puces"] if g["tag"] else g["puces"]):
                if p.strip().startswith("["):
                    continue
                if (m := re.search(r"\b(?:coch[ée]e?s?|cit[ée]e?s?) en ([A-Z]\d{1,2})\b", p)):
                    it["copie_de"] = m.group(1)  # « Opérateurs cochés en A7 uniquement »
                    continue
                if (m := re.match(r"^exemples?\s*:\s*(.+)$", p, re.I)):
                    labels += _decouper_puce(m.group(1)) if "," in m.group(1) else [m.group(1)]
                    continue
                cible = None
                if (m := re.search(r"\s*→\s*(.+)$", p)):
                    p, cible = p[:m.start()].strip(), m.group(1).strip()
                p, _ = _condition_puce(p)
                for l in _decouper_puce(p):
                    labels.append(l)
                    if cible:
                        routes.append((l, cible))
            if tl.startswith("echelle") and (m := re.search(r"(\d+)\s*a\s*(\d+)", tl)):
                lo, hi = int(m.group(1)), int(m.group(2))
                bornes = dict(re.findall(r"(\d+)\s*=\s*([^·,]+)", " ".join(it["puces"])))
                labels = [f"{v} – {bornes[str(v)].strip()}" if str(v) in bornes else str(v) for v in range(lo, hi + 1)]
                mods = [{"code": str(v), "label": l} for v, l in zip(range(lo, hi + 1), labels)]
            else:
                mods = _codes(labels, type_)
            num = it["num"] if len(groupes) == 1 else f"{it['num']}{'abcdefgh'[g_k]}"
            q = {**base, "num": num, "type": type_, "modalites": mods, "routes": routes}
            if g["tag"]:
                q["niveau_tag"] = g["tag"]
                court = re.sub(r"\s+", " ", texte).rstrip(" ?:")[:70]
                q["libelle"] = f"{court} ({g['tag']})"
            if (m := re.search(r"(\d+)\s+r[ée]ponses?\s+maximum", it["type_ligne"], re.I)):
                q["max_choix"] = int(m.group(1))
            if (m := re.search(r"(?:parmi les r[ée]ponses [àa]|m[êe]mes modalit[ée]s que)\s+([A-Z]\d+)", it["type_ligne"], re.I)):
                q["copie_de"] = m.group(1).upper()
            elif it.get("copie_de"):
                q["copie_de"] = it["copie_de"]
            # la question de cible (« Vous répondez en tant que ») : la première trouvée, « en tant que » avant « vous êtes »
            cible_q = s["genre"] == "profil" and len(mods) > 1 and not any(x.get("role") == "fonction" for x in developpees)
            if cible_q and re.search(r"\ben tant que\b", _bas(texte)):
                q["role"] = "fonction"
            elif cible_q and re.search(r"\b(vous etes|je suis)\b", _bas(texte)) and not any(
                    re.search(r"\ben tant que\b", _bas(x["texte"])) for x in items if x["section"]["genre"] == "profil"):
                q["role"] = "fonction"
            else:
                q["role"] = _role(texte)
            developpees.append(q)
    # réponses reprises d'une autre question (« parmi les réponses à A7 », « mêmes modalités que E3 »)
    par_base = {}
    for q in developpees:
        par_base.setdefault(q["base"], q)
    for q in developpees:
        if q.get("copie_de") in par_base:
            propres = [m for m in q["modalites"] if not re.match(r"^(aucun|aucune)\b", _bas(m["label"]))]
            src = [m for m in par_base[q["copie_de"]]["modalites"] if not re.match(r"^(aucun|aucune|ne sait pas)\b", _bas(m["label"]))]
            q["modalites"] = _codes([m["label"] for m in src] + [m["label"] for m in q["modalites"] if m not in propres], q["type"])
            copies.append(q["num"])
    # renvois : « → fin » met fin au questionnaire ; « → X » saute les questions intermédiaires
    position = {}
    for k, q in enumerate(developpees):
        position.setdefault(q["base"], k)
    debut_bloc = {}
    for k, q in enumerate(developpees):
        debut_bloc.setdefault(q["section"], k)
    for k, q in enumerate(developpees):
        codes = {m["label"]: m["code"] for m in q["modalites"]}
        sauts = {}
        for lib, cible in q["routes"]:
            c, bas = codes.get(lib), _bas(cible)
            if not c:
                continue
            if re.match(r"^fin\b(?! du bloc)", bas):
                q.setdefault("exclut", []).append(c)
                continue
            if bas.startswith("fin du bloc"):
                fin = next((j for j in range(k + 1, len(developpees)) if developpees[j]["section"] != q["section"]), len(developpees))
            elif (m := re.match(r"^bloc\s+([0-9a-z])\b", bas)):
                lettre = m.group(1).upper()
                fin = debut_bloc.get("A" if lettre == "0" else f"bloc_{lettre}", len(developpees))
            elif (m := re.match(r"^([a-z]\d{1,2}[a-z]?)\b", bas)) and (m.group(1)[0].upper() + m.group(1)[1:]) in position:
                fin = position[m.group(1)[0].upper() + m.group(1)[1:]]
            else:
                continue
            for j in range(k + 1, fin):
                if developpees[j]["base"] != q["base"]:
                    sauts.setdefault(j, set()).add(c)
        for j, sautes in sauts.items():
            # la question n'est posée que pour les autres réponses (forme positive : réponse absente = question masquée)
            garder = [m["code"] for m in q["modalites"] if m["code"] not in sautes]
            if garder:
                developpees[j]["clauses"] = [{"num": q["num"], "valeurs": garder, "sauf": False}]  # le renvoi le plus proche l'emporte
    # profils de la cible (question « Vous répondez en tant que ») : mentions [PME / GE] et conditions sur le profil
    fonction = next((q for q in developpees if q.get("role") == "fonction"), None)
    profils = [m["label"] for m in fonction["modalites"] if not _bas(m["label"]).startswith("autre")] if fonction else []

    def _sigle(label):
        mots = [w for w in re.findall(r"[a-z]+", _bas(_hors_parentheses(label))) if len(w) > 2 and w not in ("une", "des", "les", "pour")]
        return "".join(w[0] for w in mots)

    def _singulier(t):
        return " ".join(w[:-1] if len(w) > 3 and w.endswith("s") else w for w in re.findall(r"[a-z0-9']+", _bas(t)))

    def _profils_cites(texte):
        retenus = set()
        for jeton in re.split(r"\s*/\s*|\s*,\s*|\s+ou\s+|\s+et\s+", texte):
            j = _singulier(re.sub(r"^(les|le|la|l')\s*", "", _bas(jeton))).strip()
            if len(j) < 2:
                continue
            for lab in profils:
                if j in _singulier(lab) or (len(j) <= 3 and j in _sigle(lab)):
                    retenus.add(lab)
        return retenus

    def _code_profil(lab):
        return slug(_nettoyer_liste(lab), maxi=20)

    for q in developpees:
        if q.get("niveau_tag") and profils:
            retenus = _profils_cites(q["niveau_tag"])
            if retenus and len(retenus) < len(profils):
                q["niveau"] = [_code_profil(l) for l in profils if l in retenus]
    # conditions écrites en clair : « Posée si : A4 = Oui », « D1 = Oui et D3 ≠ Une seule fois », lignes « (si D7 banque = Oui) »
    par_num = {q["num"]: q for q in developpees}

    def _question(ref, precision):
        if ref == "profil_final":
            return fonction
        if precision:  # ligne d'une grille : « D7 banque », « D7 mobile money »
            lignes = [q for q in developpees if q["base"] == ref and q["num"] != ref]
            notes_l = [(_proche(precision, re.sub(r"\s*\([A-Z]\d+\)$", "", q.get("libelle", ""))), q) for q in lignes]
            meilleur = max(notes_l, key=lambda x: x[0], default=(0, None))
            return meilleur[1] if meilleur[0] else None
        return par_num.get(ref)

    def _traduire(texte):
        """Clauses (reliées par « ou ») et profils concernés ; None si la condition n'est pas lisible."""
        t = re.sub(r"\.\s.*$", "", texte.strip()).rstrip(" .")  # première phrase seulement
        clauses, niveau = [], None
        for ou in re.split(rf"\s+ou\s+(?={_REF}\b)", t):
            retenue = None
            for et in re.split(rf"\s+et\s+(?={_REF}\b)", ou):
                m = re.match(rf"^({_REF})(?:\s+([^=≠!]+?))?\s*(=|≠|!=)\s*(.+)$", et.strip())
                if not m:
                    return None
                q = _question(m.group(1), (m.group(2) or "").strip())
                if q is None:
                    return None
                valeurs = [v.strip() for v in re.split(r"\s+ou\s+", m.group(4)) if v.strip()]
                sauf = m.group(3) != "="
                if q is fonction:
                    cites = set().union(*[_profils_cites(v) for v in valeurs]) if valeurs else set()
                    if not cites:
                        return None
                    gardes = [l for l in profils if (l in cites) != sauf]
                    niveau = [_code_profil(l) for l in gardes]
                    continue
                choisies = [x for x in (_choisir(v, q["modalites"]) for v in valeurs) if x]
                if len(choisies) != len(valeurs):
                    return None
                codes = [x["code"] for x in choisies]
                garder = [x["code"] for x in q["modalites"] if (x["code"] in codes) != sauf]
                if garder:
                    cl = {"num": q["num"], "valeurs": garder, "sauf": False}  # forme positive
                    # « et » : la clause sur la question la plus tardive suffit (elle n'est posée que si les autres le sont)
                    if retenue is None or developpees.index(q) > developpees.index(par_num[retenue["num"]]):
                        retenue = cl
            if retenue:
                clauses.append(retenue)
        return clauses, niveau

    for q in developpees + ouvertes:
        # la condition propre à une ligne de grille, plus précise, passe avant celle de la grille entière
        ligne = q.pop("posee_si_ligne", None)
        res_ligne = _traduire(ligne) if ligne else None
        textes = [("ligne", ligne, res_ligne)] if res_ligne else []
        if not res_ligne:
            textes = [("question", q.pop("posee_si", None), None)] + ([("ligne", ligne, None)] if ligne else [])
        else:
            q.pop("posee_si", None)
        for _, texte, res in textes:
            if not texte:
                continue
            res = res or _traduire(texte)
            if res is None:
                if q.get("role") not in ("pays", "fonction", "enqueteur", "restitution"):  # gérées par la plateforme
                    non_lues.append(q["num"])
                q["consigne"] = (q.get("consigne", "") + " " if q.get("consigne") else "") + f"Posée si : {texte}"
                continue
            clauses, niveau = res
            if clauses:
                q["clauses"] = clauses  # la condition écrite prime sur celle déduite des renvois
            if niveau:
                q["niveau"] = [c for c in niveau if c in q["niveau"]] if q.get("niveau") else niveau
    for q in developpees + ouvertes:
        q.pop("routes", None)
        q.pop("niveau_tag", None)
    if ouvertes:
        notes.append(f"Questions ouvertes ({', '.join(o['num'] for o in ouvertes)}) : ajoutées au questionnaire comme questions de texte, "
                     "à leur place, avec leur condition ; collectées mais non calculées dans le rapport.")
    if a_completer:
        notes.append(f"Listes à établir pays par pays ({', '.join(a_completer)}) : banques, opérateurs… à compléter dans l'étape Questionnaire.")
    if copies:
        notes.append(f"Réponses reprises d'une question précédente ({', '.join(copies)}) : la liste complète est proposée, sans filtrage sur la réponse donnée.")
    if controles:
        notes.append(f"Ligne de contrôle d'attention ({', '.join(sorted(set(controles)))}) non reprise : à traiter à l'apurement.")
    if non_lues:
        notes.append(f"Conditions écrites non traduites ({', '.join(non_lues)}) : reportées en consigne, à programmer à la main.")
    if auto:
        notes.append(f"Remplissages automatiques (« Sinon : », {', '.join(auto)}) non programmés : à calculer à l'analyse.")
    return developpees + ouvertes, notes


def _condition(texte, par_num):
    """« Si B1 ≠ Jamais », « Si E4 = Oui, en production ou E4 = Oui, en phase pilote », « Si Aucun de ces outils non coché en C1 »."""
    clauses = []
    t = re.sub(r"^si\s+", "", texte.strip(), flags=re.I)
    morceaux = [m for p in re.split(r"\s+ou\s+(?=[A-Z]\d+\s*[=≠]|.+?coch)", t) for m in re.split(r"\s+et\s+", p)]
    for m in morceaux:
        if (r := re.match(r"^([A-Z]\d+)\s*(=|≠)\s*(.+)$", m.strip())):
            num, op, lib = r.group(1).upper(), r.group(2), r.group(3).strip()
            sauf = op == "≠"
        elif (r := re.match(r"^(.+?)\s+(non\s+)?coch[ée]e?\s+en\s+([A-Z]\d+)$", m.strip(), re.I)):
            lib, sauf, num = r.group(1).strip(), bool(r.group(2)), r.group(3).upper()
        else:
            continue
        q = par_num.get(num)
        if not q:
            continue
        code = next((x["code"] for x in q["modalites"] if _sans_accents(x["label"]) == _sans_accents(lib)), None)
        if not code:
            continue
        for c in clauses:
            if c["num"] == num and c["sauf"] == sauf:
                c["valeurs"].append(code)
                break
        else:
            clauses.append({"num": num, "valeurs": [code], "sauf": sauf})
    return clauses


def _vers_indicateurs(questions, format_):
    """Une question = un indicateur ; les questions d'identification prises en charge par la plateforme sont écartées."""
    par_num = {q["num"]: q for q in questions}
    retenues = [q for q in questions if q.get("role") not in ("enqueteur", "pays", "secteur", "fonction", "restitution")
                and q["type"] != "ouverte"]
    ids = {q["num"]: f"I{k:02d}" for k, q in enumerate(retenues, 1)}
    inds = []
    for q in retenues:
        bloc = q["bloc"] if format_ in ("note", "redige") or q["section"] != "A" else "Profil de l'entreprise"
        ind = {"id": ids[q["num"]], "libelle": q.get("libelle") or re.sub(r"\s+", " ", q["texte"]).rstrip(" ?:")[:90],
               "type": q["type"], "bloc": bloc, "niveau": q.get("niveau") or "tous",
               "actif": True, "sens": "", "objet": "", "question": q["texte"],
               "options": [{"code": m["code"], "label": m["label"]} if m["code"] else m["label"] for m in q["modalites"]]}
        if format_ == "redige":
            ind["code_origine"] = q["num"]  # code du questionnaire d'origine (B2_3…), repris par le plan d'analyse et les scores
        if q.get("consigne"):
            ind["consigne"] = q["consigne"]
        if q["section"] == "A":
            ind["identification"] = True
        if q.get("exclut"):
            ind["exclut"] = q["exclut"]
        if q["type"] == "multiple":
            ind["max_choix"] = q.get("max_choix", 0)
        clauses = [c for c in q.get("clauses") or [] if c["num"] in ids]  # renvois et conditions d'un questionnaire rédigé
        if clauses:
            ind["condition"] = [{"si": ids[c["num"]], "valeurs": c["valeurs"], "sauf": c["sauf"]} for c in clauses]
        if q.get("condition_texte") and format_ == "technique":
            clauses = [c for c in _condition(q["condition_texte"], par_num) if c["num"] in ids]
            if clauses:
                ind["condition"] = [{"si": ids[c["num"]], "valeurs": c["valeurs"], "sauf": c["sauf"]} for c in clauses]
        inds.append(ind)
    return inds


def _ouvertes(questions):
    """Questions ouvertes d'un questionnaire rédigé : placées après la question qui les précède, avec leur condition."""
    retenues = [q for q in questions if q.get("role") not in ("enqueteur", "pays", "secteur", "fonction", "restitution")
                and q["type"] != "ouverte"]
    ids = {q["num"]: f"I{k:02d}" for k, q in enumerate(retenues, 1)}
    res = []
    for q in questions:
        if q["type"] != "ouverte":
            continue
        res.append({"num": q["num"], "texte": q["texte"], "bloc": q["bloc"], "facultatif": q.get("facultatif", False),
                    "consigne": q.get("consigne", ""), "niveau": q.get("niveau") or "tous", "apres": ids.get(q.get("apres")),
                    "condition": [{"si": ids[c["num"]], "valeurs": c["valeurs"], "sauf": c["sauf"]}
                                  for c in q.get("clauses") or [] if c["num"] in ids]})
    return res


def ajouter_ouvertes(projet, ouvertes):
    """Ajoute au questionnaire généré les questions ouvertes de l'import, chacune sous la question qui la précède."""
    from . import moteur
    if not ouvertes:
        return projet
    d = projet["etapes"]["questionnaire"]["data"]
    if not d.get("sections"):  # questionnaire pas encore généré
        return projet
    sections = d["sections"]
    profils = {p["code"] for p in d.get("profils") or []}
    deja = {q["id"] for s in sections for q in s["ids"]}
    for o in ouvertes:
        ident = f"aj_ouv_{slug(o['num'], maxi=8)}"
        if ident in deja:
            continue
        q = {"id": ident, "texte": o["texte"], "type": "text", "modalites": [], "ajoutee": True, "modifiee": True,
             "dans_rapport": False, "bloc": o["bloc"], "obligatoire": not o["facultatif"], "consigne": o["consigne"],
             "profils": [c for c in o["niveau"] if c in profils] if isinstance(o["niveau"], list) else None,
             "conditions": [[f"q_{c['si']}", c["valeurs"], c["sauf"]] for c in o["condition"]], "num": "…", "var": "…"}
        place = None
        for si, s in enumerate(sections):
            for qi, x in enumerate(s["ids"]):
                if o["apres"] and x.get("indicateur") == o["apres"]:
                    place = (si, qi + 1)
        if place is None:  # question précédente absente : en fin de la section du même bloc, sinon avant la clôture
            si = next((k for k, s in enumerate(sections) if s["titre"] == o["bloc"]), len(sections) - 2)
            place = (si, len(sections[si]["ids"]))
        sections[place[0]]["ids"].insert(place[1], q)
    return moteur.maj_data(projet, "questionnaire", {"sections": sections})


# ------------------------------------------------------------------ proposition complète
def proposer(chemin_note, chemin_questionnaire=None):
    """Proposition d'étude à vérifier : fiche, contexte, objectifs, indicateurs (et leur origine), points d'attention."""
    prop, notes = analyser_note(lire(chemin_note))
    prop["origine_indicateurs"] = "note" if prop["indicateurs"] else "aucune"
    if chemin_questionnaire:
        questions, format_, n2 = analyser_questionnaire(lire(chemin_questionnaire))
        notes += n2
        prop["format_questionnaire"] = format_
        ident = {q["role"]: q for q in questions if q.get("role")}
        f = prop["fiche"]
        # les questions d'identification du questionnaire précisent le champ de l'étude
        if "pays" in ident:
            pays_q = [m["label"] for m in ident["pays"]["modalites"] if not _bas(m["label"]).startswith("autre")]
            if f.get("zones") and set(map(_sans_accents, pays_q)) != set(map(_sans_accents, re.split(r"\s*,\s*", f["zones"]))):
                notes.append(f"Pays : la note en cite {len(re.split(r'\s*,\s*', f['zones']))}, le questionnaire {len(pays_q)} ; "
                             "la liste du questionnaire est retenue.")
            f["zones"] = ", ".join(pays_q)
        if "secteur" in ident:
            f["secteur"] = ", ".join(_nettoyer_liste(m["label"]) for m in ident["secteur"]["modalites"] if not m["label"].lower().startswith("autre"))
        if "fonction" in ident:
            f["cible"] = ", ".join(_nettoyer_liste(m["label"]) for m in ident["fonction"]["modalites"] if not m["label"].lower().startswith("autre"))
        # les alertes de la note sur un champ que le questionnaire a fourni n'ont plus lieu d'être
        for cle, lib in (("zones", "les pays"), ("cible", "la cible")):
            if f.get(cle):
                notes = [n for n in notes if n != f"La note ne précise pas {lib} de façon reconnaissable : à compléter."]
        inds = _vers_indicateurs(questions, format_)
        prop["questions_ouvertes"] = _ouvertes(questions)
        if inds and prop["indicateurs"] and format_ == "terrain":
            # la note a son tableau d'indicateurs (types d'échelle, indice) : il prime sur un questionnaire terrain
            notes.append("Indicateurs repris du tableau de la note (types et indice conservés) ; le questionnaire a servi à préciser le champ.")
        elif inds:
            prop["indicateurs"] = inds
            prop["origine_indicateurs"] = "questionnaire"
        grilles = sorted({q["base"] for q in questions if q.get("base") and q["num"] != q["base"] and q.get("libelle", "").endswith(f"({q['base']})")}
                         | {q["num"].split(".")[0] for q in questions if "." in q["num"]})
        if grilles:
            notes.append(f"Grilles ({', '.join(grilles)}) : chaque ligne devient une question à choix unique.")
    elif prop["indicateurs"]:
        sans_options = [i["libelle"] for i in prop["indicateurs"] if i["type"] in ("unique", "multiple")]
        if sans_options:
            notes.append(f"{len(sans_options)} indicateur(s) à choix n'ont pas de modalités dans la note : complétez-les dans l'étape Cadrage.")
    elif len(prop["questions_note"]) >= 3:  # une question isolée dans une note rédigée n'est pas un questionnaire
        # questions écrites dans la note elle-même : une question = un indicateur
        prop["indicateurs"] = _vers_indicateurs(prop["questions_note"], "note")
        prop["origine_indicateurs"] = "questions_note"
        qs = prop["indicateurs"]
        a_completer = sum(1 for q in qs if q["type"] in ("unique", "multiple") and not q["options"])
        oui_non = sum(1 for q in qs if q["options"] == ["Oui", "Non"])
        notes.append(f"{len(qs)} questions lues dans la note, reprises une par une comme indicateurs"
                     + (f" ; {oui_non} en Oui / Non d'après leur formulation" if oui_non else "")
                     + (f" ; {a_completer} sans liste de réponses (banques, opérateurs, réponses libres…) : à compléter dans l'étape Questionnaire" if a_completer else "")
                     + ".")
    prop.pop("questions_note", None)
    if prop["origine_indicateurs"] == "aucune":
        notes.append("Aucun tableau d'indicateurs ni questionnaire : la plateforme proposera les indicateurs de sa banque, à ajuster.")
    return prop, notes


# ------------------------------------------------------------------ création de l'étude
def creer_etude(prop, fiche, chemin_note, chemin_questionnaire=None, valider=True):
    """Crée l'étude à partir de la proposition vérifiée : cadrage repris de la note (validé si demandé), documents
    d'origine conservés, questionnaire généré à partir des indicateurs."""
    import shutil
    from . import moteur, store
    from .etapes import cadrage
    p = store.creer({**prop["fiche"], **fiche})
    sources = store.dossier(p["slug"]) / "sources"
    sources.mkdir(parents=True, exist_ok=True)
    noms = {}
    for cle, chemin in (("note", chemin_note), ("questionnaire", chemin_questionnaire)):
        if chemin:
            cible = sources / f"{cle}_origine{chemin.suffix}"
            shutil.copy(chemin, cible)
            noms[cle] = cible.name
    moteur.generer(p, "cadrage")
    d = p["etapes"]["cadrage"]["data"]
    if prop.get("indicateurs"):
        d["indicateurs"] = prop["indicateurs"]
        d["domaine"] = "Importé"
    if prop.get("contexte"):
        d["contexte"] = prop["contexte"]
    if prop.get("complement_contexte"):
        d["contexte"] = list(d.get("contexte") or []) + prop["complement_contexte"]
    if prop.get("objectifs"):
        d["objectifs_specifiques"] = prop["objectifs"]
    d["redaction"] = "importee"
    d["sources"] = noms
    d["theme_ref"] = [p["fiche"]["theme"], p["fiche"]["objectif"]]
    p["etapes"]["cadrage"]["data"] = cadrage.normaliser(d)
    store.journaliser(p, "Note de cadrage importée" + (" avec son questionnaire" if chemin_questionnaire else "") + ".")
    moteur._apres_maj(p, "cadrage")
    if valider:
        moteur.valider(p, "cadrage")
        moteur.generer(p, "questionnaire")
        p = ajouter_ouvertes(p, prop.get("questions_ouvertes"))
    return p
