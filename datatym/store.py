"""Stockage d'un baromètre : un dossier par baromètre (fiche, livrables, versions validées, données)."""
import json
import shutil
from datetime import datetime
from pathlib import Path

from .banque import slug
from .config import PROJETS_DIR

ETAPES = [
    ("cadrage", "Note de cadrage"),
    ("questionnaire", "Questionnaire et formulaires"),
    ("echantillonnage", "Échantillonnage, recrutement et formation"),
    ("methodologie", "Note méthodologique"),
    ("collecte", "Collecte et tableau de bord"),
    ("suivi", "Note de suivi des enquêtes"),
    ("rapport", "Rapport d'analyse"),
]
CLES = [c for c, _ in ETAPES]

CHAMPS_FICHE = ["theme", "objectif", "cible", "zones", "secteur", "taille", "duree", "cout",
                "commanditaire", "date_debut", "outil", "pays"]


def maintenant():
    return datetime.now().isoformat(timespec="seconds")


def dossier(slug_):
    return PROJETS_DIR / slug_


def _fichier(slug_):
    return dossier(slug_) / "projet.json"


def nettoyer_fiche(fiche):
    f = {k: fiche.get(k, "") for k in CHAMPS_FICHE}
    for k in ("theme", "objectif", "cible", "zones", "secteur", "commanditaire", "pays"):
        f[k] = str(f[k] or "").strip()
    for k in ("taille", "duree"):
        try:
            f[k] = max(1, int(float(str(f[k]).replace(" ", "").replace(",", "."))))
        except ValueError:
            f[k] = 0
    try:
        f["cout"] = int(float(str(f["cout"]).replace(" ", "").replace(",", "."))) if str(f["cout"]).strip() else None
    except ValueError:
        f["cout"] = None
    f["outil"] = f["outil"] if f["outil"] in ("kobo", "questionpro") else "kobo"
    f["date_debut"] = str(f["date_debut"] or "").strip()
    return f


def erreurs_fiche(f):
    manquants = []
    for k, lib in (("theme", "Thème"), ("objectif", "Objectif"), ("cible", "Cible"), ("zones", "Champ d'enquête (zones)"),
                   ("taille", "Taille de population"), ("duree", "Durée de l'enquête")):
        if not f.get(k):
            manquants.append(lib)
    return manquants


def etape_vide():
    return {"statut": "a_generer", "version": 0, "data": {}, "docs": {}, "fichiers": [], "maj": None, "valide_le": None}


def creer(fiche):
    PROJETS_DIR.mkdir(parents=True, exist_ok=True)
    f = nettoyer_fiche(fiche)
    base = slug(f["theme"], "-", 50)
    s, n = base, 2
    while dossier(s).exists():
        s, n = f"{base}-{n}", n + 1
    projet = {"slug": s, "cree": maintenant(), "maj": maintenant(), "fiche": f,
              "etapes": {c: etape_vide() for c in CLES}, "journal": []}
    journaliser(projet, "Fiche d'entrée saisie.")
    for sous in ("livrables", "versions", "donnees", "graphiques"):
        (dossier(s) / sous).mkdir(parents=True, exist_ok=True)
    sauver(projet)
    return projet


def charger(slug_):
    f = _fichier(slug_)
    if not f.exists():
        return None
    projet = json.loads(f.read_text(encoding="utf-8"))
    for c in CLES:
        projet["etapes"].setdefault(c, etape_vide())
    return projet


def sauver(projet):
    projet["maj"] = maintenant()
    d = dossier(projet["slug"])
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "projet.json.tmp"
    tmp.write_text(json.dumps(projet, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(_fichier(projet["slug"]))


def supprimer(slug_):
    d = dossier(slug_)
    if d.exists() and d.parent == PROJETS_DIR:
        shutil.rmtree(d)


def lister():
    PROJETS_DIR.mkdir(parents=True, exist_ok=True)
    res = []
    for f in PROJETS_DIR.glob("*/projet.json"):
        try:
            p = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        valides = sum(1 for c in CLES if p["etapes"].get(c, {}).get("statut") == "valide")
        res.append({"slug": p["slug"], "theme": p["fiche"]["theme"], "cible": p["fiche"]["cible"],
                    "zones": p["fiche"]["zones"], "taille": p["fiche"]["taille"], "maj": p["maj"],
                    "valides": valides, "total": len(CLES)})
    return sorted(res, key=lambda r: r["maj"], reverse=True)


def journaliser(projet, message):
    projet.setdefault("journal", []).insert(0, {"date": maintenant(), "message": message})
    del projet["journal"][200:]


def theme_court(fiche):
    mots = [m for m in slug(fiche.get("theme", ""), " ", 80).split() if len(m) > 2][:4]
    return "".join(m.capitalize() for m in mots) or "Barometre"


def nom_fichier(projet, document, version, ext):
    """Règle de nommage : Baromètre_Thème_Document_Version."""
    return f"Barometre_{theme_court(projet['fiche'])}_{document}_v{max(version, 1)}.{ext}"
