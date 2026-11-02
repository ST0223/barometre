"""Apurement des données : corrections tracées, recodage des « Autre (préciser) », doublons, base finale figée.

Les corrections ne touchent jamais la base des soumissions (donnees/collecte.csv) : elles sont rejouées à chaque lecture,
dans l'ordre du journal. La base figée (donnees/base_finale.csv) est celle du rapport et de la restitution ; le suivi
de la collecte et la paie restent sur les données du moment.
"""
import html
import re
from datetime import date

import pandas as pd
from openpyxl import Workbook

from .config import auteur_fichiers
from .formulaires import _feuille
from .outils import date_fr
from .store import dossier, maintenant

AUTRES = ("autre", "autre_hors")   # modalités « Autre (préciser) » et « Autre fonction » (hors cible)
GARDER = "autre"                   # recodage revu : la réponse reste en « Autre »
EXCLURE = "_exclure"               # correction qui écarte toute la réponse


def donnees(projet):
    return (projet["etapes"]["collecte"].get("data") or {}).setdefault("apurement", {"corrections": [], "recodages": {}, "figee": None})


def chemin_finale(projet):
    return dossier(projet["slug"]) / "donnees" / "base_finale.csv"


def figee(projet):
    return bool(((projet["etapes"]["collecte"].get("data") or {}).get("apurement") or {}).get("figee"))


def _quest(projet):
    return projet["etapes"]["questionnaire"].get("data") or {}


def _norm(texte):
    """Clé de regroupement d'un texte « Autre » : sans accents, casse ni ponctuation (entités HTML de QuestionPro décodées)."""
    from .etapes.collecte import _norm as n
    return n(html.unescape(str(texte or "")))


def actives(projet):
    return [c for c in donnees(projet)["corrections"] if not c.get("annulee")]


def appliquer(projet, df, exclure=True, recoder=True):
    """Rejoue le journal sur la base : réponses écartées, valeurs corrigées, « Autre » recodés."""
    a = ((projet["etapes"]["collecte"].get("data") or {}).get("apurement")) or {}
    corrections = [c for c in a.get("corrections") or [] if not c.get("annulee")]
    if df is None or df.empty or "_id" not in df:
        return df
    df = df.copy()
    ids = df["_id"].astype(str)
    if exclure:
        ecartees = {c["id"] for c in corrections if c["var"] == EXCLURE}
        if ecartees:
            df, ids = df[~ids.isin(ecartees)], ids[~ids.isin(ecartees)]
    for c in corrections:
        if c["var"] != EXCLURE:
            if c["var"] not in df:
                df[c["var"]] = ""
            df.loc[ids == c["id"], c["var"]] = c["apres"]
    if recoder:
        types = {q["var"]: q["type"] for q in _quest(projet).get("questions_plates") or []}
        for var, table in (a.get("recodages") or {}).items():
            col = f"{var}_autre"
            table = {k: v for k, v in table.items() if v and v != GARDER}
            if not table or var not in df or col not in df:
                continue
            for i in df.index[df[col].astype(str).str.strip() != ""]:
                code = table.get(_norm(df.at[i, col]))
                if not code:
                    continue
                jetons = str(df.at[i, var]).split()
                if not any(j in AUTRES for j in jetons):
                    continue
                if types.get(var) == "select_multiple":
                    nouveaux = []
                    for j in jetons:
                        j = code if j in AUTRES else j
                        if j not in nouveaux:
                            nouveaux.append(j)
                    df.at[i, var] = " ".join(nouveaux)
                else:
                    df.at[i, var] = code
    return df


def _base_brute(projet):
    """Base des soumissions sans aucune règle appliquée (toutes les lignes, identifiants garantis)."""
    from .etapes import collecte
    f = collecte.chemin_donnees(projet)
    if not f.exists():
        return None
    return collecte.avec_identifiants(pd.read_csv(f, dtype=str, keep_default_na=False))


