"""Déroulement de l'étude, présenté au dirigeant dès la fiche d'entrée : calendrier, scénarios, options de taille,
points de vigilance et moments de décision. Tout est calculé à partir des sept paramètres de la fiche.
"""
import math
from datetime import date, timedelta

from . import budget
from .banque import decouper, nom_barometre, sont_des_pays
from .charte import chiffres, liste, p, rendre_modele, section, tableau
from .outils import MOIS, aujourdhui, date_fr, debut_collecte, fcfa, fmt_marge, jours_collecte, nombre

MOIS_COURTS = ["janv.", "févr.", "mars", "avril", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
PART_RESERVE = 15
DELAI_RH = 10       # jours laissés aux RH pour recruter
RETOUR_LISTE = 7    # la liste revient une semaine avant la collecte
NOMS = {"bas": ("Favorable", "Les répondants sont disponibles, peu de refus : le terrain avance vite."),
        "central": ("Probable", "Le rythme habituel d'un baromètre, avec quelques refus et rendez-vous reportés."),
        "haut": ("Difficile", "Refus fréquents chez les dirigeants, zones éloignées, rendez-vous à relancer.")}

# Jours fériés communs à l'Afrique de l'Ouest et du Centre ; fêtes musulmanes à un ou deux jours près
FIXES = {(1, 1): "Jour de l'an", (5, 1): "Fête du travail", (8, 15): "Assomption", (11, 1): "Toussaint", (12, 25): "Noël"}
MOBILES = [
    (date(2026, 2, 18), date(2026, 3, 19), "Ramadan"), (date(2026, 3, 20), date(2026, 3, 21), "Korité (Aïd el-Fitr)"),
    (date(2026, 5, 27), date(2026, 5, 28), "Tabaski (Aïd el-Kébir)"), (date(2026, 8, 25), date(2026, 8, 26), "Maouloud"),
    (date(2027, 2, 8), date(2027, 3, 9), "Ramadan"), (date(2027, 3, 10), date(2027, 3, 11), "Korité (Aïd el-Fitr)"),
    (date(2027, 5, 17), date(2027, 5, 18), "Tabaski (Aïd el-Kébir)"), (date(2027, 8, 15), date(2027, 8, 16), "Maouloud"),
    (date(2028, 1, 28), date(2028, 2, 26), "Ramadan"), (date(2028, 2, 27), date(2028, 2, 28), "Korité (Aïd el-Fitr)"),
    (date(2028, 5, 5), date(2028, 5, 6), "Tabaski (Aïd el-Kébir)"),
]


def fetes(debut, fin):
    """Fêtes et jours fériés qui tombent entre deux dates."""
    trouves = []
    d = debut
    while d <= fin:
        if (d.month, d.day) in FIXES:
            trouves.append(f"{FIXES[(d.month, d.day)]} ({date_fr(d)})")
        d += timedelta(days=1)
    for a, b, nom in MOBILES:
        if a <= fin and b >= debut:
            trouves.append(f"{nom} ({date_fr(a)}{f' au {date_fr(b)}' if b > a + timedelta(days=1) else ''}, date approximative)")
    return trouves


def ouvres(depart, n):
    """Date atteinte après n jours ouvrés (lundi à vendredi)."""
    d, k = depart, 0
    while k < n:
        d += timedelta(days=1)
        if d.weekday() < 5:
            k += 1
    return d


def presenter(projet):
    fiche = projet["fiche"]
    n = int(fiche.get("taille") or 0) or 1
    zones = decouper(fiche.get("zones", "")) or [""]
    Z = "pays" if sont_des_pays(zones) else "zones"
    debut = debut_collecte(fiche)
    jours = jours_collecte(debut, fiche.get("duree") or 1)
    fin = jours[-1]
    today = date.today()
    # point de départ : création de l'étude (une étude déjà lancée garde son calendrier réel)
    try:
        depart = min(date.fromisoformat(str(projet.get("cree", ""))[:10]), today)
    except ValueError:
        depart = today
    depart = min(depart, debut - timedelta(days=2))
    est = budget.estimer_cadrage(fiche)
    hyp_scen = {cle: {**budget.HYPOTHESES_DEFAUT, **h} for cle, _, _, h, _ in budget.SCENARIOS}

    # ---------------- calendrier
    retour_rh = debut - timedelta(days=RETOUR_LISTE)
    if retour_rh < today:  # préparation déjà passée (étude importée en cours de route) : calendrier théorique
        depart = min(depart, retour_rh - timedelta(days=DELAI_RH + 7))
    envoi_rh = min(max(depart, retour_rh - timedelta(days=DELAI_RH)), retour_rh)
    rapport = ouvres(fin, int(hyp_scen["central"]["jours_analyse"]))
    phases = [
        ("Cadrage et questionnaire", depart, envoi_rh, "Note de cadrage, indicateurs, questionnaire validés"),
        ("Recrutement par les RH", envoi_rh, retour_rh, "Annonce publiée, candidats sélectionnés, liste des enquêteurs retournée"),
        ("Préparation du terrain", retour_rh, debut - timedelta(days=2), "Contrats, formulaire de collecte, quotas par enquêteur"),
        ("Formation (Teams)", debut - timedelta(days=1), debut - timedelta(days=1), "Titulaires et réserves, prise en main de l'outil"),
        ("Collecte", debut, fin, f"{len(jours)} jours de terrain, suivi quotidien à distance"),
        ("Analyse et rapport", fin + timedelta(days=1), rapport, "Contrôle des données, indicateurs, rapport d'analyse"),
        ("Restitution et clôture", rapport, ouvres(rapport, 3), "Présentation des résultats, archivage de l'étude"),
    ]

    periodes = decouper_periodes(phases[0][1], phases[-1][2])

    # ---------------- scénarios de déroulement
    scenarios = []
    for s in est["scenarios"]:
        nom, texte = NOMS[s["cle"]]
        h = hyp_scen[s["cle"]]
        scenarios.append({
            "cle": s["cle"], "nom": nom, "contexte": texte, "hypothese": s["hypothese"],
            "rendement": next(r for c, _, r, _, _ in budget.SCENARIOS if c == s["cle"]),
            "enqueteurs": s["nb_enqueteurs"], "reserves": math.ceil(s["nb_enqueteurs"] * PART_RESERVE / 100),
            "total": s["total"], "par_questionnaire": s["par_questionnaire"],
            "rapport": ouvres(fin, int(h["jours_analyse"])).isoformat(),
        })

    # ---------------- et si : taille de l'échantillon
    tailles = sorted({max(50, int(round(n * k / 50.0)) * 50) for k in (2 / 3, 1, 4 / 3)} | {n})
    options = []
    for t in tailles:
        e = budget.estimer_cadrage({**fiche, "taille": t})
        sc = next(x for x in e["scenarios"] if x["cle"] == "central")
        options.append({"taille": t, "retenue": t == n, "total": e["central"], "enqueteurs": sc["nb_enqueteurs"],
                        "marge": fmt_marge(t), "marge_zone": fmt_marge(t // max(len(zones), 1)),
                        "par_zone": t // max(len(zones), 1)})

    # ---------------- points de vigilance
    vigilance = []
    par_zone = n // max(len(zones), 1)
    if len(zones) > 1 and par_zone < 30:
        vigilance.append(f"Environ {par_zone} répondants par {Z[:-1] if Z == 'zones' else 'pays'} : les résultats ne seront lisibles qu'au niveau global. "
                         f"Il faut au moins {30 * len(zones)} répondants pour une lecture par {Z[:-1] if Z == 'zones' else 'pays'}.")
    elif len(zones) > 1 and par_zone < 100:
        vigilance.append(f"Environ {par_zone} répondants par {'pays' if Z == 'pays' else 'zone'} : marge d'erreur de {fmt_marge(par_zone)} par "
                         f"{'pays' if Z == 'pays' else 'zone'}, à présenter comme des tendances.")
    plafond = fiche.get("cout")
    if plafond and est["haut"] > plafond:
        vigilance.append(f"Plafond de {fcfa(plafond)} : " + ("dépassé dès le scénario favorable ; réduire la taille de l'échantillon ou le nombre de pays."
                         if est["bas"] > plafond else "tenu dans le scénario favorable, mais dépassé si le terrain est difficile."))
    if retour_rh >= today and (retour_rh - envoi_rh).days < 7:
        vigilance.append(f"Recrutement serré : les RH disposent de {max((retour_rh - envoi_rh).days, 0)} jours. Avancer la note de cadrage ou décaler la collecte.")
    if envoi_rh >= today and (envoi_rh - depart).days < 5:
        vigilance.append("Cadrage et questionnaire à boucler en moins d'une semaine : prévoir une validation rapide de la note de cadrage.")
    f = fetes(debut - timedelta(days=1), fin)
    if f:
        vigilance.append("Pendant la collecte : " + " ; ".join(f) + ". Prévoir un rythme réduit ces jours-là.")
    if not vigilance:
        vigilance.append("Aucun point bloquant : effectifs, budget et calendrier sont cohérents.")

    # ---------------- moments de décision du dirigeant
    decisions = [
        (envoi_rh, "Valider la note de cadrage", "Indicateurs, cible et fourchette de coût"),
        (retour_rh, "Valider le budget et l'équipe", "Budget de collecte, liste des enquêteurs retenus"),
        (jours[len(jours) // 2], "Point à mi-collecte", "Avancement, quotas en retard, éventuelle réallocation"),
        (rapport, "Recevoir le rapport", "Résultats, messages clés, restitution"),
    ]
    return {
        "titre": nom_barometre(fiche.get("theme", "")), "n": n, "zones": zones, "Z": Z, "jours": len(jours),
        "debut": debut.isoformat(), "fin": fin.isoformat(), "rapport": rapport.isoformat(),
        "phases": [{"nom": a, "debut": b.isoformat(), "fin": c.isoformat(), "detail": d, "cols": _colonnes(b, c, periodes)}
                   for a, b, c, d in phases],
        "unite": "semaine" if (periodes[0][1] - periodes[0][0]).days == 6 else "mois",
        "periodes": [{"debut": a.isoformat(), "fin": b.isoformat(), "libelle": l, "courante": a <= today <= b} for a, b, l in periodes],
        "scenarios": scenarios, "options": options, "vigilance": vigilance, "plafond": plafond,
        "decisions": [{"date": d.isoformat(), "titre": t, "detail": x} for d, t, x in decisions],
    }


def decouper_periodes(t0, t1):
    """Colonnes du diagramme : semaines (du lundi au dimanche), ou mois si l'étude dure plus de 16 semaines."""
    lundi = t0 - timedelta(days=t0.weekday())
    if (t1 - lundi).days < 16 * 7:
        sem, d = [], lundi
        while d <= t1:
            sem.append((d, d + timedelta(days=6), f"{d.day} {MOIS_COURTS[d.month - 1]}"))
            d += timedelta(days=7)
        return sem
    mois, m = [], date(t0.year, t0.month, 1)
    while m <= t1:
        suivant = date(m.year + (m.month == 12), m.month % 12 + 1, 1)
        mois.append((m, suivant - timedelta(days=1), f"{MOIS_COURTS[m.month - 1]} {str(m.year)[2:]}"))
        m = suivant
    return mois


def _colonnes(a, b, periodes):
    """Première et dernière colonne couvertes par une étape."""
    i = [k for k, (x, y, _) in enumerate(periodes) if x <= b and y >= a]
    return [i[0], i[-1]] if i else [0, 0]


def _periode(a, b):
    a, b = date.fromisoformat(a), date.fromisoformat(b)
    if a == b:
        return date_fr(a)
    if a.year == b.year and a.month == b.month:
        return f"du {a.day} au {date_fr(b)}"
    return f"du {date_fr(a)} au {date_fr(b)}"


# ------------------------------------------------------------------ Word
def docx(chemin, projet, d=None):
    d = d or presenter(projet)
    fiche = projet["fiche"]
    prob = next(s for s in d["scenarios"] if s["cle"] == "central")
    modele = {
        "titre": "Déroulement de l'étude", "surtitre": "Note au dirigeant", "sous_titre": fiche["theme"],
        "meta": [f"{d['n']} répondants · {len(d['zones'])} {d['Z']} · {d['jours']} jours de collecte", f"Version du {aujourdhui()}"],
        "en_tete": f"{d['titre']} — Déroulement de l'étude",
        "sections": [
            section("synthese", "1. L'essentiel", [
                chiffres([{"valeur": date_fr(d["debut"]), "libelle": "début de la collecte"},
                          {"valeur": date_fr(prob["rapport"]), "libelle": "remise du rapport (scénario probable)"},
                          {"valeur": fcfa(prob["total"]), "libelle": "coût probable"},
                          {"valeur": str(prob["enqueteurs"]), "libelle": f"enquêteurs (+ {prob['reserves']} en réserve)"}]),
                p(f"L'étude interroge {d['n']} répondants dans {len(d['zones'])} {d['Z']} ({', '.join(d['zones'])}). "
                  "La formation des enquêteurs se fait en ligne et le terrain est suivi à distance par Datatym."),
            ], source="auto"),
            section("calendrier", "2. Calendrier", [
                tableau(["Étape", *[x["libelle"] for x in d["periodes"]]],
                        [[x["nom"], *[("{{fond:" + ("E0B61F" if "Formation" in x["nom"] else "0087E0" if i % 2 == 0 else "19243E") + "}}")
                                      if x["cols"][0] <= j <= x["cols"][1] else "" for j in range(len(d["periodes"]))]]
                         for i, x in enumerate(d["phases"])],
                        "Calendrier par " + ("semaine (date du lundi)" if d["unite"] == "semaine" else "mois"),
                        [2.4] + [1] * len(d["periodes"]), 8),
                tableau(["Période", "Étape", "Contenu"], [[_periode(x["debut"], x["fin"]), x["nom"], x["detail"]] for x in d["phases"]],
                        "Calendrier de l'étude", [1.6, 1.5, 3.1], 9.5)], source="auto"),
            section("scenarios", "3. Trois scénarios de déroulement", [
                tableau(["", *[s["nom"] for s in d["scenarios"]]], [
                    ["Situation", *[s["contexte"] for s in d["scenarios"]]],
                    ["Rythme du terrain", *[f"{s['rendement']} questionnaires par enquêteur et par jour" for s in d["scenarios"]]],
                    ["Équipe", *[f"{s['enqueteurs']} enquêteurs + {s['reserves']} réserves" for s in d["scenarios"]]],
                    ["Coût total", *[f"**{fcfa(s['total'])}**" for s in d["scenarios"]]],
                    ["Par questionnaire", *[fcfa(s["par_questionnaire"]) for s in d["scenarios"]]],
                    ["Remise du rapport", *[date_fr(s["rapport"]) for s in d["scenarios"]]],
                ], "Scénarios", [1.3, 1.65, 1.65, 1.65], 9),
                p("La date de fin de collecte est la même dans les trois cas : c'est la taille de l'équipe qui s'adapte au rythme du terrain.", "note"),
            ], source="auto"),
            section("options", "4. Et si l'on changeait la taille de l'échantillon ?", [
                tableau(["Répondants", "Coût probable", "Enquêteurs", "Marge d'erreur globale", f"Marge par {'pays' if d['Z'] == 'pays' else 'zone'}"],
                        [[f"**{o['taille']}** (retenu)" if o["retenue"] else str(o["taille"]), fcfa(o["total"]), str(o["enqueteurs"]), o["marge"],
                          f"{o['marge_zone']} ({o['par_zone']} répondants)"] for o in d["options"]], "Taille, coût et précision", taille=9.5),
            ], source="auto"),
            section("vigilance", "5. Points de vigilance", [liste(d["vigilance"])], source="auto"),
            section("decisions", "6. Vos rendez-vous de décision", [
                tableau(["Date", "Décision", "Ce qui est présenté"], [[date_fr(x["date"]), x["titre"], x["detail"]] for x in d["decisions"]],
                        "Moments de décision", [1.3, 1.7, 3.2])], source="auto"),
        ],
    }
    rendre_modele(modele, chemin)
    return chemin


# ------------------------------------------------------------------ PowerPoint
def pptx(chemin, projet, d=None):
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN

    from .formation import BLEU, BLEU_PALE, CLAIR, GRIS, JAUNE, MARINE, OR, TEXTE, Deck

    d = d or presenter(projet)
    fiche = projet["fiche"]
    k = Deck(f"{d['titre']} · Déroulement de l'étude")
    prob = next(s for s in d["scenarios"] if s["cle"] == "central")
    k.couverture(d["titre"], "Déroulement de l'étude · Note au dirigeant",
                 f"DATATYM, marque d'AGILTYM  ·  {MOIS[date.today().month - 1].capitalize()} {date.today().year}")

    # L'essentiel
    s = k.contenu("L'étude en un coup d'œil")
    k.soustitre(s, fiche.get("objectif") or "")
    for i, (v, l) in enumerate([(date_fr(d["debut"]), "début de la collecte"), (date_fr(prob["rapport"]), "remise du rapport"),
                                (fcfa(prob["total"]).replace(" FCFA", ""), "FCFA, coût probable"),
                                (f"{prob['enqueteurs']} + {prob['reserves']}", "enquêteurs + réserves")]):
        x = 0.6 + i * 3.08
        k.forme(s, x, 2.0, 2.8, 2.1, MARINE)
        k.texte(s, x + 0.2, 2.25, 2.4, 1.0, v, 26 if i < 2 else 32, True, OR)
        k.texte(s, x + 0.2, 3.3, 2.4, 0.7, l, 14, couleur="FFFFFF")
    k.forme(s, 0.6, 4.5, 12.1, 1.8, JAUNE)
    k.texte(s, 0.9, 4.7, 11.5, 1.5, [[(f"{d['n']} répondants", {"gras": True}), (f" dans {len(d['zones'])} {d['Z']} : {', '.join(d['zones'])}.", {})],
                                     "Formation des enquêteurs en ligne (Teams), terrain suivi à distance par Datatym."], 15, couleur=TEXTE, interligne=6)

    # Calendrier : une colonne par période (semaine ou mois), une ligne par étape
    s = k.contenu("Calendrier de l'étude")
    per = d["periodes"]
    x0, w, y0, hl = 3.7, 9.0, 1.85, 0.6
    cw = w / len(per)
    taille = 11 if len(per) <= 10 else 9 if len(per) <= 14 else 8
    for j, pe in enumerate(per):
        x = x0 + j * cw
        k.forme(s, x + 0.02, 1.35, cw - 0.04, 0.38, OR if pe["courante"] else MARINE, arrondi=0.15)
        k.texte(s, x, 1.35, cw, 0.38, pe["libelle"], taille, True, MARINE if pe["courante"] else "FFFFFF", PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
        if j % 2 == 0:
            k.forme(s, x, 1.78, cw, hl * len(d["phases"]) + 0.05, CLAIR, arrondi=0)
    couleurs = [BLEU, MARINE, BLEU, OR, MARINE, BLEU, MARINE]
    for i, ph in enumerate(d["phases"]):
        y = y0 + i * hl
        k.texte(s, 0.6, y + 0.0, 3.0, 0.3, ph["nom"], 13, True, MARINE)
        k.texte(s, 0.6, y + 0.28, 3.0, 0.25, _periode(ph["debut"], ph["fin"]), 9.5, couleur=GRIS)
        c0, c1 = ph["cols"]
        k.forme(s, x0 + c0 * cw + 0.05, y + 0.1, (c1 - c0 + 1) * cw - 0.1, 0.34, couleurs[i % len(couleurs)], arrondi=0.3)
    k.texte(s, 0.6, 6.3, 12.1, 0.4, f"Remise du rapport prévue le {date_fr(prob['rapport'])} (scénario probable)."
            + ("  ·  En jaune : la période en cours." if any(p_["courante"] for p_ in per) else ""), 13, True, BLEU)

    # Scénarios
    s = k.contenu("Trois scénarios de déroulement")
    k.soustitre(s, "La fin de la collecte ne bouge pas : c'est la taille de l'équipe qui s'adapte au rythme du terrain.")
    for i, sc in enumerate(d["scenarios"]):
        x = 0.6 + i * 4.1
        fond, ct = (MARINE, "FFFFFF") if sc["cle"] == "central" else (CLAIR, MARINE)
        k.forme(s, x, 1.75, 3.85, 4.75, fond)
        k.texte(s, x + 0.3, 1.95, 3.3, 0.45, sc["nom"], 22, True, OR if sc["cle"] == "central" else BLEU)
        k.texte(s, x + 0.3, 2.5, 3.3, 0.9, sc["contexte"], 12, couleur=ct, italique=True)
        k.texte(s, x + 0.3, 3.45, 3.3, 0.6, fcfa(sc["total"]), 24, True, ct)
        k.texte(s, x + 0.3, 4.15, 3.3, 2.2, [f"•  {sc['rendement']} questionnaires / enquêteur / jour",
                                             f"•  {sc['enqueteurs']} enquêteurs + {sc['reserves']} réserves",
                                             f"•  {fcfa(sc['par_questionnaire'])} par questionnaire",
                                             f"•  Rapport le {date_fr(sc['rapport'])}"], 12.5, couleur=ct, interligne=5)

    # Et si
    s = k.contenu("Et si l'on changeait la taille de l'échantillon ?")
    k.soustitre(s, "Plus de répondants : un coût plus élevé, mais des résultats plus précis, notamment par " + ("pays." if d["Z"] == "pays" else "zone."))
    k.tableau(s, 0.6, 1.9, 12.1, ["Répondants", "Coût probable", "Enquêteurs", "Marge d'erreur globale", f"Marge par {'pays' if d['Z'] == 'pays' else 'zone'}"],
              [[f"{o['taille']}  (retenu)" if o["retenue"] else str(o["taille"]), fcfa(o["total"]), str(o["enqueteurs"]), o["marge"],
                f"{o['marge_zone']}  ({o['par_zone']} rép.)"] for o in d["options"]], [1.4, 1.8, 1.1, 1.8, 2.2], 15)
    k.texte(s, 0.6, 5.6, 12.1, 0.8, "Marge d'erreur à 95 % : un résultat de 50 % avec une marge de ± 4 points se situe entre 46 % et 54 %. "
            "En dessous de 30 répondants, un résultat n'est pas interprétable.", 12, couleur=GRIS, italique=True)

    # Vigilance et décisions
    s = k.contenu("Points de vigilance et rendez-vous de décision")
    k.texte(s, 0.6, 1.4, 5.8, 0.4, "Points de vigilance", 18, True, MARINE)
    lignes = sum(math.ceil(len(v) / 62) for v in d["vigilance"]) + len(d["vigilance"]) * 0.4
    k.forme(s, 0.6, 1.9, 5.8, min(4.6, 0.5 + 0.3 * lignes), JAUNE)
    k.texte(s, 0.85, 2.1, 5.3, 4.3, [f"•  {v}" for v in d["vigilance"]], 12.5 if len(" ".join(d["vigilance"])) < 600 else 11, couleur=TEXTE, interligne=8)
    k.texte(s, 6.8, 1.4, 5.9, 0.4, "Vos rendez-vous de décision", 18, True, MARINE)
    for i, x in enumerate(d["decisions"]):
        y = 1.95 + i * 1.15
        k.forme(s, 6.8, y, 1.55, 0.95, MARINE)
        dd = date.fromisoformat(x["date"])
        k.texte(s, 6.8, y + 0.08, 1.55, 0.85, [str(dd.day), MOIS_COURTS[dd.month - 1]], 18, True, OR, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
        k.texte(s, 8.55, y + 0.05, 4.2, 0.4, x["titre"], 15, True, MARINE)
        k.texte(s, 8.55, y + 0.45, 4.2, 0.5, x["detail"], 12, couleur=GRIS)
    k.prs.save(chemin)
    return chemin
