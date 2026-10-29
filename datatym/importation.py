"""Import d'une note de cadrage déjà rédigée (Word), avec ou sans son questionnaire, pour lancer une étude.

La note fournit la fiche (thème, objectif, cible, pays, secteurs, taille, durée), le contexte, les objectifs et, si elle
en a un, le tableau des indicateurs. Le questionnaire, s'il est joint, fournit les indicateurs (une question = un
indicateur) avec leurs codes, leurs modalités et leurs conditions ; ses questions d'identification précisent les pays,
les secteurs et les fonctions. Deux formats de questionnaire sont lus : « technique » (N°, Variable, Question,
Modalités, Type, Condition) et « terrain » (Code, Question, Consigne, Réponses).
"""
import re

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
                if (m := re.match(r"objectif g[ée]n[ée]ral\s*:\s*(.+)", b["texte"], re.I)):
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
    if "taille" not in prop["fiche"] and (m := re.search(r"\b(\d[\d\s]{1,5})\s+(?:dirigeants|répondants|entreprises|questionnaires|personnes|ménages)", texte_tout)):
        prop["fiche"]["taille"] = int(m.group(1).replace(" ", ""))
    if "duree" not in prop["fiche"]:
        # seulement une durée rattachée au terrain (« 15 jours de collecte », « terrain de 40 jours »)
        if (m := re.search(r"(?:terrain|collecte|enqu[êe]te)[^.]{0,60}?\b(\d{1,3})\s+jours\b|\b(\d{1,3})\s+jours\s+de\s+(?:terrain|collecte)", texte_tout, re.I)):
            prop["fiche"]["duree"] = int(m.group(1) or m.group(2))
        elif (m := re.search(r"\b(\d{1,2})\s+semaines\b", texte_tout)):
            prop["fiche"]["duree"] = 7 * int(m.group(1))
            notes.append(f"Durée déduite de « {m.group(0)} » : à vérifier, c'est peut-être la durée totale de l'étude et non celle du terrain.")
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
            pays_q = [m["label"] for m in ident["pays"]["modalites"]]
            if f.get("zones") and set(map(_sans_accents, pays_q)) != set(map(_sans_accents, re.split(r"\s*,\s*", f["zones"]))):
                notes.append(f"Pays : la note en cite {len(re.split(r'\s*,\s*', f['zones']))}, le questionnaire {len(pays_q)} ; "
                             "la liste du questionnaire est retenue.")
            f["zones"] = ", ".join(pays_q)
        if "secteur" in ident:
            f["secteur"] = ", ".join(_nettoyer_liste(m["label"]) for m in ident["secteur"]["modalites"] if not m["label"].lower().startswith("autre"))
        if "fonction" in ident:
            f["cible"] = ", ".join(_nettoyer_liste(m["label"]) for m in ident["fonction"]["modalites"] if not m["label"].lower().startswith("autre"))
        par_num = {q["num"]: q for q in questions}
        retenues = [q for q in questions if q.get("role") not in ("enqueteur", "pays", "secteur", "fonction", "restitution")]
        ids = {q["num"]: f"I{k:02d}" for k, q in enumerate(retenues, 1)}
        inds = []
        for q in retenues:
            ind = {"id": ids[q["num"]], "libelle": q.get("libelle") or re.sub(r"\s+", " ", q["texte"]).rstrip(" ?")[:90],
                   "type": q["type"], "bloc": "Profil de l'entreprise" if q["section"] == "A" else q["bloc"], "niveau": "tous",
                   "actif": True, "sens": "", "objet": "", "question": q["texte"],
                   "options": [{"code": m["code"], "label": m["label"]} if m["code"] else m["label"] for m in q["modalites"]]}
            if q["section"] == "A":
                ind["identification"] = True
            if q.get("exclut"):
                ind["exclut"] = q["exclut"]
            if q["type"] == "multiple":
                ind["max_choix"] = q.get("max_choix", 0)
            if q.get("condition_texte") and prop.get("format_questionnaire") == "technique":
                clauses = [c for c in _condition(q["condition_texte"], par_num) if c["num"] in ids]
                if clauses:
                    ind["condition"] = [{"si": ids[c["num"]], "valeurs": c["valeurs"], "sauf": c["sauf"]} for c in clauses]
            inds.append(ind)
        if inds and prop["indicateurs"] and format_ == "terrain":
            # la note a son tableau d'indicateurs (types d'échelle, indice) : il prime sur un questionnaire terrain
            notes.append("Indicateurs repris du tableau de la note (types et indice conservés) ; le questionnaire a servi à préciser le champ.")
        elif inds:
            prop["indicateurs"] = inds
            prop["origine_indicateurs"] = "questionnaire"
        grilles = sorted({q["num"].split(".")[0] for q in questions if "." in q["num"]})
        if grilles:
            notes.append(f"Grilles ({', '.join(grilles)}) : chaque ligne devient une question à choix unique.")
    elif prop["indicateurs"]:
        sans_options = [i["libelle"] for i in prop["indicateurs"] if i["type"] in ("unique", "multiple")]
        if sans_options:
            notes.append(f"{len(sans_options)} indicateur(s) à choix n'ont pas de modalités dans la note : complétez-les dans l'étape Cadrage.")
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
    return p