def autres(projet):
    """Réponses « Autre (préciser) » regroupées par texte, question par question, avec le recodage choisi."""
    from .etapes import collecte
    df = collecte.lire(projet, apurer=False)
    if df is None or df.empty:
        return []
    df = appliquer(projet, df, recoder=False)
    recodages = donnees(projet)["recodages"]
    res = []
    for q in _quest(projet).get("questions_plates") or []:
        var, col = q["var"], f"{q['var']}_autre"
        if q["type"] not in ("select_one", "select_multiple") or col not in df or var not in df:
            continue
        sel = df[df[var].astype(str).str.split().map(lambda js: any(j in AUTRES for j in js)) & (df[col].astype(str).str.strip() != "")]
        if sel.empty:
            continue
        groupes = {}
        for t in sel[col].astype(str).map(html.unescape).str.strip():
            g = groupes.setdefault(_norm(t), {"cle": _norm(t), "textes": {}, "n": 0})
            g["n"] += 1
            g["textes"][t] = g["textes"].get(t, 0) + 1
        items = [{"cle": g["cle"], "texte": max(g["textes"], key=g["textes"].get), "n": g["n"],
                  "code": (recodages.get(var) or {}).get(g["cle"], "")} for g in groupes.values() if g["cle"]]
        items.sort(key=lambda x: (-x["n"], x["texte"]))
        res.append({"var": var, "num": q["num"], "question": q["texte"], "type": q["type"], "items": items,
                    "modalites": [{"code": m["code"], "label": m["label"]} for m in q.get("modalites") or [] if m["code"] not in AUTRES]})
    return res


def recoder(projet, var, cle, code):
    q = next((x for x in _quest(projet).get("questions_plates") or [] if x["var"] == var), None)
    if not q:
        raise ValueError("Question introuvable.")
    if code and code != GARDER and code not in {m["code"] for m in q.get("modalites") or []}:
        raise ValueError("Modalité inconnue pour cette question.")
    table = donnees(projet)["recodages"].setdefault(var, {})
    if code:
        table[cle] = code
    else:
        table.pop(cle, None)


def _tel(x):
    chiffres = re.sub(r"\D", "", str(x or ""))
    return chiffres[-8:] if len(chiffres) >= 8 else ""


def doublons(projet):
    """Réponses suspectes d'être des doublons, à vérifier : même téléphone, même entreprise et même fonction,
    ou réponses identiques à toutes les questions."""
    from .etapes import collecte
    df = collecte.lire(projet)
    quest = _quest(projet)
    if df is None or df.empty:
        return []
    par = {q["id"]: q["var"] for q in quest.get("questions_plates") or []}
    v_enq, v_zone, v_prof = collecte.variables_cles(quest)
    col_enq = "enqueteur" if "enqueteur" in df else v_enq
    cons = df.get("consentement", pd.Series(["oui"] * len(df), index=df.index)).astype(str).str.lower().isin(["oui", "1", "yes"])
    df = df[cons]
    groupes, vus = [], set()

    def ajouter(motif, sous):
        ids = tuple(sorted(sous["_id"].astype(str)))
        if len(ids) < 2 or ids in vus:
            return
        vus.add(ids)
        groupes.append({"motif": motif, "reponses": [
            {"id": str(l["_id"]), "collecteur": str(l.get(col_enq, "") or ""), "date": str(l.get("start", ""))[:16].replace("T", " "),
             "duree": str(l.get("duree_minutes", "") or "")} for _, l in sous.iterrows()]})

    if par.get("cl_telephone") in df:
        tel = df[par["cl_telephone"]].map(_tel)
        for t, sous in df[tel != ""].groupby(tel[tel != ""]):
            ajouter("Même numéro de téléphone", sous)
    if par.get("cl_entreprise") in df:
        ent = df[par["cl_entreprise"]].map(_norm)
        cles = ent + "|" + (df[v_prof].astype(str) if v_prof in df else "")
        for c, sous in df[ent != ""].groupby(cles[ent != ""]):
            ajouter("Même entreprise et même fonction", sous)
    vars_q = [q["var"] for q in quest.get("questions_plates") or [] if q["var"] in df and q["id"] != "id_enqueteur"]
    if vars_q:
        empreinte = df[vars_q].astype(str).agg("|".join, axis=1)
        for e, sous in df.groupby(empreinte):
            if len(sous) > 1 and e.replace("|", "").strip():
                ajouter("Réponses identiques à toutes les questions", sous)
    return groupes[:60]


