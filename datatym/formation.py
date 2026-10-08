"""PowerPoint de formation des enquêteurs (.pptx modifiable), généré pour chaque baromètre."""
import math
from datetime import date, timedelta

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Emu, Pt

from .config import BLEU, LOGO, LOGO_AGILTYM, LOGO_AGILTYM_BLANC, LOGO_DATATYM_BLANC, MARINE, charger_parametres
from .outils import date_fr

W, H = Emu(12192000), Emu(6858000)
POL = "Calibri"


def _c(h):
    return RGBColor.from_string(h)


class Deck:
    def __init__(self):
        self.prs = Presentation()
        self.prs.slide_width, self.prs.slide_height = W, H
        self.vide = self.prs.slide_layouts[6]
        self.n = 0

    def slide(self, fond="FFFFFF"):
        s = self.prs.slides.add_slide(self.vide)
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = _c(fond)
        self.n += 1
        return s

    def rect(self, s, x, y, w, h, couleur, forme=MSO_SHAPE.RECTANGLE):
        r = s.shapes.add_shape(forme, Emu(x), Emu(y), Emu(w), Emu(h))
        r.fill.solid()
        r.fill.fore_color.rgb = _c(couleur)
        r.line.fill.background()
        r.shadow.inherit = False
        return r

    def texte(self, s, x, y, w, h, contenu, taille=18, gras=False, couleur=MARINE, align=PP_ALIGN.LEFT, ancre=MSO_ANCHOR.TOP):
        tb = s.shapes.add_textbox(Emu(x), Emu(y), Emu(w), Emu(h))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = ancre
        tf.margin_left = tf.margin_right = Emu(0)
        lignes = contenu if isinstance(contenu, list) else [contenu]
        for i, l in enumerate(lignes):
            par = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            par.alignment = align
            par.space_after = Pt(6)
            r = par.add_run()
            r.text = str(l)
            r.font.size, r.font.bold, r.font.name = Pt(taille), gras, POL
            r.font.color.rgb = _c(couleur)
        return tb

    def puces(self, s, x, y, w, h, items, taille=17, couleur="1F2937"):
        tb = s.shapes.add_textbox(Emu(x), Emu(y), Emu(w), Emu(h))
        tf = tb.text_frame
        tf.word_wrap = True
        for i, it in enumerate(items):
            par = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            par.space_after = Pt(10)
            r = par.add_run()
            r.text = "■  "
            r.font.size, r.font.color.rgb, r.font.name = Pt(taille - 6), _c(BLEU), POL
            if isinstance(it, tuple):
                r = par.add_run()
                r.text = it[0] + " "
                r.font.size, r.font.bold, r.font.name = Pt(taille), True, POL
                r.font.color.rgb = _c(MARINE)
                it = it[1]
            r = par.add_run()
            r.text = str(it)
            r.font.size, r.font.name = Pt(taille), POL
            r.font.color.rgb = _c(couleur)
        return tb

    def logos(self, s, sombre=False, y=300000, h=300000, droite=11592000):
        """Datatym puis Agiltym, alignés en haut à droite de la diapositive."""
        datatym, agiltym = (LOGO_DATATYM_BLANC, LOGO_AGILTYM_BLANC) if sombre else (LOGO, LOGO_AGILTYM)
        if agiltym.exists():
            a = s.shapes.add_picture(str(agiltym), Emu(0), Emu(y), height=Emu(int(h * .85)))
            a.left = Emu(droite - a.width)
            droite = a.left - 260000
        if datatym.exists():
            d = s.shapes.add_picture(str(datatym), Emu(0), Emu(y), height=Emu(h))
            d.left = Emu(droite - d.width)

    def contenu(self, titre, surtitre=""):
        s = self.slide()
        self.rect(s, 0, 0, 12192000, 90000, BLEU)
        if surtitre:
            self.texte(s, 600000, 380000, 9000000, 300000, surtitre.upper(), 12, True, BLEU)
        self.texte(s, 600000, 640000, 10500000, 700000, titre, 30, True, MARINE)
        self.logos(s)
        self.texte(s, 600000, 6330000, 6000000, 250000, f"{self.n}   ·   Document interne — Confidentiel", 10, False, "9CA3AF")
        return s

    def intercalaire(self, num, titre, sous):
        s = self.slide(MARINE)
        self.logos(s, sombre=True)
        self.rect(s, 600000, 2500000, 120000, 1700000, BLEU)
        self.texte(s, 950000, 2350000, 3000000, 900000, f"{num:02d}", 54, True, BLEU)
        self.texte(s, 950000, 3150000, 10000000, 700000, titre, 36, True, "FFFFFF")
        self.texte(s, 950000, 3850000, 10000000, 500000, sous, 18, False, "C7D2E3")
        return s

    def tableau(self, s, x, y, w, colonnes, lignes, taille=12):
        h = Emu(330000 * (len(lignes) + 1))
        t = s.shapes.add_table(len(lignes) + 1, len(colonnes), Emu(x), Emu(y), Emu(w), h).table
        for j, c in enumerate(colonnes):
            cell = t.cell(0, j)
            cell.text = str(c)
            cell.fill.solid()
            cell.fill.fore_color.rgb = _c(MARINE)
            for par in cell.text_frame.paragraphs:
                for r in par.runs:
                    r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(taille), True, _c("FFFFFF"), POL
        for i, l in enumerate(lignes, 1):
            for j, v in enumerate(l):
                cell = t.cell(i, j)
                cell.text = str(v)
                cell.fill.solid()
                cell.fill.fore_color.rgb = _c("F2F4F7" if i % 2 == 0 else "FFFFFF")
                for par in cell.text_frame.paragraphs:
                    for r in par.runs:
                        r.font.size, r.font.name, r.font.color.rgb = Pt(taille), POL, _c("1F2937")
        return t


