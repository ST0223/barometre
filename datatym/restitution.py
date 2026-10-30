"""Supports de restitution, tirés du rapport d'analyse : présentation PowerPoint des résultats, note de synthèse,
infographie pour les réseaux et communiqué de presse. Produits à la clôture, rangés avec les livrables.
"""
import re
import textwrap
from datetime import date
from pathlib import Path

from .banque import du_barometre, nom_barometre, sont_des_pays
from .charte import chiffres, liste, p, rendre_modele, section, tableau
from .config import STATIC_DIR, auteur_fichiers, charger_parametres
from .outils import MOIS, aujourdhui, date_fr, fmt_marge, nombre, pct
from .store import dossier, maintenant, nom_fichier

SUPPORTS = [
    ("pptx", "Restitution_Resultats", "Présentation des résultats (PowerPoint)",
     "Support de la réunion de restitution : messages clés, chiffres, résultats commentés, méthode."),
    ("docx", "Note_Synthese", "Note de synthèse (Word)", "L'essentiel en deux pages pour le dirigeant ou le client."),
    ("png", "Infographie", "Infographie (image)", "Format portrait 1080 × 1350 pour LinkedIn, WhatsApp ou une newsletter."),
    ("docx", "Communique_Presse", "Communiqué de presse (Word)", "Annonce publique des résultats, à relire et compléter avant diffusion."),
]
MAX_RESULTATS = 8  # indicateurs détaillés dans la présentation


def disponible(projet):
    return bool((projet["etapes"]["rapport"].get("data") or {}).get("analyse"))


def _sans_gras(t):
    """Sans le gras Markdown, avec une espace insécable dans les guillemets et devant : ; % (jamais « seul en fin de ligne)."""
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t or "").replace("« ", "« ")
    return re.sub(r" ([:;%»?!])", " \\1", t)


def _court(texte, n):
    """Coupe à la fin d'une phrase sans dépasser n caractères."""
    t = _sans_gras(texte).strip()
    if len(t) <= n:
        return t
    coupe = t[:n]
    fin = max(coupe.rfind(". "), coupe.rfind(" ; "))
    return (coupe[:fin + 1] if fin > n * 0.4 else coupe.rsplit(" ", 1)[0] + "…").strip()


def chiffre(R, r):
    """Chiffre clé d'un indicateur ; pour un choix, la première réponse réelle (jamais « Ne sait pas »)."""
    if r["type"] in ("multiple", "unique") and r["global"].get("n"):
        for label, code, v in R._classement(r["global"], r):
            if not R._est_nsp(label, code):
                return [pct(v), f"{r['libelle']} : « {label} »"]
        return None
    return R.chiffre_cle(r)


def _contexte(projet):
    """Ce qu'il faut pour tous les supports : rapport, plan, chiffres clés, résultats à détailler."""
    from .etapes import rapport as R
    fiche = projet["fiche"]
    d = projet["etapes"]["rapport"]["data"]
    an = d["analyse"]
    ech = projet["etapes"]["echantillonnage"].get("data") or {}
    jours = ech.get("jours") or []
    zones = list(an["lib_zone"].values())
    stats = (projet["etapes"]["collecte"].get("data") or {}).get("stats")
    res = an["resultats"]
    x = an.get("indice_hc")
    chif = []
    if x:
        chif.append([f"{nombre(x['moyenne'], 1)}/100", f"Indice H&C de Maturité IA moyen, niveau {x['niveau_moyen']} « {x['niveaux'][x['niveau_moyen'] - 1]['nom']} »"])
    chif += [c for c in (chiffre(R, r) for r in res if not r.get("identification")) if c]
    detail = [r for r in res if not r.get("identification") and r["global"].get("n")][:MAX_RESULTATS]
    return {
        "fiche": fiche, "d": d, "an": an, "x": x, "res": res, "chif": chif, "detail": detail, "zones": zones,
        "pays": sont_des_pays(zones), "n": an["n"], "titre": nom_barometre(fiche["theme"]),
        "periode": (date_fr(jours[0]), date_fr(jours[-1])) if jours else None,
        # collecte encore en cours : les supports présentent des résultats provisoires
        "provisoire": bool(stats) and 0 < stats["jour_index"] < stats["nb_jours"],
        "collecte": (f"en cours depuis le {date_fr(jours[0])} (résultats provisoires au {date_fr(stats['reference'])})"
                     if stats and 0 < stats["jour_index"] < stats["nb_jours"] and jours
                     else f"du {date_fr(jours[0])} au {date_fr(jours[-1])}" if jours else ""),
        "messages": [_sans_gras(m) for m in d.get("messages") or []],
        "enseignements": [_sans_gras(m) for m in d.get("enseignements") or []],
        "conclusion": _sans_gras(d.get("conclusion") or ""),
        "limites": (projet["etapes"]["methodologie"].get("data") or {}).get("limites") or [],
        "dg": dossier(projet["slug"]) / "graphiques", "R": R,
    }


