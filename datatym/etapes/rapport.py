"""Étape 7 — Rapport d'analyse : calcul des indicateurs, graphiques, lecture par profil, enseignements."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from .. import llm  # noqa: E402
from ..banque import NSP_CODE, TYPES, du_barometre, slug, sont_des_pays  # noqa: E402
from ..charte import chiffres, image, liste, p, section, tableau  # noqa: E402
from ..outils import aujourdhui, fmt_marge, nombre, pct, solde_txt  # noqa: E402
from ..store import dossier  # noqa: E402
from .collecte import lire, valides, variables_cles  # noqa: E402

DOCS = {"rapport_analyse": ("RapportAnalyse", "Rapport d'analyse")}
SEUIL = 30
ROMAINS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV"]

ENCRE, ENCRE2, GRILLE = "#19243E", "#4B5563", "#E5E7EB"
DIVERGENT = ["#0B5FA5", "#5AAEE8", "#C9D3E0", "#F2A07B", "#C8553D"]
BLEU = "#0087E0"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": GRILLE, "axes.labelcolor": ENCRE2,
                     "xtick.color": ENCRE2, "ytick.color": ENCRE, "axes.spines.top": False, "axes.spines.right": False})


# ------------------------------------------------------------------ calculs
def _serie(df, var):
    return df[var].astype(str).str.strip() if var in df else pd.Series(dtype=str)


def stats_echelle(s, ind, mods):
    s = s[s != ""]
    n = len(s)
    if not n:
        return {"n": 0}
    dist = {m["code"]: 100 * (s == m["code"]).sum() / n for m in mods}
    hors_nsp = s[s != NSP_CODE]
    nh = len(hors_nsp) or 1
    pos = 100 * hors_nsp.isin(TYPES[ind["type"]]["positifs"]).sum() / nh
    neg = 100 * hors_nsp.isin(TYPES[ind["type"]]["negatifs"]).sum() / nh
    dist_exp = {m["code"]: 100 * (hors_nsp == m["code"]).sum() / nh for m in mods if m["code"] != NSP_CODE}
    r = {"n": n, "dist": dist, "dist_exp": dist_exp, "nsp": 100 * (s == NSP_CODE).sum() / n, "positif": pos, "negatif": neg, "solde": pos - neg}
    if ind["type"] == "satisfaction":
        r["moyenne"] = pd.to_numeric(hors_nsp, errors="coerce").mean()
    return r


def stats_multiple(s, mods):
    s = s[s != ""]
    n = len(s)
    if not n:
        return {"n": 0}
    morceaux = s.str.split()
    return {"n": n, "citations": {m["code"]: 100 * morceaux.map(lambda l, c=m["code"]: c in l).sum() / n for m in mods}}


def stats_unique(s, mods):
    s = s[s != ""]
    n = len(s)
    return {"n": n, "dist": {m["code"]: 100 * (s == m["code"]).sum() / n for m in mods}} if n else {"n": 0}


def calculer(df, ind, q, groupes):
    var, mods = q["var"], q["modalites"]
    f = stats_multiple if ind["type"] == "multiple" else (stats_unique if ind["type"] == "unique" else None)
    calc = (lambda s: f(s, mods)) if f else (lambda s: stats_echelle(s, ind, mods))
    res = {"global": calc(_serie(df, var))}
    for nom, (col, valeurs) in groupes.items():
        res[nom] = {code: calc(_serie(df[df[col] == code], var)) for code in valeurs} if col in df else {}
    return res


def analyser(projet, cadrage, quest, ech):
    brut = lire(projet)
    if brut is None or brut.empty:
        return None
    df = valides(brut, quest)
    _, v_zone, v_prof = variables_cles(quest)
    lib_prof = {pr["code"]: pr["libelle"] for pr in quest["profils"]}
    lib_zone = {slug(z, maxi=18): z for z in ech["zones"]}
    groupes = {"par_profil": (v_prof, list(lib_prof)), "par_zone": (v_zone, list(lib_zone))}
    q_de = {q["indicateur"]: q for q in quest["questions_plates"] if q.get("indicateur")}
    resultats = []
    for ind in cadrage["indicateurs"]:
        if not ind.get("actif", True) or ind["type"] == "indice" or ind["id"] not in q_de:
            continue
        q = q_de[ind["id"]]
        r = calculer(df, ind, q, groupes)
        resultats.append({"id": ind["id"], "libelle": ind["libelle"], "type": ind["type"], "bloc": ind["bloc"], "var": q["var"],
                          "question": q["texte"], "modalites": q["modalites"], **r})
    par_id = {r["id"]: r for r in resultats}
    for ind in cadrage["indicateurs"]:
        if ind.get("actif", True) and ind["type"] == "indice":
            comps = [par_id[c] for c in ind.get("composantes", []) if c in par_id]

            def val(getter):
                soldes = [getter(c) for c in comps]
                soldes = [x for x in soldes if x is not None]
                return (sum(soldes) / len(soldes) + 100) / 2 if soldes else None
            r = {"id": ind["id"], "libelle": ind["libelle"], "type": "indice", "bloc": "Synthèse",
                 "global": {"n": len(df), "valeur": val(lambda c: c["global"].get("solde"))}, "composantes": [c["id"] for c in comps]}
            for g in groupes:
                r[g] = {code: {"n": max([c[g].get(code, {}).get("n", 0) for c in comps] or [0]),
                               "valeur": val(lambda c, code=code: c[g].get(code, {}).get("solde"))} for code in groupes[g][1]}
            resultats.insert(0, r)
    return {"n": len(df), "n_brut": len(brut), "lib_profil": lib_prof, "lib_zone": lib_zone,
            "effectifs_profil": {c: int((df.get(v_prof, "") == c).sum()) for c in lib_prof},
            "effectifs_zone": {c: int((df.get(v_zone, "") == c).sum()) for c in lib_zone},
            "resultats": resultats}


# ------------------------------------------------------------------ graphiques
def _sauver(fig, chemin):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(chemin, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return chemin


def graphique(r, an, dossier_g):
    chemin = dossier_g / f"{r['id']}.png"
    lp, lz = an["lib_profil"], an["lib_zone"]
    if r["type"] == "indice":
        lignes = [("Ensemble", r["global"]["valeur"])] + [(lp[c], v["valeur"]) for c, v in r["par_profil"].items() if v["n"] >= SEUIL]
        lignes += [(lz[c], v["valeur"]) for c, v in r["par_zone"].items() if v["n"] >= SEUIL]
        lignes = [(a, b) for a, b in lignes if b is not None]
        fig, ax = plt.subplots(figsize=(6.4, 0.42 * len(lignes) + 0.8))
        noms = [a for a, _ in lignes][::-1]
        vals = [b for _, b in lignes][::-1]
        ax.barh(noms, vals, color=[ENCRE if n == "Ensemble" else BLEU for n in noms], height=0.6)
        ax.axvline(50, color=ENCRE2, lw=1, ls="--")
        ax.set_xlim(0, 100)
        for y, v in enumerate(vals):
            ax.text(v + 1.2, y, nombre(v, 1), va="center", color=ENCRE, fontsize=9, fontweight="bold")
        ax.set_xlabel("Indice (0 à 100) — 50 = équilibre des opinions")
        ax.grid(axis="x", color=GRILLE, lw=0.6)
        ax.set_axisbelow(True)
        return _sauver(fig, chemin)
    if r["type"] in ("multiple", "unique"):
        cle = "citations" if r["type"] == "multiple" else "dist"
        items = sorted(((m["label"], r["global"].get(cle, {}).get(m["code"], 0)) for m in r["modalites"]), key=lambda x: x[1])
        fig, ax = plt.subplots(figsize=(6.4, 0.36 * len(items) + 0.7))
        ax.barh([a for a, _ in items], [b for _, b in items], color=BLEU, height=0.62)
        for y, (_, v) in enumerate(items):
            ax.text(v + 0.8, y, pct(v), va="center", color=ENCRE, fontsize=8.5)
        ax.set_xlim(0, max([b for _, b in items] + [10]) * 1.18)
        ax.xaxis.set_visible(False)
        ax.spines["bottom"].set_visible(False)
        return _sauver(fig, chemin)
    # échelles : barres empilées Ensemble + profils
    # du plus favorable au plus défavorable : codes ordinaux décroissants (bleu = favorable)
    mods = sorted((m for m in r["modalites"] if m["code"] != NSP_CODE), key=lambda m: -int(m["code"]) if m["code"].isdigit() else 0)
    lignes = [("Ensemble", r["global"])] + [(lp[c], v) for c, v in r["par_profil"].items() if v.get("n", 0) >= SEUIL]
    fig, ax = plt.subplots(figsize=(6.4, 0.5 * len(lignes) + 1.0))
    couleurs = DIVERGENT if len(mods) == 5 else ([DIVERGENT[0], DIVERGENT[2], DIVERGENT[4]] if len(mods) == 3 else [DIVERGENT[0], DIVERGENT[1], DIVERGENT[3], DIVERGENT[4]])
    noms = [a for a, _ in lignes][::-1]
    gauche = [0.0] * len(lignes)
    for k, m in enumerate(mods):
        vals = [st.get("dist_exp", {}).get(m["code"], 0) for _, st in lignes][::-1]
        ax.barh(noms, vals, left=gauche, color=couleurs[k % len(couleurs)], height=0.6, label=m["label"], edgecolor="white", linewidth=0.8)
        for y, (g, v) in enumerate(zip(gauche, vals)):
            if v >= 7:
                ax.text(g + v / 2, y, f"{v:.0f}", ha="center", va="center", fontsize=8, color="white" if k in (0, len(mods) - 1) else ENCRE)
        gauche = [g + v for g, v in zip(gauche, vals)]
    ax.set_xlim(0, 100)
    ax.xaxis.set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.legend(ncol=min(len(mods), 5), loc="upper center", bbox_to_anchor=(0.5, -0.02), frameon=False, fontsize=7.5)
    ax.set_title("En % des répondants ayant exprimé une opinion (hors « Ne sait pas »)", fontsize=7.5, color=ENCRE2, loc="left")
    return _sauver(fig, chemin)


# ------------------------------------------------------------------ rédaction
def lecture(r, an):
    g = r["global"]
    lp = an["lib_profil"]
    if not g.get("n"):
        return "Aucune réponse exploitable pour cet indicateur."
    if r["type"] == "indice":
        v = g["valeur"]
        pos = "au-dessus" if v >= 50 else "en dessous"
        txt = f"L'indice s'établit à **{nombre(v, 1)} sur 100**, {pos} du seuil d'équilibre de 50 : "
        txt += "les opinions favorables l'emportent sur les opinions défavorables." if v >= 50 else "les opinions défavorables l'emportent."
        prof = [(lp[c], x["valeur"]) for c, x in r["par_profil"].items() if x["n"] >= SEUIL and x["valeur"] is not None]
        if len(prof) > 1:
            hi, lo = max(prof, key=lambda x: x[1]), min(prof, key=lambda x: x[1])
            txt += f" Par profil, l'indice varie de {nombre(lo[1], 1)} ({lo[0]}) à {nombre(hi[1], 1)} ({hi[0]})."
        return txt
    if r["type"] in ("multiple", "unique"):
        cle = "citations" if r["type"] == "multiple" else "dist"
        items = sorted(((m["label"], g[cle].get(m["code"], 0)) for m in r["modalites"]), key=lambda x: -x[1])
        verbe = "citent" if r["type"] == "multiple" else "choisissent"
        txt = f"**{pct(items[0][1])}** des répondants {verbe} « {items[0][0]} »"
        if len(items) > 1:
            txt += f", devant « {items[1][0]} » ({pct(items[1][1])})"
        if len(items) > 2:
            txt += f" et « {items[2][0]} » ({pct(items[2][1])})"
        return txt + f". Base : {g['n']} répondants concernés."
    txt = (f"Le solde d'opinion s'établit à **{solde_txt(g['solde'])} points** : {pct(g['positif'])} de réponses favorables "
           f"contre {pct(g['negatif'])} de réponses défavorables (base : {g['n']} répondants).")
    if r["type"] == "satisfaction" and g.get("moyenne") == g.get("moyenne"):
        txt += f" La note moyenne atteint {nombre(g['moyenne'], 1)} sur 5."
    prof = [(lp[c], x["solde"]) for c, x in r["par_profil"].items() if x.get("n", 0) >= SEUIL]
    if len(prof) > 1:
        hi, lo = max(prof, key=lambda x: x[1]), min(prof, key=lambda x: x[1])
        if hi[1] - lo[1] >= 10:
            txt += f" L'écart entre profils est marqué : {solde_txt(hi[1])} pour le profil « {hi[0]} » contre {solde_txt(lo[1])} pour le profil « {lo[0]} »."
        else:
            txt += " Les profils partagent une appréciation proche."
    return txt


def chiffre_cle(r):
    g = r["global"]
    if not g.get("n"):
        return None
    if r["type"] == "indice":
        return [f"{nombre(g['valeur'], 1)}/100", f"{r['libelle']}"]
    if r["type"] in ("multiple", "unique"):
        cle = "citations" if r["type"] == "multiple" else "dist"
        m, v = max(((m["label"], g[cle].get(m["code"], 0)) for m in r["modalites"]), key=lambda x: x[1])
        return [pct(v), f"{r['libelle']} : « {m} » arrive en tête"]
    if r["type"] == "intention":
        return [pct(g["positif"]), f"{r['libelle']} (taux d'intention)"]
    if r["type"] == "satisfaction":
        return [pct(g["positif"]), f"{r['libelle']} (part de satisfaits)"]
    return [f"{solde_txt(g['solde'])} pts", f"{r['libelle']} (solde d'opinion)"]


def messages_regles(an):
    res = an["resultats"]
    msgs = []
    indice = next((r for r in res if r["type"] == "indice" and r["global"].get("valeur") is not None), None)
    if indice:
        msgs.append(f"{indice['libelle']} : {nombre(indice['global']['valeur'], 1)}/100, "
                    + ("des opinions majoritairement favorables." if indice["global"]["valeur"] >= 50 else "des opinions majoritairement défavorables."))
    soldes = [r for r in res if "solde" in r["global"]]
    if soldes:
        hi = max(soldes, key=lambda r: r["global"]["solde"])
        lo = min(soldes, key=lambda r: r["global"]["solde"])
        msgs.append(f"Point le plus favorable : {hi['libelle'].lower()} ({solde_txt(hi['global']['solde'])} pts).")
        msgs.append(f"Point le plus fragile : {lo['libelle'].lower()} ({solde_txt(lo['global']['solde'])} pts).")
    for r in res:
        if r["type"] == "multiple" and r["global"].get("n"):
            m, v = max(((m["label"], r["global"]["citations"].get(m["code"], 0)) for m in r["modalites"]), key=lambda x: x[1])
            msgs.append(f"{r['libelle']} : « {m} » est citée par {pct(v)} des répondants.")
    ecarts = []
    for r in soldes:
        prof = [(an["lib_profil"][c], x["solde"]) for c, x in r["par_profil"].items() if x.get("n", 0) >= SEUIL]
        if len(prof) > 1:
            hi, lo = max(prof, key=lambda x: x[1]), min(prof, key=lambda x: x[1])
            ecarts.append((hi[1] - lo[1], r, hi, lo))
    if ecarts:
        e, r, hi, lo = max(ecarts, key=lambda x: x[0])
        msgs.append(f"Plus fort écart entre profils sur {r['libelle'].lower()} : {solde_txt(hi[1])} profil « {hi[0]} », {solde_txt(lo[1])} profil « {lo[0]} ».")
    return msgs


def enseignements_regles(an):
    res = an["resultats"]
    ens = []
    neg = [r for r in res if "solde" in r["global"] and r["global"]["solde"] < 0]
    pos = [r for r in res if "solde" in r["global"] and r["global"]["solde"] > 20]
    if pos:
        ens.append("Des points d'appui nets : " + ", ".join(r["libelle"].lower() for r in pos[:3]) + ".")
    if neg:
        ens.append("Des signaux de vigilance à suivre de près lors de la prochaine édition : " + ", ".join(r["libelle"].lower() for r in neg[:3]) + ".")
    ens.append("Les écarts entre profils invitent à des réponses différenciées selon le niveau de responsabilité des répondants.")
    ens.append("La reconduction du baromètre avec les mêmes indicateurs permettra de transformer ces constats en tendances.")
    return ens


def _redaction_ia(projet, an):
    synthese = []
    for r in an["resultats"]:
        g = r["global"]
        if r["type"] == "indice":
            synthese.append(f"{r['libelle']} : {g.get('valeur')}")
        elif "solde" in g:
            synthese.append(f"{r['libelle']} : solde {round(g['solde'])} ; favorables {round(g['positif'])} % ; par profil "
                            + ", ".join(f"{an['lib_profil'][c]} {round(x['solde'])}" for c, x in r["par_profil"].items() if x.get("n", 0) >= SEUIL))
        elif g.get("n"):
            cle = "citations" if r["type"] == "multiple" else "dist"
            synthese.append(f"{r['libelle']} : " + ", ".join(f"{m['label']} {round(g[cle].get(m['code'], 0))} %" for m in r["modalites"]))
    schema = {"type": "object", "properties": {
        "messages_cles": {"type": "array", "items": {"type": "string"}},
        "enseignements": {"type": "array", "items": {"type": "string"}},
        "conclusion": {"type": "string"}},
        "required": ["messages_cles", "enseignements", "conclusion"], "additionalProperties": False}
    consigne = (f"Baromètre « {projet['fiche']['theme']} » ({an['n']} répondants). Objectif : {projet['fiche']['objectif']}.\n"
                "Résultats calculés :\n- " + "\n- ".join(synthese) +
                "\n\nRédige 5 messages clés pour la direction (une phrase chacun, avec les chiffres exacts fournis), "
                "4 enseignements (faits → implication pour la décision, sans causalité non démontrée) et une conclusion de 2 à 3 phrases.")
    return llm.generer_json(consigne, schema)


# ------------------------------------------------------------------ étape
def generer(projet, cadrage, quest, ech, precedent=None):
    prec = precedent or {}
    an = analyser(projet, cadrage, quest, ech)
    data = {"analyse": an, "titre": prec.get("titre") or projet["fiche"]["theme"],
            "sous_titre": prec.get("sous_titre") or "Rapport d'analyse"}
    if an:
        ia = _redaction_ia(projet, an) if llm.disponible() else None
        data["messages"] = (ia or {}).get("messages_cles") or messages_regles(an)
        data["enseignements"] = (ia or {}).get("enseignements") or enseignements_regles(an)
        data["conclusion"] = (ia or {}).get("conclusion") or (
            "Ce baromètre fournit une photographie de référence. Sa valeur tiendra à sa répétition : les mêmes indicateurs, "
            "mesurés selon la même méthode, permettront de suivre les évolutions et d'évaluer l'effet des décisions prises.")
        data["redaction"] = "ia" if ia else "regles"
    return data


def construire_docs(projet, data, ech):
    fiche = projet["fiche"]
    an = data.get("analyse")
    if not an:
        return {"rapport_analyse": {"titre": "Rapport d'analyse", "surtitre": "Baromètre Datatym", "sous_titre": fiche["theme"], "meta": [],
                                    "en_tete": "", "sections": [section("vide", "Données manquantes", [p("Importez les données de collecte pour générer le rapport.")], source="auto")]}}
    dg = dossier(projet["slug"]) / "graphiques"
    rel = lambda c: str(c.relative_to(dossier(projet["slug"]).parent.parent))  # noqa: E731
    lp, lz = an["lib_profil"], an["lib_zone"]
    Z = "Pays" if sont_des_pays(list(lz.values())) else "Zone"
    res = an["resultats"]
    n = an["n"]
    chif = [c for c in (chiffre_cle(r) for r in res) if c][:10]

    sections = [
        section("guide", "Comment lire ce rapport", [
            p(f"Ce rapport présente les résultats {du_barometre(fiche['theme'])}, établis à partir de **{n} questionnaires valides**. "
              "Il se lit d'un bout à l'autre pour disposer du diagnostic complet ; le lecteur pressé trouvera l'essentiel dans les messages clés "
              "et les chiffres à retenir."),
            p("Un **solde d'opinion** est la différence entre la part de réponses favorables et la part de réponses défavorables. Il varie de −100 "
              "à +100 : un solde positif signifie que les opinions favorables l'emportent. Un **indice** ramène ces soldes sur une échelle de 0 à 100, "
              "50 marquant l'équilibre."),
            p("Ce document distingue les faits (chiffres issus des données Datatym) de leur interprétation. Lorsque deux données évoluent "
              "ensemble, le texte parle d'association, jamais de causalité. Aucun résultat n'est présenté pour un groupe de moins de 30 répondants."),
        ]),
        section("messages", "Les messages clés", [liste(data.get("messages", []))]),
        section("chiffres", "Les chiffres à retenir", [tableau(["Chiffre", "Ce qu'il mesure"], chif, "Chiffres à retenir", [1, 3.5])], source="auto"),
        section("repondants", "I. Qui sont les répondants", [
            p(f"L'analyse porte sur {n} questionnaires valides, sur {an['n_brut']} formulaires reçus (refus, hors-cible et entretiens trop rapides exclus)."),
            tableau(["Profil", "Effectif", "Part", "Marge d'erreur"],
                    [[lp[c], v, pct(100 * v / n if n else 0), fmt_marge(v)] for c, v in an["effectifs_profil"].items()], "Répartition par profil"),
            tableau([Z, "Effectif", "Part", "Marge d'erreur"],
                    [[lz[c], v, pct(100 * v / n if n else 0), fmt_marge(v)] for c, v in an["effectifs_zone"].items()], f"Répartition par {Z.lower()}"),
        ], source="auto"),
    ]
    chap = 1
    indice = next((r for r in res if r["type"] == "indice"), None)
    if indice and indice["global"].get("valeur") is not None:
        chap += 1
        g = graphique(indice, an, dg)
        noms = {r["id"]: r["libelle"] for r in res}
        sections.append(section(f"ch_{indice['id']}", f"{ROMAINS[chap - 1]}. {indice['libelle']}", [
            chiffres([{"valeur": f"{nombre(indice['global']['valeur'], 1)}", "libelle": f"{indice['libelle']} (sur 100)"}]),
            p(lecture(indice, an)),
            image(rel(g), f"{indice['libelle']} par profil et par {Z.lower()}", 15),
            p("Composantes : " + "; ".join(noms.get(c, c) for c in indice.get("composantes", [])) + ".", "note"),
        ], source="auto"))
    blocs = []
    for r in res:
        if r["type"] != "indice" and r["bloc"] not in blocs:
            blocs.append(r["bloc"])
    for bloc in blocs:
        chap += 1
        blocs_doc = []
        for r in [x for x in res if x["bloc"] == bloc]:
            g = graphique(r, an, dg)
            blocs_doc.append({"type": "p", "texte": f"**{r['libelle']}**", "style": "normal"})
            blocs_doc.append(p(f"Question posée : « {r['question']} »", "note"))
            blocs_doc.append(image(rel(g), r["libelle"], 14.5))
            blocs_doc.append(p(lecture(r, an)))
            if "solde" in r["global"]:
                lignes = [["Ensemble", r["global"]["n"], pct(r["global"]["positif"]), pct(r["global"]["negatif"]), solde_txt(r["global"]["solde"])]]
                for grp, labels in (("par_profil", lp), ("par_zone", lz)):
                    for c, x in r[grp].items():
                        if x.get("n", 0) >= SEUIL:
                            lignes.append([labels[c], x["n"], pct(x["positif"]), pct(x["negatif"]), solde_txt(x["solde"])])
                        elif x.get("n"):
                            lignes.append([labels[c], x["n"], "effectif insuffisant", "", ""])
                blocs_doc.append(tableau(["Groupe", "Base", "Favorables", "Défavorables", "Solde"], lignes, f"{r['libelle']} selon le profil et {'le pays' if Z == 'Pays' else 'la zone'}", taille=9))
        sections.append(section(f"ch_{slug(bloc)}", f"{ROMAINS[chap - 1]}. {bloc}", blocs_doc, source="auto"))
    sections += [
        section("enseignements", f"{ROMAINS[chap]}. Enseignements", [liste(data.get("enseignements", []))]),
        section("methode", "Annexe : méthode et limites", [
            p(f"Enquête quantitative par questionnaire, échantillonnage non probabiliste par quotas (zone × profil), {n} questionnaires valides "
              f"collectés auprès de {fiche['cible']}. Marge d'erreur indicative sur l'ensemble : {fmt_marge(n)} (intervalle de confiance à 95 %, cas le plus défavorable)."),
        ], source="auto"),
        section("conclusion", "Conclusion", [p(data.get("conclusion", ""))]),
    ]
    return {"rapport_analyse": {
        "titre": data.get("titre") or fiche["theme"], "surtitre": "Baromètre Datatym — Rapport d'analyse", "sous_titre": data.get("sous_titre", ""),
        "meta": [f"{n} répondants · {', '.join(ech['zones'])}", f"Version du {aujourdhui()} — diffusion restreinte"],
        "en_tete": f"Baromètre {fiche['theme']} — Rapport d'analyse", "sommaire": True, "sections": sections,
    }}