def corriger(projet, ident, var, valeur, motif):
    from .etapes import collecte
    motif = str(motif or "").strip()
    if not motif:
        raise ValueError("Indiquez le motif de la correction : il figure au journal.")
    brut = collecte.lire(projet, apurer=False)
    if brut is None or "_id" not in brut or str(ident) not in set(brut["_id"].astype(str)):
        raise ValueError(f"Aucune réponse avec l'identifiant « {ident} ».")
    ident = str(ident)
    if any(c["id"] == ident and c["var"] == EXCLURE for c in actives(projet)):
        raise ValueError("Cette réponse est déjà écartée.")
    if var == EXCLURE:
        avant, apres = "", ""
    else:
        q = next((x for x in _quest(projet).get("questions_plates") or [] if x["var"] == var), None)
        if not q:
            raise ValueError("Variable inconnue.")
        apres = str(valeur or "").strip()
        if q["type"] in ("select_one", "select_multiple") and apres:
            codes = {m["code"] for m in q.get("modalites") or []}
            inconnus = [c for c in apres.split() if c not in codes]
            if inconnus or (q["type"] == "select_one" and len(apres.split()) > 1):
                raise ValueError("Valeur hors des modalités de la question.")
        courant = appliquer(projet, brut, exclure=False)
        ligne = courant[courant["_id"].astype(str) == ident]
        avant = str(ligne.iloc[0].get(var, "")) if len(ligne) else ""
        if avant == apres:
            raise ValueError("La valeur est déjà celle-ci.")
    journal = donnees(projet)["corrections"]
    c = {"n": max((x["n"] for x in journal), default=0) + 1, "date": maintenant(), "type": "exclusion" if var == EXCLURE else "correction",
         "id": ident, "var": var, "avant": avant, "apres": apres, "motif": motif[:300]}
    journal.append(c)
    return c


def annuler(projet, n):
    c = next((x for x in donnees(projet)["corrections"] if x["n"] == int(n)), None)
    if not c or c.get("annulee"):
        raise ValueError("Correction introuvable.")
    c["annulee"] = maintenant()   # la ligne reste au journal, barrée : rien ne disparaît de la trace
    return c


def figer(projet):
    """Base finale : les données apurées du moment, enregistrées telles quelles pour le rapport et la restitution."""
    from .etapes import collecte
    df = collecte.lire(projet)
    if df is None or df.empty:
        raise ValueError("Aucune réponse à figer.")
    f = chemin_finale(projet)
    f.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(f, index=False)
    a = donnees(projet)
    brut = _base_brute(projet)
    controle = projet["etapes"]["collecte"]["data"].get("controle_qualite", True)
    cons = df.get("consentement", pd.Series(["oui"] * len(df), index=df.index)).astype(str).str.lower().isin(["oui", "1", "yes"])
    valides = len(collecte.valides(df, _quest(projet))) if controle else int(cons.sum())
    a["figee"] = {"date": maintenant(), "version": len(a.get("gels") or []) + 1,
                  "brut": len(brut), "lignes": len(df), "valides": valides,
                  "corrections": len([c for c in actives(projet) if c["var"] != EXCLURE]),
                  "exclusions": len([c for c in actives(projet) if c["var"] == EXCLURE]),
                  "recodages": sum(1 for t in a["recodages"].values() for v in t.values() if v and v != GARDER)}
    a.setdefault("gels", []).append(dict(a["figee"]))
    return a["figee"]


def defiger(projet):
    a = donnees(projet)
    a["figee"] = None
    f = chemin_finale(projet)
    if f.exists():
        f.unlink()


def synthese(projet):
    a = ((projet["etapes"]["collecte"].get("data") or {}).get("apurement")) or {}
    act = [c for c in a.get("corrections") or [] if not c.get("annulee")]
    fig = a.get("figee")
    res = {"corrections": sum(c["var"] != EXCLURE for c in act), "exclusions": sum(c["var"] == EXCLURE for c in act),
           "recodages": sum(1 for t in (a.get("recodages") or {}).values() for v in t.values() if v and v != GARDER), "figee": fig}
    if fig:
        brut = _base_brute(projet)
        res["nouvelles"] = max(len(brut) - fig["brut"], 0) if brut is not None else 0
    return res


