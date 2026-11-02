"""Documents terrain des enquêteurs : lettre d'introduction auprès des répondants, ordre de mission et engagement
de chaque enquêteur, guide de l'enquêteur. Tirés de la fiche, du questionnaire et du plan d'échantillonnage.
"""
import math
from datetime import date, timedelta

from docx.enum.text import WD_ALIGN_PARAGRAPH

from .banque import du_barometre, sont_des_pays
from .charte import DocDatatym, ajouter_texte, chiffres, liste, p, rendre_modele, section, tableau
from .config import MARINE, auteur_fichiers, charger_parametres
from .etapes.questionnaire import DUREE_MAX
from .outils import aujourdhui, date_fr, fcfa, nombre


def _contexte(projet):
    fiche = projet["fiche"]
    quest = projet["etapes"]["questionnaire"].get("data") or {}
    ech = projet["etapes"]["echantillonnage"].get("data") or {}
    hyp = (ech.get("params") or {}).get("hypotheses") or {}
    b = ech.get("budget") or {}
    u = {c["cle"]: c["valeur"] for c in b.get("couts") or []}
    postes = {l["cle"] for l in b.get("lignes") or []}
    jours = [date.fromisoformat(j) for j in ech.get("jours") or []]
    params = charger_parametres()
    auteur = auteur_fichiers()
    return {
        "fiche": fiche, "quest": quest, "ech": ech, "hyp": hyp, "jours": jours,
        "tarif": u.get("remu_questionnaire", 0) if "remu_questionnaire" in postes else 0,
        "forfaits": [(l, u.get(k, 0)) for k, l in (("transport_jour", "transport"), ("communication_jour", "communication")) if k in postes and u.get(k)],
        # durée annoncée au répondant : celle du message de consentement (plafonnée comme lui)
        "minutes": math.ceil(min(max((quest.get("duree_terrain") or {0: 0}).values()) or 0, DUREE_MAX)),
        "contact": (params.get("contact_enquete") or "").strip(),
        "signataire": "" if auteur.upper() == "DATATYM" else auteur,
        "pays": sont_des_pays(ech.get("zones") or []),
        "profils": {pr["code"]: pr["libelle"] for pr in quest.get("profils") or []},
        "outil": "KoboCollect (KoboToolbox)" if fiche.get("outil", "kobo") == "kobo" else "QuestionPro",
    }


def _membres(ech):
    """Titulaires puis réserves, chacun avec ses coordonnées si la liste des RH a été importée."""
    return [(m, False) for m in ech.get("enqueteurs") or []] + [(r, True) for r in ech.get("reserves") or []]


def _titre(d, texte, sous=""):
    pr = d.doc.add_paragraph()
    ajouter_texte(pr, texte, 18, MARINE, gras_defaut=True)
    if sous:
        pr = d.doc.add_paragraph()
        ajouter_texte(pr, sous, 11, "4B5563")


def _signatures(d, gauche, droite):
    t = d.doc.add_table(rows=2, cols=2)
    for i, (titre, nom) in enumerate((gauche, droite)):
        for r, texte in ((0, titre), (1, f"\n\n\n{nom}")):
            cp = t.rows[r].cells[i].paragraphs[0]
            cp.alignment = WD_ALIGN_PARAGRAPH.LEFT
            ajouter_texte(cp, texte, 11, gras_defaut=(r == 0))


