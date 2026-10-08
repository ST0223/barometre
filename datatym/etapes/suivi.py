"""Étape 6 — Note de suivi des enquêtes, produite à la clôture à partir du tableau de bord."""
from datetime import date

from ..charte import chiffres, liste, p, section, tableau
from ..outils import aujourdhui, date_courte, date_fr, nombre, pct

DOCS = {"note_suivi": ("NoteSuivi", "Note de suivi des enquêtes")}


def generer(projet, precedent=None):
    prec = precedent or {}
    return {
        "observations": prec.get("observations") or [
            "Bonne adhésion des répondants au message de consentement.",
            "Difficultés d'accès à certains profils de direction, compensées par des prises de rendez-vous.",
        ],
        "recommandations": prec.get("recommandations") or [
            "Anticiper les prises de rendez-vous avec les profils de direction dès la première semaine.",
            "Renforcer le contrôle de la durée des entretiens dès les premiers jours.",
            "Conserver les mêmes échelles et formulations pour la prochaine édition afin d'assurer la comparabilité.",
        ],
    }


def construire_docs(projet, data, stats):
    fiche = projet["fiche"]
    if not stats:
        return {"note_suivi": {"titre": "Note de suivi des enquêtes", "surtitre": "Baromètre Datatym", "sous_titre": fiche["theme"],
                               "meta": [], "en_tete": "", "sections": [section("vide", "Données manquantes", [
                                   p("Aucune soumission n'a encore été importée à l'étape Collecte.")], source="auto")]}}
    s = stats
    j0, j1 = s["par_jour"][0]["date"], s["par_jour"][-1]["date"]
    ecart = s["realise"] - s["objectif"]
    sections = [
        section("synthese", "1. Synthèse", [
            chiffres([{"valeur": str(s["realise"]), "libelle": f"questionnaires valides sur {s['objectif']} visés"},
                      {"valeur": pct(s["taux"]), "libelle": "taux de réalisation"},
                      {"valeur": pct(s["taux_completion"]), "libelle": "taux de complétion"},
                      {"valeur": f"{nombre(s['duree_mediane'], 1)} min" if s["duree_mediane"] else "–", "libelle": "durée médiane"}]),
            p(f"La collecte s'est déroulée du {date_fr(j0)} au {date_fr(j1)}. **{s['realise']} questionnaires valides** ont été recueillis "
              f"pour un objectif de {s['objectif']}, soit un taux de réalisation de {pct(s['taux'])}"
              + (f" ({ecart:+d} questionnaires)." if ecart else ".")),
            p(f"Sur {s['brut']} formulaires reçus, {s['refus']} correspondent à des refus de participation, {s['hors_cible']} à des répondants hors cible "
              f"et {s['rapides']} à des entretiens trop rapides, écartés de l'analyse."),
        ], source="auto"),
        section("realise", "2. Réalisé contre prévu", [
            tableau(["Zone", "Objectif", "Réalisé", "Taux"], [[z["zone"], z["objectif"], z["realise"], pct(z["taux"])] for z in s["par_zone"]], "Réalisation par zone"),
            tableau(["Profil", "Objectif", "Réalisé", "Taux"], [[x["profil"], x["objectif"], x["realise"], pct(x["taux"])] for x in s["par_profil"]], "Réalisation par profil"),
            tableau(["Zone", "Profil", "Objectif", "Réalisé", "Taux"], [[q["zone"], q["profil"], q["objectif"], q["realise"], pct(q["taux"])] for q in s["quotas"]], "Atteinte des quotas zone × profil", taille=9),
        ], source="auto"),
        section("enqueteurs", "3. Performance des enquêteurs", [
            tableau(["Enquêteur", "Zone", "Objectif", "Réalisé", "Taux", "Écart"],
                    [[e["nom"], e["zone"], e["objectif"], e["realise"], pct(e["taux"]), f"{e['realise'] - e['objectif']:+d}"] for e in s["par_enqueteur"]],
                    "Réalisation par enquêteur", taille=9),
        ], source="auto"),
        section("rythme", "4. Rythme de collecte", [
            tableau(["Jour", "Prévu", "Réalisé", "Cumul prévu", "Cumul réalisé"],
                    [[date_courte(j["date"]), j["prevu"], j["realise"], j["cumul_prevu"], j["cumul_realise"]] for j in s["par_jour"]],
                    "Rythme quotidien", taille=9),
        ], source="auto"),
        section("qualite", "5. Incidents et qualité des données", [
            liste(s["incidents"] or ["Aucun incident majeur relevé."]),
            p("Règles appliquées : exclusion des refus, des hors-cible et des entretiens d'une durée inférieure à 40 % de la médiane ; "
              "contrôle de cohérence des réponses ; rappel de vérification d'un échantillon de répondants.", "note"),
        ], source="auto"),
        section("observations", "6. Observations de terrain", [liste(data.get("observations", []))]),
        section("recommandations", "7. Recommandations pour la prochaine édition", [liste(data.get("recommandations", []))]),
    ]
    return {"note_suivi": {
        "titre": "Note de suivi des enquêtes", "surtitre": "Baromètre Datatym", "sous_titre": fiche["theme"],
        "meta": [f"Collecte du {date_fr(j0)} au {date_fr(j1)}", f"Version du {aujourdhui()}"],
        "en_tete": f"Baromètre {fiche['theme']} — Note de suivi", "sections": sections,
    }}