# ------------------------------------------------------------------ PowerPoint
def _image(deck, s, chemin, x, y, w_max, h_max):
    from PIL import Image
    with Image.open(chemin) as im:
        w, h = im.size
    k = min(w_max / (w / 200), h_max / (h / 200))  # graphiques enregistrés à 200 dpi
    lw, lh = w / 200 * k, h / 200 * k
    from .formation import _po
    s.shapes.add_picture(str(chemin), _po(x + (w_max - lw) / 2), _po(y + (h_max - lh) / 2), _po(lw), _po(lh))


def pptx(chemin, projet, c=None):
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN

    from .formation import BLEU, BLEU_PALE, CLAIR, GRIS, JAUNE, MARINE, OR, TEXTE, Deck
    c = c or _contexte(projet)
    R, an, x = c["R"], c["an"], c["x"]
    k = Deck(f"{c['titre']} · Restitution des résultats")
    mois = f"{MOIS[date.today().month - 1].capitalize()} {date.today().year}"
    k.couverture(c["titre"], "Restitution des résultats provisoires" if c["provisoire"] else "Restitution des résultats",
                 f"DATATYM, marque d'AGILTYM  ·  {mois}")

    # l'étude en bref
    s = k.contenu("L'étude en bref")
    k.soustitre(s, _court(c["fiche"].get("objectif") or "", 210))
    tuiles = [(str(c["n"]), "répondants" + (" validés" if an.get("controle", True) else "")),
              (str(len(c["zones"])), "pays" if c["pays"] else "zones"),
              (fmt_marge(c["n"]).replace(" pts", ""), "points de marge d'erreur"),
              (str(len(c["res"])), "indicateurs mesurés")]
    for i, (v, l) in enumerate(tuiles):
        xx = 0.6 + i * 3.08
        k.forme(s, xx, 1.95, 2.8, 2.1, MARINE)
        k.texte(s, xx + 0.25, 2.2, 2.3, 0.9, v, 40 if len(v) < 6 else 30, True, OR)
        k.texte(s, xx + 0.25, 3.2, 2.3, 0.7, l, 14, couleur="FFFFFF")
    k.forme(s, 0.6, 4.45, 12.1, 1.95, JAUNE)
    k.texte(s, 0.9, 4.65, 11.5, 1.7, [
        [("Cible : ", {"gras": True}), (c["fiche"]["cible"], {})],
        [("Champ : ", {"gras": True}), (", ".join(c["zones"]), {})],
        [("Collecte : ", {"gras": True}), (c["collecte"] or "—", {})],
        [("Méthode : ", {"gras": True}), ("enquête quantitative par questionnaire, échantillon par quotas", {})],
    ], 14, couleur=TEXTE, interligne=4)

    # messages clés
    if c["messages"]:
        k.intercalaire(1, "Les messages clés", "Ce qu'il faut retenir")
        s = k.contenu("Les messages clés")
        msgs = c["messages"][:5]
        h = min(1.0, 4.9 / len(msgs))
        for i, m in enumerate(msgs):
            y = 1.45 + i * (h + 0.12)
            k.forme(s, 0.6, y, 12.1, h, CLAIR)
            k.texte(s, 0.85, y, 0.8, h, f"{i + 1:02d}", 24, True, BLEU, ancre=MSO_ANCHOR.MIDDLE)
            k.texte(s, 1.8, y + 0.08, 10.7, h - 0.16, _court(m, 190), 15 if len(m) < 120 else 13, couleur=TEXTE, ancre=MSO_ANCHOR.MIDDLE)

    # chiffres à retenir
    if c["chif"]:
        s = k.contenu("Les chiffres à retenir")
        for i, (v, l) in enumerate(c["chif"][:6]):
            xx, y = 0.6 + (i % 3) * 4.1, 1.5 + (i // 3) * 2.55
            k.forme(s, xx, y, 3.85, 2.3, MARINE if i == 0 else CLAIR)
            k.texte(s, xx + 0.3, y + 0.25, 3.3, 0.9, v, 34 if len(v) < 9 else 26, True, OR if i == 0 else BLEU)
            k.texte(s, xx + 0.3, y + 1.15, 3.3, 1.05, _court(l, 95), 13, couleur="FFFFFF" if i == 0 else TEXTE)

    num = 2
    # Indice H&C
    if x:
        g1, g2 = R.graphiques_indice(x, c["dg"])
        k.intercalaire(num, "Indice H&C de Maturité IA", "Où en sont les entreprises ?")
        num += 1
        s = k.contenu("Le niveau de maturité des entreprises")
        k.forme(s, 0.6, 1.5, 3.9, 4.9, MARINE)
        k.texte(s, 0.9, 1.75, 3.4, 1.1, nombre(x["moyenne"], 1), 54, True, OR)
        k.texte(s, 0.9, 2.85, 3.4, 0.4, "sur 100, indice moyen", 14, couleur="FFFFFF")
        k.texte(s, 0.9, 3.5, 3.4, 2.7, [f"Niveau {x['niveau_moyen']}", f"« {x['niveaux'][x['niveau_moyen'] - 1]['nom']} »",
                                       f"{x['n']} entreprises"], 18, True, "FFFFFF", interligne=6)
        _image(k, s, g2, 4.8, 1.45, 7.9, 5.0)
        s = k.contenu("Les cinq piliers de la maturité")
        _image(k, s, g1, 0.6, 1.45, 7.3, 5.0)
        k.texte(s, 8.2, 1.6, 4.5, 4.8, _court(R.lecture_indice_hc(x), 520), 13, couleur=TEXTE)

    # résultats détaillés, bloc par bloc
    bloc = None
    for r in c["detail"]:
        if r["bloc"] != bloc:
            bloc = r["bloc"]
            k.intercalaire(num, bloc, "Résultats")
            num += 1
        g = R.graphique(r, an, c["dg"])
        s = k.contenu(_court(r["libelle"], 70))
        k.soustitre(s, _court(f"« {r['question']} »", 200) if r.get("question") else "")
        _image(k, s, g, 0.6, 1.75, 7.4, 4.75)
        cle = chiffre(R, r)
        if cle:
            k.forme(s, 8.3, 1.8, 4.4, 1.5, MARINE)
            k.texte(s, 8.55, 1.9, 3.9, 0.8, cle[0], 32, True, OR)
            k.texte(s, 8.55, 2.7, 3.9, 0.55, _court(cle[1], 70), 11.5, couleur="FFFFFF")
        k.texte(s, 8.3, 3.55, 4.4, 2.9, _court(R.lecture(r, an), 430), 12.5, couleur=TEXTE)

    # enseignements et conclusion
    if c["enseignements"]:
        k.intercalaire(num, "Enseignements", "Ce que les résultats disent pour la décision")
        s = k.contenu("Les enseignements")
        ens = c["enseignements"][:4]
        h = min(1.15, 4.9 / len(ens))
        for i, m in enumerate(ens):
            y = 1.45 + i * (h + 0.12)
            k.forme(s, 0.6, y, 0.12, h, BLEU, arrondi=0)
            k.texte(s, 0.95, y + 0.05, 11.7, h - 0.1, _court(m, 230), 14, couleur=TEXTE, ancre=MSO_ANCHOR.MIDDLE)
    if c["conclusion"]:
        s = k.contenu("En conclusion")
        k.forme(s, 0.6, 1.6, 12.1, 3.6, CLAIR)
        k.texte(s, 1.0, 1.9, 11.3, 3.1, _court(c["conclusion"], 600), 18, couleur=MARINE, ancre=MSO_ANCHOR.MIDDLE)

    # méthode
    s = k.contenu("Méthode et limites")
    k.texte(s, 0.6, 1.45, 5.9, 0.4, "Méthode", 18, True, MARINE)
    k.texte(s, 0.6, 1.95, 5.9, 4.4, [
        f"•  Enquête quantitative par questionnaire ; cible : {c['fiche']['cible']}.",
        f"•  {c['n']} répondants, échantillon par quotas (zone × profil).",
        f"•  Marge d'erreur indicative sur l'ensemble : {fmt_marge(c['n'])} (IC à 95 %).",
        "•  Aucun résultat publié pour un groupe de moins de 30 répondants.",
    ] + ([f"•  Collecte {c['collecte']}."] if c["collecte"] else []), 13, couleur=TEXTE, interligne=8)
    k.texte(s, 6.9, 1.45, 5.8, 0.4, "Limites", 18, True, MARINE)
    k.forme(s, 6.9, 1.95, 5.8, 4.4, JAUNE)
    k.texte(s, 7.15, 2.15, 5.3, 4.0, [f"•  {_court(l, 170)}" for l in c["limites"][:4]] or ["•  Voir la note méthodologique."],
            12, couleur=TEXTE, interligne=8)

    k.couverture("Merci", "Questions et échanges", f"DATATYM, marque d'AGILTYM  ·  {mois}")
    cp = k.prs.core_properties
    cp.author = cp.last_modified_by = auteur_fichiers()
    cp.title, cp.subject = c["titre"], "Restitution des résultats"
    k.prs.save(chemin)
    return chemin


# ------------------------------------------------------------------ note de synthèse
def note_synthese(chemin, projet, c=None):
    c = c or _contexte(projet)
    x = c["x"]
    blocs_ens = [liste(c["enseignements"][:4])] if c["enseignements"] else []
    modele = {
        "titre": c["fiche"]["theme"], "surtitre": "", "sous_titre": "Note de synthèse",
        "meta": [f"{c['n']} répondants · {len(c['zones'])} {'pays' if c['pays'] else 'zones'}", f"Version du {aujourdhui()}", "Auteur : DATATYM"],
        "en_tete": f"{c['titre']} — Note de synthèse", "pied": "Datatym",
        "sections": [
            section("bref", "L'essentiel", [
                chiffres([{"valeur": v, "libelle": _court(l, 80)} for v, l in c["chif"][:4]]),
                p(f"Résultats {du_barometre(c['fiche']['theme'])}, établis à partir de {c['n']} répondants"
                  + (f" (collecte {c['collecte']})" if c["collecte"] else "")
                  + f" dans {len(c['zones'])} {'pays' if c['pays'] else 'zones'} ({', '.join(c['zones'])})."),
            ]),
            section("messages", "Les messages clés", [liste(c["messages"][:5])]),
        ] + ([section("indice", "Indice H&C de Maturité IA", [p(c["R"].lecture_indice_hc(x))])] if x else []) + [
            section("enseignements", "Enseignements", blocs_ens or [p("Voir le rapport d'analyse.")]),
            section("conclusion", "Conclusion", [p(c["conclusion"] or "Voir le rapport d'analyse.")]),
            section("methode", "Méthode", [p(f"Enquête quantitative par questionnaire (cible : {c['fiche']['cible']}) ; échantillon par quotas ; "
                                           f"marge d'erreur indicative sur l'ensemble : {fmt_marge(c['n'])} (IC à 95 %). "
                                           "Le détail figure dans le rapport d'analyse et la note méthodologique.", "note")]),
        ],
    }
    rendre_modele(modele, chemin)
    return chemin


# ------------------------------------------------------------------ communiqué de presse
def communique(chemin, projet, c=None):
    c = c or _contexte(projet)
    params = charger_parametres()
    msgs = c["messages"]
    zones = ", ".join(c["zones"])
    modele = {
        "titre": _court(msgs[0], 140) if msgs else c["titre"], "surtitre": "", "sous_titre": "Communiqué de presse",
        "meta": [("Résultats provisoires : à diffuser une fois la collecte terminée" if c["provisoire"] else f"Pour diffusion à partir du {aujourdhui()}"),
                 "Auteur : DATATYM"],
        "en_tete": f"{c['titre']} — Communiqué de presse", "pied": "Datatym",
        "sections": [
            section("chapeau", "", [p(
                f"**Datatym publie les résultats {du_barometre(c['fiche']['theme'])}**, une enquête "
                + (f"menée {c['collecte']}" if c["collecte"] and not c["provisoire"] else f"{c['collecte']}" if c["collecte"] else "menée")
                + f" auprès de {c['n']} répondants ({c['fiche']['cible']}) dans {len(c['zones'])} {'pays' if c['pays'] else 'zones'} : {zones}.")]),
            section("resultats", "Les principaux résultats", [liste(msgs[1:5] if len(msgs) > 1 else msgs)]),
        ] + ([section("enjeux", "Ce que cela signifie", [p(c["enseignements"][0])])] if c["enseignements"] else []) + [
            section("citation", "Citation", [p("[Citation du porte-parole de Datatym à ajouter avant diffusion.]", "note")]),
            section("methode", "Méthodologie", [p(
                f"Enquête quantitative par questionnaire, échantillon par quotas de {c['n']} répondants ; marge d'erreur indicative "
                f"{fmt_marge(c['n'])} (intervalle de confiance à 95 %). Aucun résultat n'est publié pour un groupe de moins de 30 répondants.")]),
            section("apropos", "À propos de Datatym", [p(params.get("presentation_datatym", ""))]),
            section("contact", "Contact presse", [p("[Nom, téléphone et mail du contact presse à ajouter.]", "note")]),
        ],
    }
    rendre_modele(modele, chemin)
    return chemin


# ------------------------------------------------------------------ infographie
def infographie(chemin, projet, c=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    c = c or _contexte(projet)
    fig = plt.figure(figsize=(7.2, 9), dpi=150)
    fig.patch.set_facecolor("#081F5C")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 72)
    ax.set_ylim(0, 90)
    ax.axis("off")
    logo = STATIC_DIR / "logo_datatym_blanc.png"
    if logo.exists():
        im = plt.imread(str(logo))
        h = 4.2
        w = h * im.shape[1] / im.shape[0]
        ax.imshow(im, extent=(5, 5 + w, 82, 82 + h), zorder=3)
    ax.text(5, 77, c["titre"].upper(), color="#7FC4FF", fontsize=10, fontweight="bold")
    ax.text(5, 72, textwrap.fill(_court(c["messages"][0], 120) if c["messages"] else "Les résultats", 38), color="white",
            fontsize=15, fontweight="bold", va="top", linespacing=1.3)
    titre = c["messages"][0] if c["messages"] else ""
    # le premier chiffre est déjà dans le titre : on passe aux suivants
    cases = c["chif"][1:5] if c["chif"] and c["chif"][0][0].split("/")[0] in titre else c["chif"][:4]
    for i, (v, l) in enumerate(cases):
        x0, y0 = 5 + (i % 2) * 32, 41 - (i // 2) * 17
        ax.add_patch(FancyBboxPatch((x0, y0), 30, 15, boxstyle="round,pad=0,rounding_size=2.2", fc="#0F2E7A", ec="none"))
        ax.text(x0 + 2.5, y0 + 9.5, v, color="#E0B61F", fontsize=22, fontweight="bold")
        ax.text(x0 + 2.5, y0 + 6.2, textwrap.fill(_court(l, 70), 34), color="white", fontsize=7.6, va="top", linespacing=1.25)
    pied = f"{c['n']} répondants · {len(c['zones'])} {'pays' if c['pays'] else 'zones'}"
    if c["collecte"]:
        pied += " · résultats provisoires, collecte en cours" if c["provisoire"] else f" · collecte {c['collecte']}"
    ax.text(5, 9, pied, color="#C9D6EA", fontsize=7.5)
    ax.text(5, 5.5, "Datatym — Discerner. Décider. Disrupter.", color="#7FC4FF", fontsize=8, fontweight="bold")
    fig.savefig(chemin, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)
    return chemin


# ------------------------------------------------------------------ production
def generer(projet):
    """Produit les quatre supports dans livrables/ et les enregistre dans projet["restitution"]."""
    if not disponible(projet):
        raise ValueError("Générez d'abord le rapport d'analyse : la restitution en reprend les résultats.")
    c = _contexte(projet)
    out = dossier(projet["slug"]) / "livrables"
    out.mkdir(parents=True, exist_ok=True)
    v = projet["etapes"]["rapport"].get("version") or 1
    faire = {"Restitution_Resultats": pptx, "Note_Synthese": note_synthese, "Infographie": infographie, "Communique_Presse": communique}
    fichiers = []
    for ext, code, nom, desc in SUPPORTS:
        f = nom_fichier(projet, code, v, ext)
        faire[code](out / f, projet, c)
        fichiers.append({"nom": nom, "description": desc, "fichier": f, "type": ext})
    projet["restitution"] = {"date": maintenant(), "fichiers": fichiers, "rapport_version": v,
                             "rapport_maj": projet["etapes"]["rapport"].get("maj")}
    return projet["restitution"]