# ------------------------------------------------------------------ lettre d'introduction
def lettre_introduction(chemin, projet):
    """Une lettre par enquêteur (nom et identifiant inscrits) ; sans liste des RH, une lettre à compléter à la main."""
    c = _contexte(projet)
    f, jours = c["fiche"], c["jours"]
    membres = [(m, r) for m, r in _membres(c["ech"]) if "à pourvoir" not in m["nom"]] if c["ech"].get("equipe_rh") else []
    d = DocDatatym(f"{f['theme']} — Lettre d'introduction", pied="Datatym")
    d.proprietes(f["theme"], "Lettre d'introduction de l'enquêteur", auteur_fichiers())
    for k, (m, _) in enumerate(membres or [(None, False)]):
        if k:
            d.saut_page()
        pr = d.doc.add_paragraph()
        ajouter_texte(pr, f"Le {aujourdhui()}", 11)
        pr = d.doc.add_paragraph()
        ajouter_texte(pr, "À l'attention de la Direction", 11, gras_defaut=True)
        pr = d.doc.add_paragraph()
        objet = du_barometre(f["theme"], "le")
        ajouter_texte(pr, f"**Objet :** {objet[:1].upper() + objet[1:]} — présentation de notre enquêteur", 11)
        d.paragraphe("Madame, Monsieur,")
        d.paragraphe(f"Datatym, cabinet spécialisé dans les études et la donnée, réalise {du_barometre(f['theme'], 'le')}. "
                     f"Son objectif : {f['objectif'].rstrip('.')}. "
                     f"Elle s'adresse à : {f['cible'].rstrip('.')}.")
        nom = (f"**{m['nom']}** (identifiant **{m['code']}**)" if m else "**…………………………………………** (identifiant **…………**)")
        d.paragraphe(f"La personne qui vous remet cette lettre, {nom}, est mandatée par Datatym pour conduire l'entretien"
                     + (f" entre le {date_fr(jours[0])} et le {date_fr(jours[-1])}" if jours else "")
                     + f". L'entretien dure environ {c['minutes']} minutes et peut se tenir à l'heure qui vous convient.")
        d.paragraphe("Vos réponses sont strictement confidentielles. Elles ne sont exploitées que de façon statistique et agrégée : "
                     "aucun nom de personne ni d'entreprise n'est publié. Votre participation est volontaire.")
        d.paragraphe("En contrepartie de votre temps, les principaux résultats du baromètre vous seront adressés dès leur publication.")
        d.paragraphe("Pour vérifier l'identité de l'enquêteur ou pour toute question, vous pouvez joindre l'équipe Datatym"
                     + (f" : **{c['contact']}**." if c["contact"] else " : ……………………………………………."))
        d.paragraphe("Nous vous remercions par avance de votre accueil et de votre contribution.")
        d.paragraphe("Veuillez agréer, Madame, Monsieur, l'expression de nos salutations distinguées.")
        pr = d.doc.add_paragraph()
        pr.alignment = WD_ALIGN_PARAGRAPH.LEFT
        ajouter_texte(pr, "\nPour Datatym,\n" + (f"{c['signataire']}\nResponsable de l'étude" if c["signataire"] else "Le responsable de l'étude"), 11, gras_defaut=True)
    return d.enregistrer(chemin)


