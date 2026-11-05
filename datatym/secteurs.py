"""Catalogue des secteurs et activités (formels et informels) proposé au lancement d'une étude.

Chaque étude n'en retient que quelques-uns : ils deviennent les modalités de la question de secteur. Les grands
domaines servent à publier une lecture fiable quand chaque secteur compte trop peu de répondants.
Les libellés ne contiennent pas de virgule : le champ « secteur » de la fiche les sépare ainsi.
"""
import re

from .banque import slug
from .outils import repartir

AUTRE = "Autre secteur"

CATALOGUE = [
    {"statut": "formel", "libelle": "Secteur formel", "domaines": [
        {"nom": "Primaire", "secteurs": ["Agriculture et élevage", "Pêche et forêt", "Mines et carrières", "Pétrole et gaz"]},
        {"nom": "Industrie et réseaux", "secteurs": ["Agro-industrie et agroalimentaire", "Autres industries manufacturières", "Énergie", "Eau et assainissement", "BTP et immobilier"]},
        {"nom": "Commerce et logistique", "secteurs": ["Commerce et distribution", "Transport et logistique"]},
        {"nom": "Finance et numérique", "secteurs": ["Banque et microfinance", "Assurance", "Télécoms", "Fintech et mobile money", "Informatique et services numériques"]},
        {"nom": "Services", "secteurs": ["Conseil et services aux entreprises", "Hôtellerie-restauration et tourisme", "Médias et communication", "Santé et pharmacie", "Éducation et formation"]},
        {"nom": "Hors secteur marchand", "secteurs": ["Administration et organismes publics", "ONG et organisations internationales"]},
    ]},
    {"statut": "informel", "libelle": "Secteur informel", "domaines": [
        {"nom": "Production informelle", "secteurs": ["Agriculture vivrière et maraîchage", "Élevage et pêche artisanale", "Orpaillage et mines artisanales", "Transformation alimentaire artisanale", "Couture et artisanat", "Menuiserie et soudure"]},
        {"nom": "Commerce informel", "secteurs": ["Boutiques et commerce de détail", "Vente ambulante et marchés"]},
        {"nom": "Services informels", "secteurs": ["Petite restauration et maquis", "Moto-taxi et transport informel", "Coiffure et soins", "Réparation auto et téléphones", "Maçonnerie et petits travaux", "Kiosques de mobile money", "Services domestiques"]},
    ]},
]

_DOMAINE = {slug(s): d["nom"] for g in CATALOGUE for d in g["domaines"] for s in d["secteurs"]}
_INFORMELS = {slug(s) for g in CATALOGUE if g["statut"] == "informel" for d in g["domaines"] for s in d["secteurs"]}


def decouper_secteurs(texte):
    """Sépare sur la virgule, le point-virgule ou le retour à la ligne, jamais sur « et » ni « / »,
    qui font partie des libellés (« Banque et microfinance »)."""
    if isinstance(texte, list):
        return [str(x).strip() for x in texte if str(x).strip()]
    return [m.strip() for m in re.split(r"\s*[,;\n]\s*", str(texte or "")) if m and m.strip()]


def contient_informel(secteurs):
    return any(slug(s) in _INFORMELS for s in secteurs)


def regroupement(modalites):
    """Grand domaine de chaque modalité {code: domaine}, vide quand le regroupement n'apporterait rien :
    secteurs hors catalogue (moins de deux domaines reconnus) ou autant de domaines que de secteurs."""
    res = {m["code"]: _DOMAINE.get(slug(m["label"]), "Autres secteurs") for m in modalites}
    reconnus = {d for d in res.values() if d != "Autres secteurs"}
    return res if len(reconnus) >= 2 and len(set(res.values())) < len(res) else {}


def objectifs_egaux(total, modalites):
    """Objectif réparti à parts égales entre les secteurs ; « Autre secteur » reste une sortie, sans objectif."""
    return repartir(total, [0 if m["label"] == AUTRE else 1 for m in modalites])
