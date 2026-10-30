"""Étape 6 — Note de suivi des enquêtes, tirée du tableau de bord de la collecte et mise à jour avec lui."""
from .. import budget
from ..charte import chiffres, liste, p, section, tableau
from ..banque import sont_des_pays
from ..outils import aujourdhui, date_courte, date_fr, fcfa, nombre, pct

DOCS = {"note_suivi": ("NoteSuivi", "Note de suivi des enquêtes")}


ANCIENS_DEFAUTS = {
    "observations": [["Bonne adhésion des répondants au message de consentement.",
                      "Difficultés d'accès à certains profils de direction, compensées par des prises de rendez-vous."]],
    "recommandations": [["Anticiper les prises de rendez-vous avec les profils de direction dès la première semaine.",
                         "Renforcer le contrôle de la durée des entretiens dès les premiers jours.",
                         "Conserver les mêmes échelles et formulations pour la prochaine édition afin d'assurer la comparabilité."]],
}


def generer(projet, precedent=None):
    """Observations et recommandations : vides = rédigées automatiquement à partir des données de collecte."""
    prec = precedent or {}
    garder = lambda k: None if prec.get(k) in ANCIENS_DEFAUTS[k] else prec.get(k)
    return {
        "observations": garder("observations"),
        "recommandations": garder("recommandations"),
        # dépenses réelles par poste du budget de collecte, saisies à la clôture
        "depenses": prec.get("depenses") or {},
    }


def _minuscule(libelle):
    """« Directeur général » -> « directeur général » ; les sigles (DSI, DRH) restent en capitales."""
    mot = libelle.split()[0] if libelle else ""
    return libelle if mot.isupper() else libelle[:1].lower() + libelle[1:]


def _pluriel(n, mot, pluriel=None):
    return f"{n} {mot if n < 2 else (pluriel or mot + 's')}"


def _liste_noms(items, n=3):
    noms = [f"{x[0]} ({x[1]})" for x in items[:n]]
    return ", ".join(noms[:-1]) + " et " + noms[-1] if len(noms) > 1 else (noms[0] if noms else "")