def generer_pptx(chemin, projet, cadrage, quest, ech):
    fiche = projet["fiche"]
    params = charger_parametres()
    outil = "KoboToolbox (KoboCollect)" if fiche.get("outil") == "kobo" else "QuestionPro"
    jours = [date.fromisoformat(j) for j in ech["jours"]]
    lib = {pr["code"]: pr["libelle"] for pr in quest["profils"]}
    d = Deck()

    # 1. Couverture
    s = d.slide()
    d.rect(s, 0, 0, 4300000, 6858000, MARINE)
    d.rect(s, 4300000, 0, 90000, 6858000, BLEU)
    d.logos(s, y=650000, h=560000, droite=11592000)
    d.texte(s, 5000000, 2200000, 6600000, 400000, "FORMATION DES ENQUÊTEURS", 14, True, BLEU)
    d.texte(s, 5000000, 2650000, 6600000, 1600000, f"Baromètre {fiche['theme']}", 34, True, MARINE)
    d.texte(s, 5000000, 4500000, 6600000, 800000, [f"Collecte du {date_fr(jours[0])} au {date_fr(jours[-1])}",
                                                   f"{fiche['taille']} questionnaires · {ech['nb_enqueteurs']} enquêteurs"], 16, False, "4B5563")
    d.texte(s, 600000, 5800000, 3400000, 500000, "Datatym", 20, True, "FFFFFF")

    # 2. Programme
    s = d.contenu("Programme de la formation")
    modules = [("01", "Datatym et le baromètre", "Objectif, cible, chiffres clés"), ("02", "Le rôle de l'enquêteur", "Posture, éthique, consentement"),
               ("03", "Le questionnaire", "Section par section, consignes et pièges"), ("04", "L'outil de collecte", outil),
               ("05", "Quotas et calendrier", "Objectifs, suivi, contrôle qualité"), ("06", "Mise en pratique", "Cas pratiques, jeu de rôle, quiz")]
    for i, (num, t, st) in enumerate(modules):
        x = 600000 + (i % 3) * 3700000
        y = 1700000 + (i // 3) * 2100000
        d.rect(s, x, y, 3450000, 1850000, "F2F4F7")
        d.texte(s, x + 250000, y + 200000, 1000000, 500000, num, 28, True, BLEU)
        d.texte(s, x + 250000, y + 800000, 3000000, 450000, t, 18, True, MARINE)
        d.texte(s, x + 250000, y + 1250000, 3000000, 500000, st, 13, False, "4B5563")

    # Module 1
    d.intercalaire(1, "Datatym et le baromètre", "Pourquoi ce baromètre, qui interroger")
    s = d.contenu("Qui sommes-nous ?", "Datatym")
    d.texte(s, 600000, 1700000, 10900000, 3500000, params.get("presentation_datatym", ""), 20, False, "1F2937")
    s = d.contenu("Le baromètre en chiffres", "Le baromètre")
    d.texte(s, 600000, 1500000, 10900000, 800000, f"Objectif : {fiche['objectif']}", 18, False, "1F2937")
    kpis = [(str(fiche["taille"]), "questionnaires"), (str(len(ech["zones"])), "zones d'enquête"), (str(len(jours)), "jours de collecte"),
            (f"{math.ceil(quest['duree_max'])} min", "durée du questionnaire")]
    for i, (v, l) in enumerate(kpis):
        x = 600000 + i * 2750000
        d.rect(s, x, 2700000, 2550000, 1900000, "E6F3FC")
        d.texte(s, x, 2950000, 2550000, 900000, v, 40, True, BLEU, PP_ALIGN.CENTER)
        d.texte(s, x, 3900000, 2550000, 500000, l, 15, False, MARINE, PP_ALIGN.CENTER)
    d.texte(s, 600000, 5000000, 10900000, 600000, "Zones : " + " · ".join(ech["zones"]), 15, False, "4B5563")
    s = d.contenu("Qui interroger ?", "La cible")
    d.texte(s, 600000, 1500000, 10900000, 500000, "Un répondant = une personne du profil attendu, dans la zone attribuée.", 18, False, "1F2937")
    for i, pr in enumerate(quest["profils"][:4]):
        x = 600000 + i * 2750000
        d.rect(s, x, 2300000, 2550000, 1500000, MARINE)
        d.texte(s, x + 150000, 2450000, 2250000, 1200000, [pr["libelle"], "Direction" if pr["niveau"] == "direction" else "Opérationnel"],
                17, True, "FFFFFF", PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
    d.puces(s, 600000, 4200000, 10900000, 1800000, [
        "Vérifier le profil (question sur la fonction) avant de poursuivre : hors cible, on remercie et on arrête.",
        f"Secteur visé : {fiche.get('secteur') or 'secteur formel'}.",
        "Un seul questionnaire par personne ; jamais de questionnaire rempli à la place du répondant."], 15)

    # Module 2
    d.intercalaire(2, "Le rôle de l'enquêteur", "Posture, éthique et consentement")
    s = d.contenu("Votre posture sur le terrain", "Rôle de l'enquêteur")
    d.puces(s, 600000, 1600000, 5300000, 4300000, [("Neutre :", "lire les questions telles qu'elles sont écrites, sans commenter les réponses."),
                                                   ("Précis :", "noter exactement ce que dit le répondant."),
                                                   ("Patient :", "laisser le temps de réfléchir, relancer sans orienter."),
                                                   ("Ponctuel :", "respecter les rendez-vous et le calendrier.")], 16)
    d.puces(s, 6300000, 1600000, 5300000, 4300000, [("Présentable :", "tenue correcte, badge Datatym visible."),
                                                    ("Honnête :", "jamais de questionnaire inventé ou complété seul."),
                                                    ("Discret :", "aucune réponse n'est répétée à un tiers."),
                                                    ("Réactif :", "signaler tout problème au superviseur le jour même.")], 16)
    s = d.contenu("Éthique et recueil du consentement", "Rôle de l'enquêteur")
    d.rect(s, 600000, 1600000, 10900000, 2300000, "E6F3FC")
    d.rect(s, 600000, 1600000, 80000, 2300000, BLEU)
    d.texte(s, 900000, 1750000, 10400000, 2000000, "« " + quest["consentement"] + " »", 15, False, MARINE)
    d.puces(s, 600000, 4200000, 10900000, 1800000, ["Lire le message de consentement en entier, sans le résumer.",
                                                    "Sans accord explicite (« Oui »), l'entretien s'arrête immédiatement.",
                                                    "Le répondant peut interrompre à tout moment : on le remercie."], 15)

    # Module 3 : questionnaire
    d.intercalaire(3, "Le questionnaire", f"{len(quest['questions_plates'])} questions, {len(quest['sections'])} sections, environ {math.ceil(quest['duree_max'])} minutes")
    s = d.contenu("Les types de questions", "Le questionnaire")
    types = [("Choix unique", "Une seule réponse. Lire les modalités, sauf « Ne sait pas »."),
             ("Choix multiple", "3 réponses au maximum. « Ne sait pas » exclut les autres réponses."),
             ("Autre (préciser)", "Noter la réponse en clair, avec les mots du répondant."),
             ("Questions filtrées", "Certaines questions ne s'affichent que pour certains profils : l'outil gère les sauts.")]
    for i, (t, c) in enumerate(types):
        y = 1600000 + i * 1100000
        d.rect(s, 600000, y, 3000000, 900000, MARINE)
        d.texte(s, 750000, y, 2700000, 900000, t, 17, True, "FFFFFF", ancre=MSO_ANCHOR.MIDDLE)
        d.texte(s, 3850000, y, 7700000, 900000, c, 16, False, "1F2937", ancre=MSO_ANCHOR.MIDDLE)
    for sec in quest["sections"]:
        qs = sec["ids"]
        for k in range(0, len(qs), 4):
            s = d.contenu(f"Section {sec['lettre']} · {sec['titre']}", "Section par section" + (" (suite)" if k else ""))
            for j, q in enumerate(qs[k:k + 4]):
                y = 1550000 + j * 1150000
                d.rect(s, 600000, y, 900000, 950000, BLEU)
                d.texte(s, 600000, y, 900000, 950000, q["num"], 18, True, "FFFFFF", PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
                d.texte(s, 1700000, y, 6400000, 950000, q["texte"], 15, True, MARINE, ancre=MSO_ANCHOR.MIDDLE)
                consigne = q.get("consigne") or ("Réservée aux : " + ", ".join(lib.get(c, c) for c in q["profils"]) if q.get("profils") else "")
                if q.get("profils") and q.get("consigne"):
                    consigne += " · Réservée aux : " + ", ".join(lib.get(c, c) for c in q["profils"])
                d.texte(s, 8300000, y, 3300000, 950000, consigne or "—", 12, False, "4B5563", ancre=MSO_ANCHOR.MIDDLE)
    s = d.contenu("Les pièges à éviter", "Le questionnaire")
    d.puces(s, 600000, 1600000, 10900000, 4500000, [
        "Reformuler une question « pour aider » : cela change la mesure. Relire la question à l'identique.",
        "Suggérer une réponse ou lire « Ne sait pas » : cette modalité n'est cochée que si le répondant la donne spontanément.",
        "Cocher plus de 3 réponses à une question à choix multiple.",
        "Interroger une personne hors profil ou hors zone pour « faire le quota ».",
        "Oublier d'envoyer les formulaires le soir : le suivi et les quotas ne sont plus à jour.",
        "Remplir un questionnaire après coup, de mémoire."], 16)

    # Module 4 : outil
    d.intercalaire(4, "L'outil de collecte", outil)
    if fiche.get("outil") == "kobo":
        etapes = [("Installer", "Télécharger KoboCollect sur le Play Store et autoriser l'application."),
                  ("Configurer", "Paramètres › Serveur : saisir l'adresse du serveur et l'identifiant fournis par Datatym."),
                  ("Télécharger", "« Télécharger formulaire » › cocher le baromètre. À refaire si une nouvelle version est annoncée."),
                  ("Saisir", "« Remplir formulaire » › suivre les écrans ; les sauts sont automatiques."),
                  ("Envoyer", "« Envoyer formulaire finalisé » chaque soir, ou dès qu'une connexion est disponible."),
                  ("Hors ligne", "La saisie fonctionne sans internet ; les formulaires restent dans le téléphone jusqu'à l'envoi.")]
    else:
        etapes = [("Installer", "Installer l'application QuestionPro Offline sur la tablette ou le smartphone."),
                  ("Se connecter", "Utiliser l'identifiant enquêteur fourni par Datatym."),
                  ("Télécharger", "Synchroniser pour récupérer le questionnaire du baromètre."),
                  ("Saisir", "Ouvrir l'enquête et suivre les écrans ; les sauts sont automatiques."),
                  ("Envoyer", "Synchroniser chaque soir pour transmettre les réponses."),
                  ("Hors ligne", "La saisie fonctionne sans internet ; synchroniser dès qu'une connexion est disponible.")]
    s = d.contenu("Prise en main en 6 étapes", "L'outil de collecte")
    for i, (t, c) in enumerate(etapes):
        x = 600000 + (i % 3) * 3700000
        y = 1600000 + (i // 3) * 2200000
        d.rect(s, x, y, 3450000, 2000000, "F2F4F7")
        d.texte(s, x + 200000, y + 150000, 3000000, 450000, f"{i + 1}. {t}", 18, True, BLEU)
        d.texte(s, x + 200000, y + 700000, 3050000, 1200000, c, 14, False, "1F2937")

    # Module 5 : quotas
    d.intercalaire(5, "Quotas et calendrier", f"Du {date_fr(jours[0])} au {date_fr(jours[-1])}")
    codes = [pr["code"] for pr in quest["profils"]]
    for k in range(0, len(ech["enqueteurs"]), 10):
        s = d.contenu("Objectifs par enquêteur", "Quotas" + (" (suite)" if k else ""))
        lignes = [[m["nom"], m["zone"]] + [m["par_profil"][c] for c in codes] + [m["objectif"], round(m["objectif"] / len(jours), 1)]
                  for m in ech["enqueteurs"][k:k + 10]]
        d.tableau(s, 600000, 1500000, 10900000, ["Enquêteur", "Zone"] + [lib[c] for c in codes] + ["Total", "Par jour"], lignes, 12)
    s = d.contenu("Suivi et contrôle qualité", "Quotas")
    d.puces(s, 600000, 1600000, 10900000, 4500000, [
        ("Chaque soir :", "envoi des formulaires et point avec le superviseur (réalisé contre objectif)."),
        ("Tableau de bord :", "Datatym suit l'avancement par enquêteur, par zone et par profil en temps réel."),
        ("Quota atteint :", "on n'interroge plus ce profil dans cette zone ; on se concentre sur les quotas restants."),
        ("Contrôle :", "10 % des répondants sont rappelés pour vérifier la réalité et la qualité de l'entretien."),
        ("Rejet :", "un questionnaire trop rapide ou incohérent est annulé et doit être refait.")], 16)

    # Module 6 : pratique
    d.intercalaire(6, "Mise en pratique", "Cas pratiques, jeu de rôle et quiz")
    s = d.contenu("Cas pratiques et jeu de rôle", "Mise en pratique")
    d.puces(s, 600000, 1600000, 10900000, 4500000, [
        ("Cas 1 :", "le répondant est pressé et propose de remplir seul « plus tard ». Que faites-vous ?"),
        ("Cas 2 :", "le répondant demande ce que vous entendez par une question. Comment répondre sans orienter ?"),
        ("Cas 3 :", "votre quota d'un profil est atteint, mais une personne de ce profil veut répondre."),
        ("Cas 4 :", "pas de réseau pendant deux jours : comment protéger vos formulaires ?"),
        ("Jeu de rôle :", "en binômes, un enquêteur et un répondant, passation complète chronométrée.")], 16)
    s = d.contenu("Quiz de fin de formation", "Mise en pratique")
    var_prof = next((q["num"] for q in quest["questions_plates"] if q["id"] == "id_profil"), "A3")
    d.puces(s, 600000, 1600000, 10900000, 4500000, [
        "1. Que faites-vous si le répondant refuse de donner son consentement ?",
        f"2. Que faites-vous si la réponse à {var_prof} est « Autre fonction » ?",
        "3. Combien de réponses au maximum pour une question à choix multiple ?",
        "4. Quand lisez-vous la modalité « Ne sait pas » ?",
        f"5. Quel est votre objectif quotidien moyen ? (≈ {round(fiche['taille'] / len(jours) / ech['nb_enqueteurs'], 1)} questionnaires)",
        "6. À quel moment envoyez-vous vos formulaires ?"], 16)

    s = d.slide(MARINE)
    d.logos(s, sombre=True)
    d.texte(s, 600000, 2500000, 10900000, 900000, "Merci et bonne collecte", 44, True, "FFFFFF", PP_ALIGN.CENTER)
    d.texte(s, 600000, 3500000, 10900000, 600000, "Place aux questions et à la mise en situation", 20, False, "C7D2E3", PP_ALIGN.CENTER)
    cp = d.prs.core_properties
    cp.author = cp.last_modified_by = "DATATYM"
    cp.title, cp.subject = fiche["theme"], "Formation des enquêteurs"
    d.prs.save(chemin)
    return chemin