def statuts(projet):
    """Statut de chaque soumission : valide, ou motif pour lequel elle est écartée."""
    from .etapes import collecte
    from . import rappels
    brut = _base_brute(projet)
    if brut is None:
        return None
    quest = _quest(projet)
    df = appliquer(projet, brut, exclure=False)
    ids = df["_id"].astype(str)
    motifs = pd.Series("", index=df.index)
    ecartees = {c["id"]: c["motif"] for c in actives(projet) if c["var"] == EXCLURE}
    motifs[ids.isin(ecartees)] = ids[ids.isin(ecartees)].map(lambda i: f"Écartée à l'apurement : {ecartees[i]}")
    motifs[(motifs == "") & ids.isin(rappels.invalides(projet))] = "Entretien non réalisé (rappel de contrôle)"
    cons = df.get("consentement", pd.Series(["oui"] * len(df), index=df.index)).astype(str).str.lower().isin(["oui", "1", "yes"])
    motifs[(motifs == "") & ~cons] = "Refus de participer"
    if projet["etapes"]["collecte"]["data"].get("controle_qualite", True):
        _, _, v_prof = collecte.variables_cles(quest)
        hors = df.get(v_prof, pd.Series([""] * len(df), index=df.index)) == "autre_hors"
        for x in quest.get("questions_plates") or []:
            if x.get("exclut") and x["var"] in df:
                hors |= df[x["var"]].isin(x["exclut"])
        motifs[(motifs == "") & hors] = "Hors cible"
        ok = set(collecte.valides(collecte.lire(projet), quest)["_id"].astype(str))
        motifs[(motifs == "") & ~ids.isin(ok)] = "Durée suspecte (moins de 40 % de la durée médiane)"
    motifs[motifs == ""] = "Valide"
    return df.assign(statut_apurement=motifs.values)


def xlsx(chemin, projet):
    """Base apurée (avec le statut de chaque réponse), journal des corrections, recodages des « Autre », synthèse."""
    quest = _quest(projet)
    lib_var = {q["var"]: f"{q['num']}. {q['texte']}" for q in quest.get("questions_plates") or []}
    base = statuts(projet)
    if base is None:
        return None
    a = donnees(projet)
    wb = Workbook()
    ws = wb.active
    ws.title = "Synthèse"
    compte = base["statut_apurement"].map(lambda m: m.split(" :")[0]).value_counts()
    fig = a.get("figee")
    _feuille(ws, ["Élément", "Valeur"], [
        ["Soumissions reçues", len(base)], *[[f"Écartées : {k.lower()}" if k != "Valide" else "Réponses valides", int(v)] for k, v in compte.items()],
        ["Corrections de valeurs", sum(c["var"] != EXCLURE for c in actives(projet))],
        ["Réponses « Autre » recodées (textes distincts)", sum(1 for t in a["recodages"].values() for v in t.values() if v and v != GARDER)],
        ["Base finale", f"figée le {date_fr(date.fromisoformat(fig['date'][:10]))} (version {fig['version']})" if fig else "non figée : données du moment"],
    ], {"Élément": 48, "Valeur": 34})
    ws = wb.create_sheet("Base apurée")
    cols = ["_id", "statut_apurement"] + [c for c in base.columns if c not in ("_id", "statut_apurement")]
    _feuille(ws, cols, base[cols].astype(str).values.tolist())
    ws = wb.create_sheet("Journal des corrections")
    _feuille(ws, ["N°", "Date", "Type", "ID réponse", "Variable", "Question", "Avant", "Après", "Motif", "Annulée le"], [
        [c["n"], c["date"].replace("T", " ")[:16], "Réponse écartée" if c["var"] == EXCLURE else "Correction", c["id"],
         "" if c["var"] == EXCLURE else c["var"], lib_var.get(c["var"], ""), c["avant"], c["apres"], c["motif"],
         (c.get("annulee") or "").replace("T", " ")[:16]] for c in a["corrections"]], {"Question": 50, "Motif": 45})
    ws = wb.create_sheet("Recodages Autre")
    lignes = []
    for q in autres(projet):
        mods = {m["code"]: m["label"] for m in q["modalites"]}
        for it in q["items"]:
            lignes.append([f"{q['num']}. {q['question']}", it["texte"], it["n"],
                           "à traiter" if not it["code"] else ("laissée en « Autre »" if it["code"] == GARDER else mods.get(it["code"], it["code"]))])
    _feuille(ws, ["Question", "Texte saisi", "Occurrences", "Recodé en"], lignes, {"Question": 55, "Texte saisi": 40, "Recodé en": 30})
    wb.properties.creator = wb.properties.lastModifiedBy = auteur_fichiers()
    wb.save(chemin)
    return chemin