def analyser(projet, s):
    """Observations de terrain et recommandations tirées des chiffres de la collecte (aucun texte figé)."""
    ech = projet["etapes"]["echantillonnage"].get("data") or {}
    quest = projet["etapes"]["questionnaire"].get("data") or {}
    obs, reco = [], []
    en_cours = s["jour_index"] < s["nb_jours"]
    if s["jour_index"] <= 0:
        # collecte pas encore commencée : les réponses reçues sont des essais
        return ([f"La collecte n'a pas encore commencé (début prévu le {date_fr(s['par_jour'][0]['date'])})"
                 + (f" ; {_pluriel(s['brut'], 'réponse reçue', 'réponses reçues')}, à considérer comme des essais." if s["brut"] else ".")],
                ["Vérifier avant le démarrage que chaque enquêteur dispose du lien ou du formulaire portant son identifiant.",
                 "Conserver les mêmes échelles et formulations pour la prochaine édition afin d'assurer la comparabilité."])
    ecoule = s["prevu_a_date"] / s["objectif"] if s["objectif"] else 0  # part de l'objectif prévue à date
    zone_mot = "pays" if sont_des_pays([z["zone"] for z in s["par_zone"]]) else "zones"

    # rythme global
    passes = [j for j in s["par_jour"] if j["passe"]]
    moyenne = s["realise"] / len(passes) if passes else 0
    restant = max(s["objectif"] - s["realise"], 0)
    if s["prevu_a_date"] and s["realise"] < 0.9 * s["prevu_a_date"]:
        retard = s["prevu_a_date"] - s["realise"]
        obs.append(f"{'Au jour ' + str(s['jour_index']) + ' sur ' + str(s['nb_jours']) if en_cours else 'En fin de collecte'}, "
                   f"{s['realise']} questionnaires valides pour {s['prevu_a_date']} prévus : retard de {retard} questionnaires "
                   f"({nombre(100 * retard / s['prevu_a_date'], 0)} % du prévu), au rythme moyen de {nombre(moyenne, 1)} par jour.")
        jours_restants = s["nb_jours"] - s["jour_index"]
        if en_cours and moyenne:
            besoin = restant / max(jours_restants, 1)
            jours_necessaires = -(-restant // max(round(moyenne), 1))
            reco.append(f"Pour atteindre l'objectif, passer de {nombre(moyenne, 1)} à {nombre(besoin, 1)} questionnaires valides par jour "
                        + (f"ou prolonger la collecte d'environ {max(jours_necessaires - jours_restants, 0)} jours"
                           if jours_necessaires > jours_restants else "")
                        + " ; mobiliser les réserves dans les pays les plus en retard.")
    elif s["prevu_a_date"] and s["realise"] > 1.1 * s["prevu_a_date"]:
        obs.append(f"La collecte est en avance : {s['realise']} questionnaires valides pour {s['prevu_a_date']} prévus à date.")
    elif s["prevu_a_date"]:
        obs.append(f"La collecte suit le calendrier : {s['realise']} questionnaires valides pour {s['prevu_a_date']} prévus à date.")
    sans_collecte = [j for j in passes if not j["realise"]]
    if len(sans_collecte) >= 2:
        obs.append(f"{_pluriel(len(sans_collecte), 'journée')} de collecte sans aucun questionnaire valide.")

    # pays ou zones
    zones = sorted([z for z in s["par_zone"] if z["objectif"]], key=lambda z: z["taux"])
    seuil = 100 * ecoule * 0.5
    retard_z = [(z["zone"], f"{z['realise']} sur {z['objectif']}") for z in zones if z["taux"] < seuil]
    avance_z = [(z["zone"], f"{nombre(z['taux'], 0)} %") for z in reversed(zones) if z["taux"] >= 100 * ecoule]
    if retard_z:
        obs.append(f"Avancement inégal entre {zone_mot} : les plus en retard sont {_liste_noms(retard_z)}"
                   + (f", quand {_liste_noms(avance_z, 2)} {'sont' if len(avance_z) > 1 else 'est'} à jour." if avance_z else "."))
        reco.append(f"Renforcer le terrain là où la collecte est en retard ({', '.join(z for z, _ in retard_z[:3])}) : réserves, relances ciblées, "
                    f"nouveaux contacts ; réaffecter si besoin les quotas vers les {zone_mot} en avance.")
    vides = [z["zone"] for z in zones if not z["realise"] and s["realise"]]
    if vides:
        obs.append(f"Aucun questionnaire valide à ce jour : {', '.join(vides)}.")

    # profils
    profils = [x for x in s["par_profil"] if x["objectif"]]
    moy = sum(x["taux"] for x in profils) / len(profils) if profils else 0
    durs = sorted([x for x in profils if x["taux"] < 0.5 * moy], key=lambda x: x["taux"])
    if durs:
        obs.append("Profils les plus difficiles à joindre : " + ", ".join(f"{x['profil']} ({x['realise']} sur {x['objectif']})" for x in durs[:3]) + ".")
        reco.append(f"Prendre rendez-vous avec les {_minuscule(durs[0]['profil'])}"
                    + (f" et les {_minuscule(durs[1]['profil'])}" if len(durs) > 1 else "")
                    + " dès la première semaine, en s'appuyant sur les réseaux professionnels et les annuaires d'entreprises.")

    # secteurs
    secteurs_vides = [x["secteur"] for x in s.get("par_secteur") or [] if not x["realise"]]
    if secteurs_vides and s["realise"] >= 30:
        obs.append(f"{_pluriel(len(secteurs_vides), 'secteur')} sans aucune réponse : {', '.join(secteurs_vides[:4])}{'…' if len(secteurs_vides) > 4 else ''}.")
        reco.append("Cibler explicitement les secteurs absents dans la liste des entreprises à contacter.")

    # qualité
    if s["brut"]:
        part_hc = 100 * s["hors_cible"] / s["brut"]
        if part_hc >= 10:
            obs.append(f"{s['hors_cible']} réponses hors cible ({nombre(part_hc, 0)} % des questionnaires reçus) : "
                       "des répondants ne correspondent pas au profil visé.")
            reco.append("Rappeler les critères d'éligibilité aux enquêteurs et placer les questions de filtrage dès le début du questionnaire.")
        part_ref = 100 * s["refus"] / s["brut"]
        if part_ref >= 10:
            obs.append(f"{s['refus']} refus de participation ({nombre(part_ref, 0)} % des contacts enregistrés).")
            reco.append("Retravailler le message d'introduction et rappeler la confidentialité des réponses dès le premier contact.")
        if s["rapides"]:
            obs.append(f"{_pluriel(s['rapides'], 'entretien anormalement court écarté', 'entretiens anormalement courts écartés')} au contrôle qualité.")
            reco.append("Vérifier par rappel les enquêteurs concernés par les entretiens trop courts.")
    duree = s.get("duree_mediane")
    estimee = max((quest.get("duree_terrain") or {}).values() or [0])
    if duree and estimee and duree > 1.25 * estimee:
        obs.append(f"Durée médiane d'un entretien de {nombre(duree, 1)} minutes, au-dessus des {nombre(estimee, 0)} minutes prévues.")
        reco.append("Alléger le questionnaire pour la prochaine édition en retirant les questions les moins utilisées dans le rapport.")
    elif duree and duree > 15:
        obs.append(f"Durée médiane d'un entretien de {nombre(duree, 1)} minutes, au-delà du plafond de 15 minutes.")
        reco.append("Alléger le questionnaire pour revenir sous les 15 minutes.")

    # collecteurs
    coll = [c for c in s.get("par_collecteur") or [] if c["valides"]]
    if len(coll) >= 3 and s["realise"]:
        top = coll[0]
        part = 100 * top["valides"] / s["realise"]
        if part >= 35:
            obs.append(f"Un collecteur concentre {nombre(part, 0)} % des questionnaires valides ({top['nom']}, {top['valides']}).")
            reco.append("Mieux répartir la charge entre collecteurs pour limiter la dépendance à une seule personne.")
    if s.get("donnees_perimees"):
        obs.append("Une partie des données provient d'une version antérieure du questionnaire.")

    if not obs:
        obs.append("La collecte se déroule conformément au plan : rythme, quotas et qualité des réponses sans écart notable.")
    reco.append("Conserver les mêmes échelles et formulations pour la prochaine édition afin d'assurer la comparabilité.")
    return obs, reco


COLONNES_SUIVI = ["Objectif", "Réalisé", "Restant", "Taux de réalisation"]


def _restant(objectif, realise):
    """Questionnaires restant à collecter ; un dépassement est signalé plutôt qu'affiché en négatif."""
    reste = objectif - realise
    return str(reste) if reste >= 0 else f"0 (+{-reste})"


def _suivi(objectif, realise):
    return [objectif, realise, _restant(objectif, realise), pct(100 * realise / objectif if objectif else 0)]


def _total(libelles, lignes):
    """Ligne de total en gras ; libelles = cellules de tête (ex. ["**Total**"] ou ["**Total**", ""])."""
    obj, rea = sum(l["objectif"] for l in lignes), sum(l["realise"] for l in lignes)
    return libelles + [f"**{v}**" for v in _suivi(obj, rea)]


def construire_docs(projet, data, stats):
    fiche = projet["fiche"]
    if not stats:
        return {"note_suivi": {"titre": "Note de suivi des enquêtes", "surtitre": "Baromètre Datatym", "sous_titre": fiche["theme"],
                               "meta": [], "en_tete": "", "sections": [section("vide", "Données manquantes", [
                                   p("Aucune soumission n'a encore été importée à l'étape Collecte.")], source="auto")]}}
    s = stats
    Z = "Pays" if sont_des_pays([z["zone"] for z in s["par_zone"]]) else "Zone"
    j0, j1 = s["par_jour"][0]["date"], s["par_jour"][-1]["date"]
    ecart = s["realise"] - s["objectif"]
    en_cours = s["jour_index"] < s["nb_jours"]
    for k in ANCIENS_DEFAUTS:  # anciens textes standard jamais retouchés : remplacés par les textes tirés des données
        if data.get(k) in ANCIENS_DEFAUTS[k]:
            data[k] = None
    auto_obs, auto_reco = analyser(projet, s)
    # textes automatiques visibles dans l'onglet Observations ; ceux saisis à la main les remplacent
    data["auto"] = {"observations": auto_obs, "recommandations": auto_reco}
    hyp = (projet["etapes"]["echantillonnage"].get("data") or {}).get("params", {}).get("hypotheses") or {}
    sections = [
        section("synthese", "1. Synthèse", [
            chiffres([{"valeur": str(s["brut"]), "libelle": "questionnaires reçus" + (f", dont {s['hors_cible']} hors cible" if s["hors_cible"] else "")},
                      {"valeur": str(s["realise"]), "libelle": f"questionnaires valides sur {s['objectif']} visés"},
                      {"valeur": pct(s["taux"]), "libelle": "taux de réalisation"},
                      {"valeur": str(max(s["objectif"] - s["realise"], 0)), "libelle": "questionnaires restants"}]),
            p((f"La collecte est prévue du {date_fr(j0)} au {date_fr(j1)} ; elle n'a pas encore commencé ({_pluriel(s['brut'], 'réponse d’essai reçue', 'réponses d’essai reçues')})."
               if s["jour_index"] <= 0 else
               f"La collecte se déroule du {date_fr(j0)} au {date_fr(j1)}. Au {date_fr(s['reference'])} (jour {s['jour_index']} sur {s['nb_jours']}), "
               f"**{s['realise']} questionnaires valides** ont été recueillis pour un objectif de {s['objectif']}, soit un taux de réalisation de "
               f"{pct(s['taux'])} ; {s['prevu_a_date']} étaient prévus à cette date." if en_cours else
               f"La collecte s'est déroulée du {date_fr(j0)} au {date_fr(j1)}. **{s['realise']} questionnaires valides** ont été recueillis "
               f"pour un objectif de {s['objectif']}, soit un taux de réalisation de {pct(s['taux'])}"
               + (f" ({ecart:+d} questionnaires)." if ecart else "."))),
            p(f"Sur {s['brut']} formulaires reçus, {s['refus']} correspondent à des refus de participation, {s['hors_cible']} à des répondants hors cible "
              f"et {s['rapides']} à des entretiens trop rapides, écartés de l'analyse : "
              f"{pct(s['taux_completion'])} des questionnaires reçus sont donc valides."
              + (f" La durée médiane d'un entretien est de {nombre(s['duree_mediane'], 1)} minutes." if s["duree_mediane"] else "")),
        ], source="auto"),
        section("realise", "2. Réalisé contre prévu", [
            tableau([Z] + COLONNES_SUIVI, [[z["zone"]] + _suivi(z["objectif"], z["realise"]) for z in s["par_zone"]]
                    + [_total(["**Total**"], s["par_zone"])], f"Réalisation par {Z.lower()}"),
            tableau(["Profil"] + COLONNES_SUIVI, [[x["profil"]] + _suivi(x["objectif"], x["realise"]) for x in s["par_profil"]]
                    + [_total(["**Total**"], s["par_profil"])], "Réalisation par profil"),
            tableau([Z, "Profil"] + COLONNES_SUIVI, [[q["zone"], q["profil"]] + _suivi(q["objectif"], q["realise"]) for q in s["quotas"]]
                    + [_total(["**Total**", ""], s["quotas"])], f"Atteinte des quotas {Z.lower()} × profil", taille=9),
        ], source="auto"),
        section("enqueteurs", "3. Performance des enquêteurs", [
            tableau(["Enquêteur", Z] + COLONNES_SUIVI,
                    [[e["nom"], e["zone"]] + _suivi(e["objectif"], e["realise"]) for e in s["par_enqueteur"]]
                    + [_total(["**Total**", ""], s["par_enqueteur"])], "Réalisation par enquêteur", taille=9),
        ], source="auto"),
        section("rythme", "4. Rythme de collecte", [
            tableau(["Jour", "Prévu", "Réalisé", "Cumul prévu", "Cumul réalisé", "Reste à collecter"],
                    [[date_courte(j["date"]), j["prevu"], j["realise"], j["cumul_prevu"], j["cumul_realise"],
                      _restant(s["objectif"], j["cumul_realise"])] for j in s["par_jour"]],
                    "Rythme quotidien", taille=9),
        ], source="auto"),
        section("qualite", "5. Incidents et qualité des données", [
            liste(s["incidents"] or ["Aucun incident majeur relevé."]),
            p(("Règles appliquées : exclusion des refus, des hors-cible et des entretiens d'une durée inférieure à 40 % de la médiane ; "
               if s.get("controle_qualite", True) else
               "Mode « suivi seul » : toutes les réponses avec consentement sont comptées, sans exclusion automatique ; ")
              + f"contrôle de cohérence des réponses ; rappel de vérification de {nombre(hyp.get('part_rappels', 10), 0)} % des répondants.", "note"),
        ], source="auto"),
        section("observations", "6. Observations de terrain", [liste(data.get("observations") or auto_obs)],
                source="texte" if data.get("observations") else "auto"),
        section("recommandations", "7. Recommandations" + (" pour la suite de la collecte et la prochaine édition" if en_cours else " pour la prochaine édition"),
                [liste(data.get("recommandations") or auto_reco)], source="texte" if data.get("recommandations") else "auto"),
    ]
    bil = budget.bilan(projet["etapes"]["echantillonnage"]["data"].get("budget"), data.get("depenses"), s)
    if bil:
        sections.append(section("bilan_financier", "8. Bilan financier", blocs_bilan(bil), source="auto"))
    return {"note_suivi": {
        "titre": "Note de suivi des enquêtes", "surtitre": "Baromètre Datatym", "sous_titre": fiche["theme"],
        "meta": [f"Collecte du {date_fr(j0)} au {date_fr(j1)}", f"Version du {aujourdhui()}"],
        "en_tete": f"Baromètre {fiche['theme']} — Note de suivi", "sections": sections,
    }}


def blocs_bilan(b):
    if not b["saisi"]:
        return [p("Les dépenses réelles ne sont pas encore saisies : renseignez-les dans l'onglet « Bilan financier » "
                  "de l'étape pour comparer le réalisé au budget de collecte.", "note")]
    ecart = lambda v: "–" if v is None else ("+" if v > 0 else "") + fcfa(v)
    lignes = [[l["poste"], fcfa(l["prevu"]), "non saisi" if l["reel"] is None else fcfa(l["reel"]), ecart(l["ecart"]),
               "–" if l["reel"] is None or not l["prevu"] else pct(100 * l["ecart"] / l["prevu"])] for l in b["lignes"]]
    lignes.append(["**Total des postes saisis**", f"**{fcfa(b['prevu_saisis'])}**", f"**{fcfa(b['reel'])}**", f"**{ecart(b['ecart'])}**",
                   f"**{pct(100 * b['ecart'] / b['prevu_saisis']) if b['prevu_saisis'] else '–'}**"])
    blocs = [
        chiffres([{"valeur": fcfa(b["reel"]), "libelle": "dépenses réelles" + ("" if b["complet"] else " (postes saisis)")},
                  {"valeur": ecart(b["ecart"]), "libelle": "écart au budget"},
                  {"valeur": fcfa(b["par_questionnaire_reel"]) if b["par_questionnaire_reel"] else "–", "libelle": "coût réel par questionnaire validé"},
                  {"valeur": fcfa(b["non_qualite"]), "libelle": "coût estimé des questionnaires écartés"}]),
        p(f"Le budget de collecte prévoyait {fcfa(b['prevu'])}, soit {fcfa(b['par_questionnaire_prevu'])} par questionnaire validé. "
          + (f"Le coût réel s'établit à {fcfa(b['par_questionnaire_reel'])} pour {b['valides']} questionnaires validés. " if b["par_questionnaire_reel"] else "")
          + (f"Les {b['ecartes']} questionnaires écartés au contrôle qualité ont mobilisé environ {fcfa(b['non_qualite'])} de frais de terrain."
             if b["ecartes"] else "")),
        tableau(["Poste", "Prévu", "Réalisé", "Écart", "Écart (%)"], lignes, "Budget prévu et dépenses réelles", [2.4, 1.2, 1.2, 1.2, 0.9], 9),
    ]
    if not b["complet"]:
        blocs.append(p("Certains postes ne sont pas encore saisis : le bilan ne porte que sur les postes renseignés.", "note"))
    blocs.append(p("Les coûts unitaires constatés servent de référence pour estimer la prochaine édition.", "note"))
    return blocs
