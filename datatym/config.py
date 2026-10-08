"""Chemins, palette et paramètres locaux de la plateforme."""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROJETS_DIR = BASE_DIR / "projets"
STATIC_DIR = BASE_DIR / "static"
LOGO = STATIC_DIR / "logo_datatym.png"
PARAMS_FILE = BASE_DIR / "parametres.json"

# Couleurs extraites du logo Datatym
MARINE = "19243E"
BLEU = "0087E0"
BLEU_CLAIR = "E6F3FC"
GRIS = "F2F4F7"

POLICE = "Times New Roman"

DATATYM_PRESENTATION = (
    "Datatym est un cabinet spécialisé dans la donnée, les études et l'intelligence "
    "artificielle appliquée à la décision. À travers ses baromètres, Datatym mesure "
    "régulièrement l'opinion, la conjoncture et les pratiques des acteurs économiques "
    "et sociaux, afin de fournir aux décideurs des indicateurs fiables, comparables "
    "dans le temps et directement exploitables."
)

PARAMS_DEFAUT = {
    "anthropic_api_key": "",
    "ia_active": False,
    "modele": "claude-opus-5-5",
    "presentation_datatym": DATATYM_PRESENTATION,
    "contact_recrutement": "recrutement@datatym.com",
}


def charger_parametres():
    params = dict(PARAMS_DEFAUT)
    if PARAMS_FILE.exists():
        try:
            params.update(json.loads(PARAMS_FILE.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    return params


def enregistrer_parametres(maj):
    params = charger_parametres()
    params.update({k: v for k, v in maj.items() if k in PARAMS_DEFAUT})
    PARAMS_FILE.write_text(json.dumps(params, ensure_ascii=False, indent=2), encoding="utf-8")
    return params
