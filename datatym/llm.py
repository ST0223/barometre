"""Rédaction assistée par Claude (optionnelle).

Sans clé API ou si l'appel échoue, chaque appelant retombe sur la rédaction
par règles : la plateforme reste entièrement utilisable hors ligne.
"""
import json
import logging

from .config import charger_parametres

log = logging.getLogger(__name__)

SYSTEME = (
    "Tu es chargé d'études senior chez Datatym, cabinet d'études et de données en Afrique de l'Ouest et centrale. "
    "Tu rédiges en français professionnel, simple et précis, sans jargon inutile ni superlatifs. "
    "Tu n'inventes jamais de chiffres : quand une valeur n'est pas fournie, tu écris une formulation qualitative. "
    "Tu réponds uniquement avec le JSON demandé."
)


def disponible():
    p = charger_parametres()
    return bool(p.get("ia_active") and p.get("anthropic_api_key"))


def generer_json(consigne, schema, max_tokens=8000):
    """Renvoie un dict conforme au schéma, ou None si l'IA est indisponible."""
    if not disponible():
        return None
    p = charger_parametres()
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=p["anthropic_api_key"])
        reponse = client.messages.create(
            model=p.get("modele") or "claude-opus-5-5",
            max_tokens=max_tokens,
            system=SYSTEME,
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": schema}},
            messages=[{"role": "user", "content": consigne}],
        )
        if reponse.stop_reason == "refusal":
            log.warning("Rédaction IA refusée : %s", getattr(reponse, "stop_details", None))
            return None
        texte = next((b.text for b in reponse.content if b.type == "text"), "")
        return json.loads(texte)
    except Exception as exc:  # repli silencieux sur la rédaction par règles
        log.warning("Rédaction IA indisponible : %s", exc)
        return None


def tester():
    """Vérifie la clé ; renvoie (ok, message)."""
    p = charger_parametres()
    if not p.get("anthropic_api_key"):
        return False, "Aucune clé API renseignée."
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=p["anthropic_api_key"])
        client.messages.create(model=p.get("modele") or "claude-opus-5-5", max_tokens=64,
                               output_config={"effort": "low"},
                               messages=[{"role": "user", "content": "Réponds OK."}])
        return True, "Connexion à Claude réussie."
    except Exception as exc:
        return False, f"Échec : {exc}"
