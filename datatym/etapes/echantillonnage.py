"""Étape 3 — Plan d'échantillonnage, répartition par enquêteur, calendrier, coûts et note de recrutement."""
import math
from datetime import date, timedelta

from .. import budget, equipe
from ..banque import decouper, du_barometre, nom_barometre, slug, sont_des_pays
from ..charte import liste, p, section, tableau, chiffres
from ..config import charger_parametres
from ..outils import aujourdhui, date_courte, date_fr, debut_collecte, fcfa, fmt_marge, jours_collecte, nombre, pct, repartir

DOCS = {
    "note_echantillonnage": ("NoteEchantillonnage", "Note d'échantillonnage des enquêteurs"),
    "note_recrutement": ("NoteRecrutement", "Note de recrutement des enquêteurs"),
    "budget_collecte": ("BudgetCollecte", "Budget de collecte"),
}


def params_defaut(projet, quest):
    fiche = projet["fiche"]
    zones = decouper(fiche["zones"])
    return {
        "rendement": 6, "marge": 0.9, "sans_dimanche": True,
        "date_debut": debut_collecte(fiche).isoformat(),
        "poids_zones": {z: 1 for z in zones},
        "poids_profils": {pr["code"]: 1 for pr in quest["profils"]},
        "noms_enqueteurs": [], "nb_enqueteurs_force": None,
        "couts": budget.couts_reference(), "hypotheses": dict(budget.HYPOTHESES_DEFAUT),
    }


def formation_texte(hyp):
    """Modalité de formation telle qu'annoncée dans les documents."""
    return "en ligne sur Microsoft Teams" if (hyp or {}).get("formation", "en_ligne") == "en_ligne" else "en présentiel dans chaque pays"


def recrutement_defaut(projet, n_enq, jours, n_res=0, hyp=None):
    fiche = projet["fiche"]
    params = charger_parametres()
    return {
        "intitule": f"Recrutement des enquêteurs — {nom_barometre(fiche['theme'])}",
        "mission": (f"Dans le cadre {du_barometre(fiche['theme'])}, Datatym demande au service des ressources humaines de recruter "
                    f"{n_enq} enquêteurs et enquêtrices{f', ainsi que {n_res} en réserve,' if n_res else ''} chargés d'administrer un questionnaire auprès de {fiche['cible']}, dans "
                    f"{'les pays suivants' if sont_des_pays(fiche['zones']) else 'les zones suivantes'} : {', '.join(decouper(fiche['zones']))}. "
                    f"La collecte se déroule sur {len(jours)} jours, du {date_fr(jours[0])} au {date_fr(jours[-1])}, "
                    f"précédée d'une formation obligatoire {formation_texte(hyp)}."),
        "taches": [
            "Identifier et contacter les répondants éligibles selon les quotas attribués.",
            "Présenter l'étude, recueillir le consentement et administrer le questionnaire sur smartphone ou tablette.",
            "Saisir les réponses avec rigueur et envoyer les formulaires chaque jour.",
            "Respecter le calendrier, les quotas et les consignes de l'équipe de supervision.",
            "Signaler sans délai toute difficulté rencontrée sur le terrain.",
        ],
        "experience": "1 an", "diplome": "Bac+3",
        "competences": [
            "Expérience d'enquête quantitative, idéalement auprès d'entreprises ou de professionnels.",
            "Maîtrise d'un outil de collecte mobile (KoboCollect, ODK, QuestionPro ou équivalent).",
            "Aisance relationnelle, sens de l'écoute et présentation soignée.",
            "Rigueur, ponctualité et respect de la confidentialité.",
            "Bonne capacité de communication.",
            "Parler et lire couramment le français ; la pratique d'une langue locale est un atout.",
        ],
        "date_limite": (jours[0] - timedelta(days=7)).isoformat(),
        "retour": params.get("mail_rh", ""),
    }


# champs tirés de la fiche et du plan (thème, cible, zones, dates, nombre d'enquêteurs)
CHAMPS_CALCULES = ("intitule", "mission", "date_limite")


def actualiser_recrutement(prec, defaut):
    """Un champ resté à sa valeur par défaut suit la fiche ; un champ retouché à la main est conservé."""
    if not prec:
        return {**defaut, "_defaut": dict(defaut)}
    ancien_defaut = prec.get("_defaut")
    rec = {}
    for k, v in defaut.items():
        if k not in prec:
            rec[k] = v
        elif ancien_defaut is None:
            # note créée avant ce suivi : les champs calculés sont repris de la fiche, les autres conservés
            rec[k] = v if k in CHAMPS_CALCULES else prec[k]
        else:
            rec[k] = v if prec[k] == ancien_defaut.get(k) else prec[k]
    rec["_defaut"] = dict(defaut)
    return rec


def calculer(projet, quest, params, recrutement=None):
    fiche = projet["fiche"]
    n = fiche["taille"]
    zones = [z for z in params["poids_zones"]] or decouper(fiche["zones"])
    profils = quest["profils"]
    debut = date.fromisoformat(params["date_debut"])
    jours = jours_collecte(debut, fiche["duree"], params.get("sans_dimanche", True))
    rend = max(float(params.get("rendement") or 6), 1)
    marge = min(max(float(params.get("marge") or 0.9), 0.3), 1)
    n_enq = params.get("nb_enqueteurs_force") or math.ceil(n / (rend * len(jours) * marge))
    n_enq = max(int(n_enq), len(zones))

    # Quotas zone × profil
    pz = [params["poids_zones"].get(z, 1) for z in zones]
    pp = [params["poids_profils"].get(pr["code"], 1) for pr in profils]
    cellules = repartir(n, [a * b for a in pz for b in pp])
    quotas = {}
    for i, z in enumerate(zones):
        for j, pr in enumerate(profils):
            quotas[(z, pr["code"])] = cellules[i * len(profils) + j]
    tot_zone = {z: sum(quotas[(z, pr["code"])] for pr in profils) for z in zones}

    # Besoin par zone (au moins un enquêteur par zone) : c'est ce qui est demandé aux RH
    besoin = dict(zip(zones, [k + 1 for k in repartir(n_enq - len(zones), [tot_zone[z] for z in zones])]))
    # Réserves : formées avec l'équipe, mobilisées seulement pour remplacer un abandon (payées au questionnaire validé)
    part_res = max(float(params.setdefault("part_reserve", 15) or 0), 0)
    n_res = math.ceil(n_enq * part_res / 100) if part_res else 0
    reserve = dict(zip(zones, repartir(n_res, [besoin[z] for z in zones]) if n_res else [0] * len(zones)))
    # Équipe : liste des RH (chaque enquêteur dans son pays), sinon ancienne liste de noms, sinon Enq1, Enq2…
    tout_rh = [m for m in params.get("equipe") or [] if m.get("pays") in besoin]
    liste_rh = [m for m in tout_rh if m.get("role") != "reserve"]
    noms = [x for x in params.get("noms_enqueteurs", []) if str(x).strip()]
    if liste_rh:
        # rangée pays par pays, dans l'ordre des identifiants attribués ci-dessous
        params["equipe"] = tout_rh = sorted(tout_rh, key=lambda m: (zones.index(m["pays"]), m.get("role") == "reserve"))
        liste_rh = [m for m in tout_rh if m.get("role") != "reserve"]
        par_zone = {z: [m for m in liste_rh if m["pays"] == z] for z in zones}
    else:
        if noms:
            n_enq = max(len(noms), len(zones))
        nb = dict(zip(zones, [k + 1 for k in repartir(n_enq - len(zones), [tot_zone[z] for z in zones])])) if noms else besoin
        it = iter(noms)
        par_zone = {z: [{"nom_complet": next(it, None)} for _ in range(nb[z])] for z in zones}
    enqueteurs, reserves, k = [], [], 0
    code_zone = equipe.codes_zones(zones)
    for z in zones:
        membres = []
        # pays sans enquêteur dans la liste des RH : un poste reste à pourvoir pour ne pas perdre ses quotas
        for r, e in enumerate(par_zone[z] or [{}], 1):
            k += 1
            # liste des RH : identifiant ENQ + code pays + rang dans le pays (ENQML01) ; sinon enq1, enq2…
            code = equipe.identifiant(code_zone[z], r) if liste_rh else f"enq{k}"
            if e.get("prenom") or e.get("nom"):
                nom = f"{e.get('prenom', '')} {e.get('nom', '')}".strip()
            else:
                nom = e.get("nom_complet") or (f"Enq{k}" if not liste_rh else f"{code} (à pourvoir)")
            m = {"code": code, "nom": nom, "zone": z, "par_profil": {}, "objectif": 0}
            if e.get("telephone") or e.get("mail"):
                m["contact"] = {c: e.get(c, "") for c in ("nom", "prenom", "ville", "telephone", "mail")}
            membres.append(m)
        nb = len(membres)
        for j, pr in enumerate(profils):
            parts = repartir(quotas[(z, pr["code"])], [1] * nb)
            parts = parts[j % nb:] + parts[:j % nb]  # rotation pour équilibrer
            for m, q in zip(membres, parts):
                m["par_profil"][pr["code"]] = q
        for m in membres:
            m["objectif"] = sum(m["par_profil"].values())
            # séquence de profils entrelacés, découpée par jour
            seq, restants = [], dict(m["par_profil"])
            while any(restants.values()):
                for c in list(restants):
                    if restants[c] > 0:
                        seq.append(c)
                        restants[c] -= 1
            par_jour = repartir(m["objectif"], [1] * len(jours))
            m["par_jour"], pos = [], 0
            for nj in par_jour:
                bloc = seq[pos:pos + nj]
                pos += nj
                m["par_jour"].append({c: bloc.count(c) for c in m["par_profil"]})
        enqueteurs += membres
        # réserves du pays : identifiants à la suite des titulaires (ENQML03…), sans quotas tant qu'elles ne remplacent personne
        for r, e in enumerate([m for m in tout_rh if m["pays"] == z and m.get("role") == "reserve"], nb + 1):
            reserves.append({"code": equipe.identifiant(code_zone[z], r), "nom": f"{e.get('prenom', '')} {e.get('nom', '')}".strip(),
                             "zone": z, "contact": {c: e.get(c, "") for c in ("nom", "prenom", "ville", "telephone", "mail")}})
    n_enq = len(enqueteurs)

    calendrier = []
    cumul = 0
    for d_i, d in enumerate(jours):
        ligne = {"date": d.isoformat(), "zones": {}, "profils": {}, "total": 0}
        for m in enqueteurs:
            for c, v in m["par_jour"][d_i].items():
                ligne["zones"][m["zone"]] = ligne["zones"].get(m["zone"], 0) + v
                ligne["profils"][c] = ligne["profils"].get(c, 0) + v
                ligne["total"] += v
        cumul += ligne["total"]
        ligne["cumul"] = cumul
        calendrier.append(ligne)

    # budget construit à partir du plan ; une étude ancienne reçoit la grille de référence
    params["couts"], params["hypotheses"] = budget.completer(params.get("couts"), params.get("hypotheses"))
    params.pop("postes", None)
    bud = budget.calculer(n, n_enq, len(jours), len(zones), params["couts"], params["hypotheses"], len(reserves) or n_res)
    bud["marginal_100"] = budget.marginal(n, n_enq, len(jours), len(zones), params["couts"], params["hypotheses"])

    rec = actualiser_recrutement(recrutement, recrutement_defaut(projet, sum(besoin.values()), jours, n_res, params["hypotheses"]))
    return {"params": params, "zones": zones, "profils": profils, "jours": [d.isoformat() for d in jours],
            "nb_enqueteurs": n_enq, "besoin": besoin, "reserve": reserve, "reserves": reserves, "equipe_rh": bool(liste_rh), "quotas": [[z, c, v] for (z, c), v in quotas.items()], "tot_zone": tot_zone,
            "enqueteurs": enqueteurs, "calendrier": calendrier, "budget": bud, "recrutement": rec}


