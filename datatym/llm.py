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


SYSTEME_ASSISTANT = (
    "Tu es l'assistant de BAROMAKER, la plateforme de Datatym qui produit des baromètres d'opinion et de conjoncture "
    "(cadrage, questionnaire, échantillonnage, collecte, apurement, rapport) en Afrique de l'Ouest et centrale. "
    "Tu aides le chargé d'études : formuler une étude, rédiger ou relire des questions, choisir une taille "
    "d'échantillon, interpréter un résultat. Réponds en français, de façon brève et concrète, avec des listes courtes "
    "quand elles aident. Tu n'inventes jamais de chiffres d'étude : si une donnée manque, dis-le. Tu ne modifies rien "
    "toi-même : tu proposes, et le chargé d'études applique dans la plateforme."
)
# modèles qui acceptent le repli côté serveur en cas de refus
_AVEC_REPLI = {"claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5", "claude-fable-5-1", "claude-fable-5-2"}


def discuter(messages, contexte=""):
    """Réponse de l'assistant à une conversation [{role, content}] ; None si l'IA est inactive.

    Lève RuntimeError avec un message lisible si l'appel échoue."""
    if not disponible():
        return None
    p = charger_parametres()
    modele = p.get("modele") or "claude-opus-5-5"
    systeme = SYSTEME_ASSISTANT + (f"\n\nContexte de l'écran ouvert :\n{contexte}" if contexte else "")
    import anthropic
    client = anthropic.Anthropic(api_key=p["anthropic_api_key"])
    args = dict(model=modele, max_tokens=8000, system=systeme, messages=messages, output_config={"effort": "low"})
    try:
        if modele in _AVEC_REPLI:
            reponse = client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **args)
        else:
            reponse = client.messages.create(**args)
    except anthropic.AuthenticationError:
        raise RuntimeError("Clé API refusée : vérifier la clé dans Paramètres.")
    except anthropic.RateLimitError:
        raise RuntimeError("Trop de demandes en même temps : réessayer dans une minute.")
    except anthropic.APIConnectionError:
        raise RuntimeError("Pas de connexion à Claude : vérifier Internet.")
    except anthropic.APIStatusError as exc:
        raise RuntimeError(f"Claude indisponible ({exc.status_code}).")
    if reponse.stop_reason == "refusal":
        return "Je ne peux pas répondre à cette demande. Reformule-la autrement."
    return "\n".join(b.text for b in reponse.content if b.type == "text").strip()


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