# ------------------------------------------------------------------ ordres de mission
def ordres_mission(chemin, projet):
    """Une page par enquêteur (titulaires puis réserves) : mission, période, objectif, rémunération et engagements, à signer."""
    c = _contexte(projet)
    f, ech, jours, hyp = c["fiche"], c["ech"], c["jours"], c["hyp"]
    en_ligne = hyp.get("formation", "en_ligne") == "en_ligne"
    formation = date_fr(jours[0] - timedelta(days=1)) if jours else "…"
    rappels = int(hyp.get("part_rappels", 10))
    d = DocDatatym(f"{f['theme']} — Ordres de mission", pied="Datatym")
    d.proprietes(f["theme"], "Ordres de mission des enquêteurs", auteur_fichiers())
    for k, (m, reserve) in enumerate(_membres(ech)):
        if k:
            d.saut_page()
        ct = m.get("contact") or {}
        _titre(d, "Ordre de mission et engagement de l'enquêteur", f"{f['theme']} · {'Réserve' if reserve else 'Enquêteur titulaire'}")
        identite = [["Nom et prénom", m["nom"]], ["Identifiant", m["code"]], ["Pays" if c["pays"] else "Zone", m["zone"]]]
        if ct.get("ville"):
            identite.append(["Ville", ct["ville"]])
        if ct.get("telephone"):
            identite.append(["Téléphone", ct["telephone"]])
        if ct.get("paiement") or ct.get("num_paiement"):
            identite.append(["Paiement", " · ".join(x for x in (ct.get("paiement"), ct.get("num_paiement")) if x)])
        d.tableau(["Enquêteur", ""], identite, "", [1.2, 3], 10)
        mission = [["Mission", f"Collecte {du_barometre(f['theme'])} auprès de : {f['cible'].rstrip('.')}"],
                   ["Formation", f"le {formation}, " + ("en ligne sur Microsoft Teams (présence obligatoire)" if en_ligne else "en présentiel (présence obligatoire)")],
                   ["Période de collecte", f"du {date_fr(jours[0])} au {date_fr(jours[-1])} ({len(jours)} jours)" if jours else "…"],
                   ["Outil", f"{c['outil']}, sur smartphone ou tablette, avec l'identifiant {m['code']}"]]
        if reserve:
            mission.append(["Objectif", "aucun tant que vous n'êtes pas mobilisé(e) ; en cas de remplacement, vous reprenez les quotas restants de l'enquêteur remplacé"])
        else:
            repart = ", ".join(f"{c['profils'].get(code, code)} : {n}" for code, n in (m.get("par_profil") or {}).items() if n)
            mission.append(["Objectif", f"{m['objectif']} questionnaires validés" + (f" ({repart})" if repart else "")
                            + (f", soit environ {nombre(m['objectif'] / len(jours), 1)} par jour" if jours else "")])
        remu = []
        if c["tarif"]:
            remu.append(f"{fcfa(c['tarif'])} par questionnaire validé")
        remu += [f"{fcfa(v)} de {lib} par jour travaillé" for lib, v in c["forfaits"]]
        mission.append(["Rémunération", " ; ".join(remu) + ", versés en fin de collecte par Mobile Money ou virement" if remu else "selon le contrat conclu avec les ressources humaines"])
        d.tableau(["Mission", ""], mission, "", [1.2, 3], 10)
        pr = d.doc.add_paragraph()
        ajouter_texte(pr, "Engagements de l'enquêteur", 12, MARINE, gras_defaut=True)
        d.liste([
            "Suivre la formation en entier et appliquer les consignes du guide de l'enquêteur.",
            "Lire chaque question telle qu'elle est écrite, sans suggérer de réponse, et ne jamais remplir un questionnaire à la place du répondant.",
            "Respecter la répartition par profil et ne pas interroger deux fois la même personne.",
            "Garder strictement confidentielles les réponses et les coordonnées des répondants.",
            "Envoyer les questionnaires chaque jour et signaler sans délai toute difficulté à l'équipe Datatym.",
            f"Accepter les contrôles : {rappels} % des répondants sont rappelés ; un questionnaire écarté au contrôle qualité n'est pas payé, "
            "et un entretien inventé met fin à la mission sans rémunération.",
        ])
        d.paragraphe("Fait en deux exemplaires.", "note")
        _signatures(d, ("Pour Datatym", c["signataire"] or "Le responsable de l'étude"), ("L'enquêteur (lu et approuvé)", m["nom"]))
    return d.enregistrer(chemin)


# ------------------------------------------------------------------ guide de l'enquêteur
def guide_enqueteur(chemin, projet):
    c = _contexte(projet)
    f, quest, ech, jours, hyp = c["fiche"], c["quest"], c["ech"], c["jours"], c["hyp"]
    rappels = int(hyp.get("part_rappels", 10))
    exclusions = [q for q in quest.get("questions_plates") or [] if q.get("exclut")]
    conditionnelles = [q for q in quest.get("questions_plates") or [] if q.get("conditions") or q.get("condition_sur")]
    Z = "pays" if c["pays"] else "zone"
    secs = [
        section("etude", "1. L'étude en bref", [
            chiffres([{"valeur": str(f["taille"]), "libelle": "questionnaires"}, {"valeur": str(len(ech.get("zones") or [])), "libelle": "pays" if c["pays"] else "zones"},
                      {"valeur": str(len(jours)), "libelle": "jours de collecte"}, {"valeur": f"{c['minutes']} min", "libelle": "par entretien"}]),
            liste([f"**Thème :** {f['theme']}.", f"**Objectif :** {f['objectif'].rstrip('.')}.", f"**Qui interroger :** {f['cible'].rstrip('.')}.",
                   f"**Profils :** {', '.join(c['profils'].values())}." if c["profils"] and ", ".join(c["profils"].values()) not in f["cible"] else "",
                   f"**Période :** du {date_fr(jours[0])} au {date_fr(jours[-1])}." if jours else ""]),
        ]),
        section("mission", "2. Votre mission", [
            liste([
                "Vous avez un **objectif de questionnaires validés**, réparti par profil : il figure dans votre ordre de mission. Respectez la répartition : "
                "un profil en excès ne compense pas un profil manquant.",
                "Vous travaillez dans votre pays de résidence, avec votre **identifiant** (ENQ, code du pays, numéro) : il relie chaque questionnaire à vous, pour le suivi et la paie."
                if c["pays"] else "Vous travaillez dans votre zone, avec votre **identifiant** : il relie chaque questionnaire à vous, pour le suivi et la paie.",
                "Organisez vos journées et prenez rendez-vous à l'avance : votre rythme quotidien figure dans votre ordre de mission"
                + (f" (en moyenne {nombre(f['taille'] / (len(ech['enqueteurs']) * len(jours)), 1)} questionnaires par jour et par enquêteur)." if ech.get("enqueteurs") and jours else "."),
                "L'équipe Datatym suit votre avancement chaque jour sur le tableau de bord et vous contacte en cas de retard ou d'anomalie.",
            ]),
        ]),
        section("avant", "3. Avant l'entretien", [
            liste([
                "Identifiez la bonne personne : seul un répondant correspondant à l'un des profils de l'étude peut être interrogé.",
                "Présentez la **lettre d'introduction** signée par Datatym ; elle donne un contact pour vérifier votre identité.",
                "Prenez rendez-vous si la personne n'est pas disponible ; ne réalisez jamais l'entretien avec un remplaçant hors cible.",
                "Vérifiez que votre téléphone est chargé et que le formulaire est à jour.",
            ]),
            p("Lisez ensuite le message d'accueil, mot pour mot :", "gras"),
            p(quest.get("consentement", ""), "encadre"),
            p("Si la personne refuse, remerciez-la et enregistrez le refus : un refus n'est pas une faute, il est compté dans le suivi.", "note"),
        ]),
        section("pendant", "4. Pendant l'entretien", [
            liste([
                "Lisez chaque question **telle qu'elle est écrite**, sans la reformuler ni suggérer de réponse.",
                "Lisez les modalités de réponse quand la question le prévoit ; pour un choix multiple, rappelez que plusieurs réponses sont possibles.",
                "Pour « Autre (préciser) », notez la réponse **mot pour mot** : elle sera recodée à l'apurement.",
                "« Ne sait pas » est une réponse valable : ne forcez jamais une réponse.",
                "Le formulaire n'affiche que les questions qui concernent le répondant (filtres automatiques) : ne sautez aucune question affichée.",
                f"L'entretien dure environ {c['minutes']} minutes. Un questionnaire rempli trop vite (moins de 40 % de la durée habituelle) est écarté.",
                "En fin de questionnaire, demandez si le répondant accepte d'être rappelé pour un court contrôle, et notez ses coordonnées s'il accepte.",
            ]),
        ] + ([p(f"**Questions d'éligibilité :** {len(exclusions)} question(s) mettent fin au questionnaire si le répondant n'entre pas dans la cible "
                f"({', '.join(q['num'] for q in exclusions)}). Un entretien hors cible n'est ni compté ni payé : vérifiez l'éligibilité dès le début.")] if exclusions else [])
          + ([p(f"**Conditions d'affichage :** {len(conditionnelles)} question(s) n'apparaissent qu'en fonction d'une réponse précédente : c'est normal.", "note")] if conditionnelles else [])),
        section("cas", "5. Cas difficiles", [
            tableau(["Situation", "Conduite à tenir"], [
                ["La personne refuse de répondre", "Remercier, ne pas insister, enregistrer le refus et passer au contact suivant."],
                ["La personne est absente ou occupée", "Proposer un rendez-vous ; noter l'heure et rappeler la veille."],
                ["L'interlocuteur n'est pas dans la cible", "Demander à être orienté vers la bonne personne ; ne jamais interroger quelqu'un d'autre à sa place."],
                ["L'entretien est interrompu", "Proposer de le reprendre plus tard ; ne pas compléter les réponses manquantes soi-même."],
                ["La réponse ne figure pas dans la liste", "Choisir « Autre (préciser) » et noter la réponse mot pour mot."],
                ["Le répondant demande les résultats", "Indiquer qu'ils lui seront adressés à leur publication ; ne jamais donner les réponses d'autres répondants."],
                ["Le répondant doute de votre identité", "Montrer la lettre d'introduction et donner le contact de Datatym qui y figure."],
                ["Problème de téléphone ou de réseau", "Le formulaire fonctionne hors ligne : continuer, puis envoyer dès que le réseau revient ; prévenir Datatym si le blocage dure."],
            ], "Situations fréquentes et conduite à tenir", [1.4, 3], 10),
        ]),
        section("outil", "6. L'outil de collecte", [
            liste([
                f"Collecte sur **{c['outil']}**, avec saisie hors ligne.",
                "Avant chaque journée : ouvrir le formulaire et vérifier que votre identifiant est bien sélectionné." if c["outil"].startswith("Kobo")
                else "Utilisez uniquement le lien personnel qui porte votre identifiant : un questionnaire rempli par un autre lien ne vous est pas attribué.",
                "Envoyez vos questionnaires **chaque jour** : c'est ce qui permet le suivi et le paiement.",
            ]),
        ]),
        section("qualite", "7. Contrôle qualité et rémunération", [
            liste([
                f"**{rappels} % des répondants sont rappelés** pour vérifier que l'entretien a bien eu lieu et que quelques réponses concordent.",
                "Sont écartés : les entretiens sans consentement, hors cible, trop rapides, en double, ou déclarés non réalisés au rappel.",
                "Seuls les questionnaires validés sont payés" + (f" ({fcfa(c['tarif'])} chacun)" if c["tarif"] else "") + ", en fin de collecte, au moyen de paiement communiqué aux RH.",
                "Un entretien inventé met fin à la mission sans rémunération.",
            ]),
        ]),
        section("contacts", "8. Contacts", [
            p("Pour toute question, difficulté ou absence, prévenez l'équipe Datatym le jour même"
              + (f" : **{c['contact']}**." if c["contact"] else " (contact communiqué lors de la formation).")
              + (" Un point d'équipe se tient en ligne sur Microsoft Teams pendant la collecte." if hyp.get("supervision", "distance") == "distance" else "")),
        ]),
    ]
    for s in secs:
        for b in s["blocs"]:
            if b["type"] == "liste":
                b["items"] = [i for i in b["items"] if i]
    modele = {"titre": f["theme"], "sous_titre": "Guide de l'enquêteur", "surtitre": "", "meta": [f"Version du {aujourdhui()}", "Auteur : DATATYM"],
              "en_tete": f"{f['theme']} — Guide de l'enquêteur", "pied": "Datatym", "sections": secs}
    return rendre_modele(modele, chemin)


FICHIERS = [
    ("Guide_Enqueteur", "Guide de l'enquêteur", guide_enqueteur),
    ("Lettre_Introduction", "Lettre d'introduction auprès des répondants", lettre_introduction),
    ("Ordres_Mission", "Ordres de mission et engagements des enquêteurs", ordres_mission),
]