def generer(projet, quest, precedent=None):
    prec = precedent or {}
    params = prec.get("params") or params_defaut(projet, quest)
    # profils et zones peuvent avoir changé en amont
    params["poids_profils"] = {pr["code"]: params.get("poids_profils", {}).get(pr["code"], 1) for pr in quest["profils"]}
    zones = decouper(projet["fiche"]["zones"])
    params["poids_zones"] = {z: params.get("poids_zones", {}).get(z, 1) for z in zones}
    return calculer(projet, quest, params, prec.get("recrutement"))


def normaliser(projet, quest, data):
    return calculer(projet, quest, data["params"], data.get("recrutement"))


def construire_docs(projet, data, quest):
    fiche = projet["fiche"]
    lib = {pr["code"]: pr["libelle"] for pr in data["profils"]}
    codes = [pr["code"] for pr in data["profils"]]
    jours = [date.fromisoformat(j) for j in data["jours"]]
    n = fiche["taille"]
    q = {(z, c): v for z, c, v in data["quotas"]}
    Z = "Pays" if sont_des_pays(data["zones"]) else "Zone"

    lignes_quotas = [[z] + [str(q[(z, c)]) for c in codes] + [str(data["tot_zone"][z])] for z in data["zones"]]
    lignes_quotas.append(["**Total**"] + [f"**{sum(q[(z, c)] for z in data['zones'])}**" for c in codes] + [f"**{n}**"])
    lignes_enq = [[m["code"], m["nom"], m["zone"]] + [str(m["par_profil"][c]) for c in codes] + [str(m["objectif"]), nombre(m["objectif"] / len(jours), 1)]
                  for m in data["enqueteurs"]]
    # au-delà de 6 pays, les colonnes par pays ne tiennent plus sur la page : le détail reste dans l'Excel
    zones_cal = data["zones"] if len(data["zones"]) <= 6 else []
    cal = [[date_courte(l["date"])] + [str(l["zones"].get(z, 0)) for z in zones_cal] + [str(l["profils"].get(c, 0)) for c in codes]
           + [str(l["total"]), str(l["cumul"])] for l in data["calendrier"]]

    sections = [
        section("synthese", "1. Synthèse du plan d'échantillonnage", [
            chiffres([{"valeur": str(n), "libelle": "questionnaires visés"}, {"valeur": str(data["nb_enqueteurs"]), "libelle": "enquêteurs"},
                      {"valeur": str(len(jours)), "libelle": "jours de collecte"}, {"valeur": nombre(n / len(jours), 0), "libelle": "questionnaires par jour"}]),
            p(f"La méthode retenue est un **échantillonnage non probabiliste par quotas**, croisant la zone d'enquête et le profil du répondant. "
              f"Le nombre d'enquêteurs est calculé pour une productivité de {nombre(data['params']['rendement'], 0)} questionnaires par enquêteur et par jour, "
              f"avec une marge de sécurité de {int(round((1 - float(data['params']['marge'])) * 100))} % pour absorber les refus et les rendez-vous manqués."),
            p(f"La collecte se déroule du {date_fr(jours[0], True)} au {date_fr(jours[-1], True)}"
              + (", hors dimanches" if data["params"].get("sans_dimanche", True) else "") + "."),
        ], source="auto"),
        section("quotas", "2. Quotas par zone et par profil", [
            tableau([Z] + [lib[c] for c in codes] + ["Total"], lignes_quotas, f"Quotas {Z.lower()} × profil"),
            tableau(["Niveau de lecture", "Effectif", "Marge d'erreur (IC 95 %)"],
                    [["Global", str(n), fmt_marge(n)]] + [[f"{Z} : {z}", str(t), fmt_marge(t)] for z, t in data["tot_zone"].items()]
                    + [[f"Profil : {lib[c]}", str(sum(q[(z, c)] for z in data['zones'])), fmt_marge(sum(q[(z, c)] for z in data['zones']))] for c in codes],
                    "Précision attendue"),
        ], source="auto"),
        section("repartition", "3. Répartition par enquêteur", [
            p(("Les enquêteurs sont ceux de la liste transmise par les ressources humaines, affectés à leur pays de résidence. "
               if data.get("equipe_rh") else "Les enquêteurs sont désignés Enq1, Enq2… tant que la liste des ressources humaines n'est pas chargée. ")
              + "Chaque enquêteur reçoit un objectif par profil."),
            tableau(["ID", "Enquêteur", Z] + [lib[c] for c in codes] + ["Objectif", "Par jour"], lignes_enq, "Objectifs par enquêteur"),
        ] + ([p("Réserves, formées avec l'équipe et mobilisées pour remplacer un abandon (elles reprennent alors les quotas restants) : "
                + ", ".join(f"{r['code']} {r['nom']} ({r['zone']})" for r in data["reserves"]) + ".")] if data.get("reserves") else []), source="auto"),
        section("calendrier", "4. Calendrier de collecte", [
            p("Objectifs quotidiens par " + ("zone et par profil" if zones_cal else "profil") + ". Le détail par "
              + ("" if zones_cal else "pays, ") + "enquêteur et jour figure dans le fichier Excel du calendrier."),
            tableau(["Jour"] + zones_cal + [lib[c] for c in codes] + ["Total", "Cumul"], cal, "Quotas journaliers", taille=8.5),
            tableau(["Moment", "Activité"], [
                [date_fr(jours[0] - timedelta(days=1), True), f"Formation des enquêteurs et des réserves {formation_texte(data['params'].get('hypotheses'))}, prise en main de l'outil et pré-test"],
                [date_fr(jours[0], True), "Démarrage de la collecte"],
                ["Chaque soir", "Envoi des formulaires, point de suivi " + ("à distance avec Datatym (tableau de bord de collecte)"
                  if (data["params"].get("hypotheses") or {}).get("supervision", "distance") == "distance" else "avec le superviseur") + ", ajustement des quotas"],
                [date_fr(jours[len(jours) // 2], True), "Bilan à mi-parcours, réallocation éventuelle des quotas"],
                [date_fr(jours[-1], True), "Clôture de la collecte et contrôle final"],
            ], "Jalons de la collecte"),
        ], source="auto"),
    ]
    rec = data["recrutement"]
    sections.append(section("profils_enq", f"{len(sections) + 1}. Profils d'enquêteurs à rechercher", [
        liste([f"Diplôme minimum : {rec['diplome']}.", f"Expérience d'enquête : {rec['experience']} minimum."] + rec["competences"]),
        p("La note de recrutement jointe reprend ces critères pour diffusion."),
    ]))
    note = {
        "titre": "Note d'échantillonnage des enquêteurs", "surtitre": "Baromètre Datatym", "sous_titre": fiche["theme"],
        "meta": [f"{n} questionnaires · {data['nb_enqueteurs']} enquêteurs · {len(jours)} jours", f"Version du {aujourdhui()}"],
        "en_tete": f"Baromètre {fiche['theme']} — Note d'échantillonnage", "sections": sections,
    }
    besoin = data.get("besoin") or {z: sum(1 for m in data["enqueteurs"] if m["zone"] == z) for z in data["zones"]}
    reserve = data.get("reserve") or {}
    n_res = sum(reserve.values())
    retour = rec.get("retour") or "l'équipe projet Datatym"
    recrut = {
        "titre": "Note de recrutement", "surtitre": "À l'attention du service des ressources humaines", "sous_titre": rec["intitule"],
        "meta": [f"{sum(besoin.values())} enquêteurs{f' + {n_res} réserves' if n_res else ''} · {len(data['zones'])} {Z.lower()}{'s' if len(data['zones']) > 1 else ''}",
                 f"Liste à retourner au plus tard le {date_fr(rec['date_limite'])}"],
        "en_tete": "Datatym — Note de recrutement",
        "sections": [
            section("objet", "1. Objet de la demande", [p(rec["mission"])]),
            section("besoin", f"2. Besoin par {Z.lower()}", [
                tableau([Z, "Titulaires", "Réserves", "Questionnaires à réaliser"],
                        [[z, str(besoin.get(z, 0)), str(reserve.get(z, 0)), str(data["tot_zone"][z])] for z in data["zones"]]
                        + [["**Total**", f"**{sum(besoin.values())}**", f"**{n_res}**", f"**{n}**"]], "Enquêteurs à recruter"),
                p("Chaque enquêteur travaille dans son pays de résidence ; il est recruté pour toute la durée de la collecte."
                  + (" Les réserves suivent la même formation que les titulaires. Elles ne sont mobilisées que pour remplacer un abandon "
                     "et sont, comme les titulaires, rémunérées au questionnaire validé." if n_res else "")),
            ], source="auto"),
            section("profil", "3. Profil recherché", [liste([f"Diplôme : {rec['diplome']} minimum.", f"Expérience d'enquête : {rec['experience']} minimum."] + rec["competences"])]),
            section("mission", "4. Mission confiée aux enquêteurs", [liste(rec["taches"])]),
            section("calendrier", "5. Calendrier", [tableau(["Échéance", "Étape"], [
                [date_fr(rec["date_limite"]), "Retour de la liste des enquêteurs retenus à Datatym"],
                [date_fr(jours[0] - timedelta(days=1)), f"Formation obligatoire des titulaires et des réserves, {formation_texte(data['params'].get('hypotheses'))}"
                 + (" (lien communiqué aux enquêteurs retenus)" if (data["params"].get("hypotheses") or {}).get("formation", "en_ligne") == "en_ligne" else "")],
                [f"Du {date_fr(jours[0])} au {date_fr(jours[-1])}", "Collecte sur le terrain"],
            ], "Calendrier du recrutement et du terrain")], source="auto"),
            section("livrable", "6. Livrable attendu : la liste des enquêteurs retenus", [
                p("La liste est renseignée dans le fichier Excel joint à cette note (feuille « Enquêteurs »), "
                  "à raison d'une ligne par enquêteur retenu. Elle sert à affecter les quotas, organiser la formation "
                  "et envoyer à chacun son contrat, son ordre de mission et les notes de suivi."),
                tableau(["Colonne", "Consigne de remplissage"], [[c, t] for c, _, t in equipe.COLONNES], "Colonnes à renseigner", [1.6, 4.6]),
                p("Exemple de remplissage (personnes fictives) :"),
                tableau([c for c, _, _ in equipe.COLONNES], [[e[k] for _, k, _ in equipe.COLONNES] for e in equipe.exemples(data["zones"])],
                        "Exemple", [0.9, 0.9, 1.0, 0.9, 1.3, 1.6, 0.8], 8),
                liste(["Une ligne par enquêteur, sans ligne vide ni cellule fusionnée ; ne pas renommer les colonnes.",
                       "Le pays de résidence est choisi dans la liste déroulante du fichier.",
                       "Le téléphone commence par l'indicatif du pays, saisi avec une apostrophe devant : **'+221 771234567**. "
                       "Sans l'apostrophe, Excel considère le numéro comme un nombre et supprime le « + ».",
                       "Ne pas ajouter d'identifiant : Datatym l'attribue à chaque enquêteur à la réception de la liste "
                       f"(ENQ, code du pays et numéro d'ordre : {', '.join(equipe.identifiant(c, 1) for c in list(equipe.codes_zones(data['zones']).values())[:3])}…)."]),
            ]),
            section("retour", "7. Retour de la liste", [
                p(f"Le fichier renseigné est à retourner à **{retour}** au plus tard le **{date_fr(rec['date_limite'])}**, "
                  f"en précisant « {rec['intitule']} ».")]),
        ],
    }
    return {"note_echantillonnage": note, "note_recrutement": recrut,
            "budget_collecte": doc_budget(projet, data, jours)}


def doc_budget(projet, data, jours):
    """Budget de collecte : coût de revient poste par poste, document interne."""
    fiche = projet["fiche"]
    b = data["budget"]
    n = b["n"]
    est = projet["etapes"]["cadrage"]["data"].get("estimation") or budget.estimer_cadrage(fiche)
    h = b["hypotheses"]
    if est["bas"] <= b["total"] <= est["haut"]:
        situe = "dans la fourchette annoncée"
    elif b["total"] < est["bas"]:
        situe = "sous la fourchette annoncée"
    else:
        situe = "au-dessus de la fourchette annoncée : les écarts tiennent aux choix du plan de collecte détaillés ci-dessous"
    comparaison = (f"La note de cadrage estimait le coût entre {fcfa(est['bas'])} et {fcfa(est['haut'])}. "
                   f"Le budget établi à partir du plan de collecte s'élève à **{fcfa(b['total'])}**, {situe}.")
    plafond = fiche.get("cout")
    if plafond:
        comparaison += (f" Il respecte le plafond fixé ({fcfa(plafond)})." if b["total"] <= plafond
                        else f" Il dépasse de {fcfa(b['total'] - plafond)} le plafond fixé ({fcfa(plafond)}).")
    lignes = [[l["poste"], l["base"], nombre(l["quantite"], 0), fcfa(l["unitaire"]), fcfa(l["montant"])] for l in b["lignes"]]
    lignes += [["**Sous-total**", "", "", "", f"**{fcfa(b['sous_total'])}**"],
               ["Imprévus", f"{nombre(b['taux_imprevus'], 0)} % du sous-total", "", "", fcfa(b["imprevus"])],
               ["**Total**", "", "", "", f"**{fcfa(b['total'])}**"]]
    sections = [
        section("synthese", "1. Synthèse", [
            chiffres([{"valeur": fcfa(b["total"]), "libelle": "coût de revient total"},
                      {"valeur": fcfa(b["par_questionnaire"]), "libelle": "par questionnaire validé"},
                      {"valeur": pct(b["part_terrain"]), "libelle": "part du terrain"},
                      {"valeur": fcfa(b["marginal_100"]), "libelle": "pour 100 questionnaires de plus"}]),
            p(comparaison),
        ], source="auto"),
        section("detail", "2. Détail par poste", [
            p(f"Chaque poste est calculé à partir du plan de collecte : {n} questionnaires validés, {b['nb_enqueteurs']} enquêteurs, "
              + (f"{b['nb_superviseurs']} superviseur(s), " if b["nb_superviseurs"] else "") + f"{b['nb_jours']} jours de collecte et {b['nb_zones']} zone(s)."),
            tableau(["Poste", "Base de calcul", "Quantité", "Coût unitaire", "Montant"], lignes, "Budget de collecte",
                    [2, 2.4, 0.8, 1.1, 1.3], 9),
        ], source="auto"),
        section("hypotheses", "3. Hypothèses", [
            liste(["Rémunération des enquêteurs au questionnaire validé : un questionnaire écarté au contrôle qualité n'est pas payé.",
                   (f"Un superviseur sur le terrain pour {nombre(h['enq_par_superviseur'], 0)} enquêteurs, au moins un par zone."
                    if h.get("supervision") == "terrain" else "Supervision à distance par Datatym (tableau de bord de collecte) : pas de superviseur sur le terrain."),
                   f"Formation de {nombre(h['jours_formation'], 0)} jour(s) avant le démarrage, {formation_texte(h)}"
                   + (", sans location de salle ni per diem." if h.get("formation", "en_ligne") == "en_ligne" else ", réserves comprises."),
                   f"Rappel de contrôle de {nombre(h['part_rappels'], 0)} % des répondants.",
                   f"{nombre(h['jours_preparation'], 0)} jours de conception et de coordination, {nombre(h['jours_analyse'], 0)} jours de traitement et d'analyse.",
                   f"Provision pour imprévus de {nombre(h['imprevus'], 0)} % du sous-total."]),
            p("Le bilan prévu contre réalisé est établi à la clôture, dans la note de suivi des enquêtes.", "note"),
        ], source="auto"),
    ]
    return {
        "titre": "Budget de collecte", "surtitre": "Baromètre Datatym", "sous_titre": fiche["theme"],
        "meta": [f"Version du {aujourdhui()}"], "en_tete": f"Baromètre {fiche['theme']} — Budget de collecte", "sections": sections,
    }


def calendrier_xlsx(chemin, data):
    from ..formulaires import _feuille
    from openpyxl import Workbook
    lib = {pr["code"]: pr["libelle"] for pr in data["profils"]}
    wb = Workbook()
    ws = wb.active
    ws.title = "Quotas journaliers"
    lignes = []
    for m in data["enqueteurs"]:
        for d, jour in zip(data["jours"], m["par_jour"]):
            for c, v in jour.items():
                if v:
                    lignes.append([d, m["nom"], m["zone"], lib.get(c, c), v])
    _feuille(ws, ["date", "enquêteur", "zone", "profil", "objectif"], lignes)
    ws2 = wb.create_sheet("Enquêteurs")
    _feuille(ws2, ["ID", "nom", "zone", "ville", "téléphone", "mail", "objectif total"] + [lib[c] for c in lib],
             [[m["code"], m["nom"], m["zone"]] + [(m.get("contact") or {}).get(k, "") for k in ("ville", "telephone", "mail")]
              + [m["objectif"]] + [m["par_profil"].get(c, 0) for c in lib] for m in data["enqueteurs"]]
             + [[r["code"], f"{r['nom']} (réserve)", r["zone"]] + [r["contact"].get(k, "") for k in ("ville", "telephone", "mail")] + [0] + [0 for c in lib]
                for r in data.get("reserves") or []])
    wb.properties.creator = wb.properties.lastModifiedBy = "DATATYM"
    wb.save(chemin)
    return chemin
