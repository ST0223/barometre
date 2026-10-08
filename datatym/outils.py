"""Fonctions communes : dates en français, répartitions, marges d'erreur, formats."""
import math
from datetime import date, datetime, timedelta

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def date_fr(d, jour=False):
    if isinstance(d, str):
        d = date.fromisoformat(d[:10])
    txt = f"{d.day} {MOIS[d.month - 1]} {d.year}"
    return f"{JOURS[d.weekday()]} {txt}" if jour else txt


def date_courte(d):
    if isinstance(d, str):
        d = date.fromisoformat(d[:10])
    return f"{JOURS[d.weekday()][:3]}. {d.day:02d}/{d.month:02d}"


def debut_collecte(fiche):
    """Date de début de collecte : celle de la fiche, sinon le lundi dans trois semaines."""
    if fiche.get("date_debut"):
        try:
            return date.fromisoformat(fiche["date_debut"][:10])
        except ValueError:
            pass
    d = date.today() + timedelta(days=21)
    return d + timedelta(days=(7 - d.weekday()) % 7)


def jours_collecte(debut, duree, sans_dimanche=True):
    """Liste des jours de collecte effectifs sur une durée calendaire."""
    jours = []
    for k in range(int(duree)):
        d = debut + timedelta(days=k)
        if sans_dimanche and d.weekday() == 6:
            continue
        jours.append(d)
    return jours or [debut]


def repartir(total, poids):
    """Répartit un entier selon des poids (méthode du plus fort reste) ; la somme est exacte."""
    poids = [max(float(p or 0), 0) for p in poids]
    s = sum(poids)
    if not poids:
        return []
    if s == 0:
        poids, s = [1.0] * len(poids), float(len(poids))
    bruts = [total * p / s for p in poids]
    base = [int(math.floor(b)) for b in bruts]
    reste = total - sum(base)
    ordre = sorted(range(len(bruts)), key=lambda i: bruts[i] - base[i], reverse=True)
    for i in ordre[:reste]:
        base[i] += 1
    return base


def marge_erreur(n, p=0.5):
    """Marge d'erreur à 95 % en points (cas le plus défavorable par défaut)."""
    if not n or n <= 0:
        return None
    return 1.96 * math.sqrt(p * (1 - p) / n) * 100


def fmt_marge(n):
    m = marge_erreur(n)
    if m is None or n < 30:
        return "non interprétable"
    return f"± {m:.1f} pts".replace(".", ",")


def fcfa(montant):
    if montant is None:
        return ""
    return f"{int(round(montant)):,} FCFA".replace(",", " ")


def nombre(x, dec=0):
    if x is None:
        return "–"
    s = f"{x:,.{dec}f}".replace(",", " ").replace(".", ",")
    return s


def pct(x, dec=0):
    return "–" if x is None else f"{nombre(x, dec)} %"


def solde_txt(x):
    if x is None:
        return "–"
    return ("+" if x > 0 else "") + nombre(x, 0)


def aujourdhui():
    return date_fr(date.today())


def horodatage():
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def propre(obj):
    """Rend un objet sérialisable en JSON strict (types numpy, NaN → None)."""
    if isinstance(obj, dict):
        return {str(k): propre(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [propre(v) for v in obj]
    if hasattr(obj, "item") and not isinstance(obj, (str, bytes)):
        obj = obj.item()
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj
