"""Étape 5 — Collecte : import des soumissions et tableau de bord de suivi."""
import hashlib
import json
import random
import re
import urllib.request
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from ..banque import NSP_CODE, code_zone, slug
from ..outils import repartir
from ..store import dossier

COLONNES_SYSTEME = {"start", "end", "today", "_submission_time", "duree_minutes", "enqueteur", "consentement", "_id", "_uuid"}


def chemin_donnees(projet):
    return dossier(projet["slug"]) / "donnees" / "collecte.csv"


def signature(quest):
    """Empreinte du questionnaire : variables, libellés et modalités. Les variables étant numérotées (c1, c2…),
    leur nom seul ne suffit pas à reconnaître des données collectées avec une version antérieure."""
    contenu = [[q["var"], q.get("texte", ""), [m.get("code") for m in q.get("modalites") or []]] for q in (quest or {}).get("questions_plates", [])]
    return hashlib.sha1(json.dumps(contenu, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def enregistrer(projet, df):
    """Écrit la base des soumissions et l'empreinte du questionnaire avec lequel elle a été collectée."""
    f = chemin_donnees(projet)
    f.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(f, index=False)
    f.with_suffix(".signature").write_text(signature(projet["etapes"]["questionnaire"]["data"]), encoding="utf-8")


def donnees_perimees(projet, quest):
    """Vrai si les données ont été collectées avec un autre questionnaire ; None si on ne le sait pas (import ancien)."""
    f = chemin_donnees(projet).with_suffix(".signature")
    return f.read_text(encoding="utf-8").strip() != signature(quest) if f.exists() else None


def variables_cles(quest):
    v = {q["id"]: q["var"] for q in quest["questions_plates"]}
    return v.get("id_enqueteur"), v.get("id_zone"), v.get("id_profil")


def _nettoyer_colonnes(df):
    df.columns = [str(c).split("/")[-1].strip() for c in df.columns]
    return df.loc[:, ~df.columns.duplicated()]


def lire(projet):
    f = chemin_donnees(projet)
    if not f.exists():
        return None
    return pd.read_csv(f, dtype=str, keep_default_na=False)


def importer_fichier(projet, chemin):
    chemin = str(chemin)
    if chemin.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(chemin, dtype=str).fillna("")
    else:
        df = pd.read_csv(chemin, dtype=str, sep=None, engine="python", keep_default_na=False)
    df = _nettoyer_colonnes(df)
    enregistrer(projet, df)
    return len(df)


ASSET_RE = re.compile(r"\ba[A-Za-z0-9]{21}\b")
# Serveur de l'API selon le domaine du lien de saisie Enketo
SERVEUR_DU_LIEN = {"ee.kobotoolbox.org": "https://kf.kobotoolbox.org", "ee-eu.kobotoolbox.org": "https://eu.kobotoolbox.org"}


def _kobo_json(url, jeton):
    req = urllib.request.Request(url, headers={"Authorization": f"Token {jeton}", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def resoudre_kobo(serveur, jeton, reference):
    """Serveur API et identifiant du projet (asset UID) à partir d'un UID, d'une adresse du projet
    (kf.kobotoolbox.org/#/forms/aXXXX…) ou du lien de saisie Enketo (ee.kobotoolbox.org/x/XXXX)."""
    reference = (reference or "").strip()
    trouve = ASSET_RE.search(reference)
    if trouve:
        return serveur, trouve.group(0)
    lien = re.search(r"https?://([^/]+)/(?:x|single|preview)/([A-Za-z0-9]+)", reference)
    if not lien:
        raise ValueError("Identifiant du formulaire non reconnu : donnez le lien de saisie (ee.kobotoolbox.org/x/…) "
                         "ou l'identifiant du projet (asset UID, commençant par « a »).")
    serveur = SERVEUR_DU_LIEN.get(lien.group(1), serveur)
    code = lien.group(2)
    url = f"{serveur.rstrip('/')}/api/v2/assets/?asset_type=survey&limit=200"
    while url:
        page = _kobo_json(url, jeton)
        for asset in page.get("results", []):
            liens = asset.get("deployment__links")
            if liens is None and asset.get("deployment__active") is not False and asset.get("url"):
                # la liste n'expose pas toujours les liens de déploiement : on lit la fiche du projet
                liens = _kobo_json(asset["url"], jeton).get("deployment__links")
            if any(isinstance(v, str) and v.rstrip("/").endswith("/" + code) for v in (liens or {}).values()):
                return serveur, asset["uid"]
        url = page.get("next")
    raise ValueError(f"Aucun projet de ce compte Kobo ne correspond au lien …/{code}. Vérifiez le jeton API "
                     "(il doit appartenir au compte propriétaire du formulaire).")


def importer_kobo(projet, serveur, jeton, asset):
    """Récupère les soumissions via l'API v2 de KoboToolbox ; renvoie (nombre, serveur, asset UID)."""
    serveur, asset = resoudre_kobo(serveur, jeton, asset)
    res = _kobo_json(f"{serveur.rstrip('/')}/api/v2/assets/{asset}/data.json?limit=30000", jeton)
    df = pd.DataFrame(res.get("results", [])).fillna("").astype(str)  # sans fillna, les champs absents deviendraient « nan »
    df = _nettoyer_colonnes(df)
    enregistrer(projet, df)
    return len(df), serveur, asset


# ------------------------------------------------------------------ QuestionPro
NUM_RE = re.compile(r"^\s*([A-Z]\d+)\s*[.)]\s*")


def _norm(texte):
    """Texte comparable : minuscules, sans accents ni ponctuation."""
    return re.sub(r"[^a-z0-9]+", " ", slug(str(texte or ""), " ", 400)).strip()


MOTS_VIDES = {"et", "de", "des", "du", "la", "le", "les", "l", "d", "a", "au", "aux", "en", "ou", "pour", "par", "sur", "preciser"}


def _mots(texte):
    return [w for w in _norm(texte).split() if w not in MOTS_VIDES]


def correspondance(texte, modalites):
    """Code de la modalité qui correspond à un libellé reçu, malgré les écarts de rédaction :
    ponctuation (« Côte dIvoire »), séparateurs (« Banque et microfinance » / « Banque – microfinance »),
    précision ajoutée (« Directeur général / DGA »), sigle (« Directeur des ressources humaines » / « DRH »)."""
    compact = _norm(texte).replace(" ", "")
    if not compact:
        return None
    mots = set(_mots(texte))
    for m in modalites:
        if _norm(m["label"]).replace(" ", "") == compact:
            return m["code"]
    egaux = [m for m in modalites if set(_mots(m["label"])) == mots]
    if len(egaux) == 1:
        return egaux[0]["code"]
    inclus = [m for m in modalites if _mots(m["label"]) and (set(_mots(m["label"])) <= mots or (mots and mots <= set(_mots(m["label"]))))]
    if len(inclus) == 1:
        return inclus[0]["code"]
    sigle = "".join(w[0] for w in _mots(texte))
    sigles = [m for m in modalites if _norm(m["label"]).replace(" ", "") == sigle or "".join(w[0] for w in _mots(m["label"])) == compact]
    return sigles[0]["code"] if len(sigles) == 1 else None


def _lire_questionpro(env, cle_api, enquete):
    """Toutes les réponses d'une enquête QuestionPro (API v2, pagination comprise)."""
    reponses, page = [], 1
    while True:
        url = f"https://api.questionpro.{env.strip('. ') or 'com'}/a/api/v2/surveys/{enquete}/responses?page={page}&perPage=100"
        req = urllib.request.Request(url, headers={"api-key": cle_api, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            res = json.loads(r.read().decode("utf-8"))
        reponses += res.get("response") or []
        pag = res.get("pagination") or {}
        if page >= int(pag.get("totalPages") or 1):
            return reponses
        page += 1


def convertir_questionpro(reponses, quest):
    """Transforme les réponses QuestionPro en lignes aux noms de variables du questionnaire Datatym.

    Correspondance des questions : code de question (a2) → numéro en tête du texte (« A2. … », tel
    qu'écrit par notre fichier d'import) → texte de la question. Les libellés deviennent des codes.
    """
    plates = quest["questions_plates"]
    par_var = {q["var"]: q for q in plates}
    par_num = {q["num"].upper(): q for q in plates}
    par_texte = {_norm(q["texte"]): q for q in plates}
    v_enq = next((q["var"] for q in plates if q["id"] == "id_enqueteur"), None)
    ignorees = set()

    def question_de(item):
        code = str(item.get("questionCode") or "").strip().lower()
        if code in par_var:
            return par_var[code]
        texte = item.get("questionText") or item.get("questionDescription") or ""
        m = NUM_RE.match(texte)
        if m and m.group(1).upper() in par_num:
            return par_num[m.group(1).upper()]
        sans_num = NUM_RE.sub("", texte)
        return par_texte.get(_norm(sans_num)) or ("consentement" if "accept" in _norm(sans_num) and "particip" in _norm(sans_num) else None)

    lignes, ecartees = [], 0
    reconnues = {}  # variable → [réponses reçues, réponses reconnues parmi les modalités]
    for rep in reponses:
        statut = str(rep.get("responseStatus") or "").lower()
        if statut and statut not in ("completed", "complete", "terminé", "complété"):
            ecartees += 1
            continue
        ligne = {"_id": str(rep.get("responseID", "")), "_source": "questionpro"}
        fin = None
        if rep.get("utctimestamp"):
            t = int(rep["utctimestamp"])
            fin = datetime.fromtimestamp(t / 1000 if t > 10 ** 11 else t, timezone.utc).replace(tzinfo=None)
        elif rep.get("timestamp"):
            fin = pd.to_datetime(rep["timestamp"], errors="coerce")
            fin = None if pd.isna(fin) else fin.to_pydatetime().replace(tzinfo=None)
        duree = int(rep.get("timeTaken") or 0)
        if fin is not None:
            ligne["end"] = ligne["_submission_time"] = fin.isoformat(timespec="seconds")
            ligne["start"] = (fin - timedelta(seconds=duree)).isoformat(timespec="seconds")
        ligne["duree_minutes"] = f"{duree / 60:.1f}" if duree else ""
        for item in rep.get("responseSet") or []:
            q = question_de(item)
            valeurs = item.get("answerValues") or []
            if q == "consentement":
                texte = _norm(valeurs[0].get("answerText")) if valeurs else ""
                ligne["consentement"] = "oui" if texte.startswith("oui") or texte.startswith("j accepte") else "non"
                continue
            if q is None:
                ignorees.add(item.get("questionText") or item.get("questionCode") or str(item.get("questionID")))
                continue
            codes, autre = [], ""
            mods = q.get("modalites", [])
            for v in valeurs:
                val = v.get("value") or {}
                if q["id"] == "id_enqueteur" and q["type"] == "select_one":
                    # collecteur : son code s'il figure au plan, sinon son nom tel que saisi dans l'outil
                    nom = " ".join(re.sub(r"\s*\(.*?\)\s*", " ", str(v.get("answerText") or "")).split())
                    codes.append(correspondance(nom, mods) or nom)
                    continue
                if q["type"] in ("select_one", "select_multiple"):
                    code = correspondance(v.get("answerText"), mods)
                    compte = reconnues.setdefault(q["var"], [0, 0])
                    compte[0] += 1
                    compte[1] += code is not None
                    if code is None and _norm(v.get("answerText")).startswith("autre"):
                        codes_q = {m["code"] for m in mods}
                        code = "autre_hors" if "autre_hors" in codes_q and "autre" not in codes_q else "autre"
                    if code:
                        codes.append(code)
                    if val.get("other"):
                        autre = val["other"]
                else:
                    codes.append(str(val.get("text") or val.get("result") or v.get("answerText") or ""))
            ligne[q["var"]] = " ".join(codes) if q["type"] == "select_multiple" else (codes[0] if codes else "")
            if autre:
                ligne[f"{q['var']}_autre"] = autre
        # enquêteur : question d'identification si présente, sinon variable personnalisée du lien (?custom1=enq3)
        perso = rep.get("customVariables") or {}
        code_enq = ligne.get(v_enq) or str(perso.get("custom1") or rep.get("externalReference") or "").strip().lower()
        if code_enq:
            ligne["enqueteur"] = code_enq
            if v_enq:
                ligne[v_enq] = code_enq
        ligne.setdefault("consentement", "oui")  # une réponse complétée vaut consentement
        lignes.append(ligne)
    df = pd.DataFrame(lignes).fillna("")
    # même code, autre question : si la plupart des réponses ne correspondent à aucune modalité, la question est écartée
    for var, (recues, ok) in reconnues.items():
        if recues >= 5 and ok < 0.6 * recues and var in df:
            df[var] = ""
            ignorees.add(f"{par_var[var]['num']} (réponses ne correspondant pas aux modalités)")
    return df, ecartees, sorted(ignorees)


def _questions_questionpro(env, cle_api, enquete):
    """Structure de l'enquête (codes, réponses dans l'ordre, lignes des grilles)."""
    url = f"https://api.questionpro.{env.strip('. ') or 'com'}/a/api/v2/surveys/{enquete}/questions?page=1&perPage=500"
    req = urllib.request.Request(url, headers={"api-key": cle_api, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8")).get("response") or []


def importer_questionpro(projet, quest, env, cle_api, enquete):
    from .. import indice_hc
    reponses = _lire_questionpro(env, cle_api, enquete)
    df, ecartees, ignorees = convertir_questionpro(reponses, quest)
    enregistrer(projet, df)
    try:
        # réponses brutes (positions) pour l'Indice H&C, calculé sur la structure réelle de l'enquête en ligne
        indice_hc.enregistrer_reponses(projet, reponses, _questions_questionpro(env, cle_api, enquete))
    except Exception:  # l'indice reste sur la synchronisation précédente ; le suivi n'en dépend pas
        pass
    return len(df), ecartees, ignorees


def condition_remplie(q, ligne, par_id):
    """Conditions d'affichage entre questions (clauses reliées par « ou »), évaluées sur les réponses déjà simulées."""
    for cible_id, valeurs, sauf in q.get("conditions") or []:
        cible = par_id.get(cible_id)
        if not cible:
            return True
        reponse = str(ligne.get(cible["var"], ""))
        choisi = any(c in reponse.split() for c in valeurs) if cible["type"] == "select_multiple" else reponse in valeurs
        if reponse and choisi != bool(sauf):
            return True
    return False


def simuler(projet, quest, ech, taux=1.0, graine=7):
    """Génère des soumissions de test cohérentes avec les quotas et le questionnaire."""
    rnd = random.Random(graine)
    v_enq, v_zone, v_prof = variables_cles(quest)
    jours = [date.fromisoformat(j) for j in ech["jours"]]
    n_jours = max(1, round(len(jours) * taux))
    # biais propres à chaque question pour produire des résultats contrastés
    biais = {q["var"]: [(0.04 if m["code"] == NSP_CODE else rnd.random() ** 1.6 + 0.05) for m in q.get("modalites", [])] for q in quest["questions_plates"]}
    par_id = {q["id"]: q for q in quest["questions_plates"]}
    ecart_profil = {pr["code"]: rnd.uniform(-0.25, 0.25) for pr in quest["profils"]}
    lignes = []
    for m in ech["enqueteurs"]:
        vitesse = rnd.uniform(0.75, 1.1)
        for j, jour in enumerate(jours[:n_jours]):
            for code_prof, nb in m["par_jour"][j].items():
                nb_reel = sum(1 for _ in range(nb) if rnd.random() < vitesse)
                for _ in range(nb_reel):
                    debut = datetime.combine(jour, datetime.min.time()) + timedelta(hours=rnd.uniform(8, 17))
                    duree = max(2.0, rnd.gauss(13, 3)) if rnd.random() > 0.04 else rnd.uniform(2, 4)
                    l = {"start": debut.isoformat(timespec="seconds"), "end": (debut + timedelta(minutes=duree)).isoformat(timespec="seconds"),
                         "_submission_time": (debut + timedelta(minutes=duree + rnd.uniform(5, 300))).isoformat(timespec="seconds"),
                         "duree_minutes": f"{duree:.1f}", "consentement": "oui"}
                    for q in quest["questions_plates"]:
                        var = q["var"]
                        if q["id"] == "id_enqueteur":
                            l[var] = m["code"]
                        elif q["id"] == "id_zone":
                            l[var] = code_zone(m["zone"])
                        elif q["id"] == "id_profil":
                            l[var] = code_prof
                        elif q.get("profils") and code_prof not in q["profils"]:
                            l[var] = ""
                        elif q.get("conditions") and not condition_remplie(q, l, par_id):
                            l[var] = ""
                        elif q.get("condition_sur"):
                            l[var] = "contact@exemple.com" if l.get(next((x["var"] for x in quest["questions_plates"] if x["id"] == q["condition_sur"][0]), ""), "") == q["condition_sur"][1] else ""
                        elif q["type"] in ("select_one", "select_multiple"):
                            mods = [mm for mm in q["modalites"] if mm["code"] != "autre_hors" and mm["code"] not in (q.get("exclut") or [])]
                            poids = biais[var][:len(mods)]
                            # décalage de la distribution selon le profil
                            dec = ecart_profil[code_prof]
                            poids = [max(0.01, w * (1 + dec * (len(mods) / 2 - k) / max(len(mods), 1))) for k, w in enumerate(poids)]
                            if q["type"] == "select_one":
                                l[var] = rnd.choices([mm["code"] for mm in mods], poids)[0]
                            else:
                                choix = set(rnd.choices([mm["code"] for mm in mods if mm["code"] != NSP_CODE], poids[:len(mods) - 1] if mods[-1]["code"] == NSP_CODE else poids, k=rnd.randint(1, 3)))
                                l[var] = " ".join(sorted(choix))
                                if "autre" in choix:
                                    l[f"{var}_autre"] = "Autre réponse"
                        elif q["type"] == "text":
                            l[var] = "" if rnd.random() < 0.7 else "Remarque libre du répondant."
                        elif q["type"] == "email":
                            l[var] = "contact@exemple.com" if rnd.random() < 0.4 else ""
                        else:
                            l[var] = ""
                    l["enqueteur"] = m["code"]
                    lignes.append(l)
    # quelques refus de consentement
    for _ in range(max(1, len(lignes) // 40)):
        m = rnd.choice(ech["enqueteurs"])
        jour = rnd.choice(jours[:n_jours])
        t = datetime.combine(jour, datetime.min.time()) + timedelta(hours=rnd.uniform(8, 17))
        lignes.append({"start": t.isoformat(timespec="seconds"), "end": (t + timedelta(minutes=1)).isoformat(timespec="seconds"),
                       "_submission_time": t.isoformat(timespec="seconds"), "duree_minutes": "1.0", "consentement": "non",
                       v_enq: m["code"], "enqueteur": m["code"]})
    df = pd.DataFrame(lignes).fillna("")
    enregistrer(projet, df)
    return len(df)


def _date(x):
    try:
        return datetime.fromisoformat(str(x)[:19]).date()
    except ValueError:
        return None


def valides(df, quest):
    """Questionnaires exploitables : consentement oui, profil dans la cible, durée non suspecte."""
    _, _, v_prof = variables_cles(quest)
    d = df.copy()
    if "consentement" in d:
        d = d[d["consentement"].str.lower().isin(["oui", "1", "yes"])]
    if v_prof in d:
        d = d[d[v_prof] != "autre_hors"]
    for x in quest["questions_plates"]:
        if x.get("exclut") and x["var"] in d:
            d = d[~d[x["var"]].isin(x["exclut"])]
    duree = pd.to_numeric(d.get("duree_minutes", pd.Series(dtype=float)), errors="coerce")
    if duree.notna().any():
        seuil = 0.4 * duree.median()
        d = d[~(duree < seuil)]
    return d


def collecteurs(df, v, quest, ech):
    """Activité de chaque collecteur tel qu'enregistré dans les réponses (code du plan ou nom saisi dans l'outil)."""
    v_enq, v_zone, _ = variables_cles(quest)
    col = "enqueteur" if "enqueteur" in df else v_enq
    if col not in df:
        return []
    noms = {m["code"]: m["nom"] for m in ech["enqueteurs"]}
    q_zone = next((x for x in quest["questions_plates"] if x["id"] == "id_zone"), {})
    lib_zone = {m["code"]: m["label"] for m in q_zone.get("modalites", [])}
    res = []
    for cle, recus in df.groupby(df[col].fillna("").astype(str).str.strip()):
        bons = v[v[col].fillna("").astype(str).str.strip() == cle] if col in v else v.iloc[0:0]
        pays = bons[v_zone].map(lambda c: lib_zone.get(c, c)).value_counts() if v_zone in bons else pd.Series(dtype=int)
        dates = [d for d in (bons["end"] if "end" in bons else pd.Series(dtype=str)).map(_date) if d]
        res.append({"nom": noms.get(cle, cle) or "Non renseigné", "recus": len(recus), "valides": len(bons),
                    "ecartes": len(recus) - len(bons), "pays": [f"{p} ({n})" for p, n in pays.head(3).items() if p],
                    "dernier": max(dates).isoformat() if dates else None})
    return sorted(res, key=lambda x: (-x["valides"], x["nom"]))


def tableau_de_bord(projet, quest, ech):
    df = lire(projet)
    if df is None or df.empty:
        return None
    v_enq, v_zone, v_prof = variables_cles(quest)
    lib = {pr["code"]: pr["libelle"] for pr in quest["profils"]}
    jours = [date.fromisoformat(j) for j in ech["jours"]]
    total_brut = len(df)
    refus = int((df.get("consentement", pd.Series(dtype=str)).str.lower() == "non").sum())
    hors_masque = df.get(v_prof, pd.Series([""] * len(df), index=df.index)) == "autre_hors"
    for x in quest["questions_plates"]:
        if x.get("exclut") and x["var"] in df:
            hors_masque |= df[x["var"]].isin(x["exclut"])
    hors = int(hors_masque.sum())
    duree = pd.to_numeric(df.get("duree_minutes", pd.Series(dtype=float)), errors="coerce")
    ok_cons = df.get("consentement", pd.Series(["oui"] * len(df))).str.lower().isin(["oui", "1", "yes"])
    med = float(duree[ok_cons].median()) if duree[ok_cons].notna().any() else None
    rapides = int(((duree < 0.4 * med) & ok_cons).sum()) if med else 0
    # suivi seul : toute réponse renseignée compte ; contrôle qualité : hors cible et entretiens trop rapides écartés
    controle = projet["etapes"]["collecte"]["data"].get("controle_qualite", True)
    v = valides(df, quest) if controle else df[ok_cons]
    n = len(v)
    dates = v["start"].map(_date) if "start" in v else pd.Series([None] * n)
    dates_toutes = [d for d in dates if d]
    ref = min(max(dates_toutes) if dates_toutes else date.today(), jours[-1])
    idx_ref = max([i for i, j in enumerate(jours) if j <= ref], default=-1)

    par_enq = []
    for i, m in enumerate(ech["enqueteurs"]):
        sel = v[v.get(v_enq, v.get("enqueteur", pd.Series(dtype=str))) == m["code"]] if (v_enq in v or "enqueteur" in v) else v.iloc[0:0]
        prevu = sum(sum(j.values()) for j in m["par_jour"][:idx_ref + 1])
        par_enq.append({"code": m["code"], "nom": m["nom"], "zone": m["zone"], "objectif": m["objectif"], "prevu": prevu,
                        "realise": len(sel), "ecart": len(sel) - prevu,
                        "taux": round(100 * len(sel) / m["objectif"], 1) if m["objectif"] else 0})
    quotas = []
    for z, c, obj in ech["quotas"]:
        r = int(((v.get(v_zone, "") == code_zone(z)) & (v.get(v_prof, "") == c)).sum()) if v_zone in v and v_prof in v else 0
        quotas.append({"zone": z, "profil": lib.get(c, c), "code": c, "objectif": obj, "realise": r, "taux": round(100 * r / obj, 1) if obj else 0})
    # par pays : toutes les réponses comptées du pays, quelle que soit la fonction
    par_zone = [{"zone": z, "code": code_zone(z), "objectif": ech["tot_zone"][z],
                 "realise": int((v.get(v_zone, pd.Series(dtype=str)) == code_zone(z)).sum()) if v_zone in v else 0} for z in ech["zones"]]
    par_profil = [{"profil": lib[c], "code": c, "objectif": sum(q["objectif"] for q in quotas if q["code"] == c),
                   "realise": sum(q["realise"] for q in quotas if q["code"] == c)} for c in lib]
    # secteurs : pas de quota par secteur dans le plan, objectif réparti à parts égales
    q_sect = next((x for x in quest["questions_plates"] if x["id"] == "id_secteur"), None)
    par_secteur = []
    if q_sect:
        objectifs = repartir(projet["fiche"]["taille"], [1] * len(q_sect["modalites"]))
        for m, obj in zip(q_sect["modalites"], objectifs):
            par_secteur.append({"secteur": m["label"], "code": m["code"], "objectif": obj,
                                "realise": int((v.get(q_sect["var"], pd.Series(dtype=str)) == m["code"]).sum())})
    if not controle:
        autres = int((v.get(v_prof, pd.Series(dtype=str)) == "autre_hors").sum())
        if autres:
            par_profil.append({"profil": "Autre fonction", "code": "autre_hors", "objectif": 0, "realise": autres})
    # croisement pays × secteur : objectif du pays réparti à parts égales entre secteurs
    croisement = []
    if q_sect and v_zone:
        for z in ech["zones"]:
            for m, obj in zip(q_sect["modalites"], repartir(ech["tot_zone"][z], [1] * len(q_sect["modalites"]))):
                r = int(((v.get(v_zone, "") == code_zone(z)) & (v.get(q_sect["var"], "") == m["code"])).sum()) if q_sect["var"] in v and v_zone in v else 0
                croisement.append({"zone": z, "secteur": m["label"], "code": m["code"], "objectif": obj, "realise": r,
                                   "taux": round(100 * r / obj, 1) if obj else 0})
    for x in par_zone + par_profil + par_secteur:
        x["taux"] = round(100 * x["realise"] / x["objectif"], 1) if x["objectif"] else 0
    par_collecteur = collecteurs(df, v, quest, ech)
    par_jour, cr, cp = [], 0, 0
    for i, j in enumerate(jours):
        r = int(sum(1 for d in dates if d == j))
        prev = ech["calendrier"][i]["total"]
        cr += r
        cp += prev
        par_jour.append({"date": j.isoformat(), "realise": r, "prevu": prev, "cumul_realise": cr, "cumul_prevu": cp, "passe": i <= idx_ref})

    incidents = []
    # le plan ne sert de référence que si les collecteurs saisis sont ceux du plan (Enq1, Enq2… ou noms définitifs)
    plan_suivi = any(e["realise"] for e in par_enq)
    for e in (par_enq if plan_suivi else []):
        if e["prevu"] and e["realise"] < 0.8 * e["prevu"]:
            incidents.append(f"{e['nom']} ({e['zone']}) : {e['realise']} réalisés pour {e['prevu']} prévus à date ({e['ecart']:+d}).")
    for q in quotas:
        if q["realise"] > q["objectif"] * 1.1 and q["objectif"]:
            incidents.append(f"Quota dépassé : {q['profil']} à {q['zone']} ({q['realise']} pour {q['objectif']}).")
    if rapides:
        incidents.append(f"{rapides} questionnaire(s) d'une durée inférieure à 40 % de la médiane, exclus de l'analyse.")
    if refus:
        incidents.append(f"{refus} refus de participation enregistré(s).")
    objectif = projet["fiche"]["taille"]
    return {
        "maj": datetime.now().isoformat(timespec="seconds"), "reference": ref.isoformat(), "jour_index": idx_ref + 1, "nb_jours": len(jours),
        "objectif": objectif, "realise": n, "taux": round(100 * n / objectif, 1) if objectif else 0,
        "prevu_a_date": par_jour[idx_ref]["cumul_prevu"] if idx_ref >= 0 else 0,
        "brut": total_brut, "refus": refus, "hors_cible": hors, "rapides": rapides,
        "taux_completion": round(100 * n / total_brut, 1) if total_brut else 0,
        "duree_mediane": round(med, 1) if med else None,
        "par_enqueteur": par_enq if plan_suivi else [], "par_zone": par_zone, "par_profil": par_profil, "par_secteur": par_secteur,
        "par_collecteur": par_collecteur, "quotas": quotas, "croisement": croisement, "par_jour": par_jour, "controle_qualite": controle,
        "incidents": incidents,
        # questions du questionnaire actuel sans colonne dans les données (données importées avant une modification)
        "variables_absentes": [q["var"] for q in quest["questions_plates"] if q["var"] not in df.columns],
        "donnees_perimees": donnees_perimees(projet, quest),
        "nb_variables": len(quest["questions_plates"]),
    }


def generer(projet, precedent=None):
    prec = precedent or {}
    data = {"source": prec.get("source", ""), "kobo": prec.get("kobo", {"serveur": "https://kf.kobotoolbox.org", "asset": ""}),
            "stats": prec.get("stats")}
    if prec.get("questionpro"):
        data["questionpro"] = prec["questionpro"]
    if "controle_qualite" in prec:
        data["controle_qualite"] = prec["controle_qualite"]  # enquête et centre de données : la resynchronisation en dépend
    return data


def indicateurs(projet, filtre=""):
    """Indicateurs de la note de cadrage calculés sur les réponses du moment, sans rien enregistrer.

    Base : réponses renseignées (consentement oui), ou valides si le contrôle qualité est activé.
    filtre : « zone:ne », « profil:dsi » ou « secteur:assurance » pour restreindre la base."""
    from .rapport import calculer  # import tardif : rapport dépend déjà de ce module
    quest = projet["etapes"]["questionnaire"]["data"]
    cadrage = projet["etapes"]["cadrage"]["data"]
    df = lire(projet)
    q_de = {q["indicateur"]: q for q in quest["questions_plates"] if q.get("indicateur")}
    par_id = {q["id"]: q for q in quest["questions_plates"]}
    options = {}
    for cle, qid in (("zone", "id_zone"), ("profil", "id_profil"), ("secteur", "id_secteur")):
        if qid in par_id:
            options[cle] = [{"code": m["code"], "label": m["label"]} for m in par_id[qid]["modalites"]]
    if df is None or df.empty:
        return {"n": 0, "options": options, "filtre": filtre, "indicateurs": []}
    controle = projet["etapes"]["collecte"]["data"].get("controle_qualite", True)
    cons = df.get("consentement", pd.Series(["oui"] * len(df), index=df.index)).str.lower().isin(["oui", "1", "yes"])
    base = valides(df, quest) if controle else df[cons]
    if ":" in filtre:
        cle, code = filtre.split(":", 1)
        qid = {"zone": "id_zone", "profil": "id_profil", "secteur": "id_secteur"}.get(cle)
        if qid in par_id and par_id[qid]["var"] in base:
            base = base[base[par_id[qid]["var"]] == code]
    res = []
    for ind in cadrage.get("indicateurs", []):
        if not ind.get("actif", True):
            continue
        if ind["type"] == "indice":
            res.append({"id": ind["id"], "libelle": ind["libelle"], "type": "indice", "bloc": ind.get("bloc", "Synthèse"),
                        "definition": ind.get("definition", ""), "composantes": ind.get("composantes", [])})
            continue
        q = q_de.get(ind["id"])
        if not q:
            continue
        g = calculer(base, ind, q, {})["global"]
        pct = g.get("citations") or g.get("dist") or {}
        res.append({"id": ind["id"], "libelle": ind["libelle"], "type": ind["type"], "bloc": ind.get("bloc", ""),
                    "num": q["num"], "question": q["texte"], "condition": q.get("condition", ""), "n": g.get("n", 0),
                    "solde": g.get("solde"), "moyenne": g.get("moyenne"),
                    "modalites": [{"code": m["code"], "label": m["label"], "pct": pct.get(m["code"], 0)} for m in q["modalites"]
                                  if m["code"] != "autre_hors"]})
    # indice composite : moyenne des soldes de ses composantes ramenée sur 0–100 (comme le rapport)
    soldes = {r["id"]: r.get("solde") for r in res}
    for r in res:
        if r["type"] == "indice" and r["composantes"]:
            vals = [soldes[c] for c in r["composantes"] if soldes.get(c) is not None]
            r["valeur"] = (sum(vals) / len(vals) + 100) / 2 if vals else None
    return {"n": len(base), "options": options, "filtre": filtre, "controle_qualite": controle, "indicateurs": res,
            "indice": indice_entreprises(projet, base, quest)}


def indice_entreprises(projet, base, quest):
    """Indice H&C de chaque entreprise de la base (une réponse = une entreprise), et moyennes par groupe."""
    from .. import indice_hc
    brut = indice_hc.lire_reponses(projet)
    if not brut or base.empty or "_id" not in base:
        return None
    codes_de = {r["id"]: r["codes"] for r in brut["reponses"]}
    par_id = {q["id"]: q for q in quest["questions_plates"]}
    libs = {k: {m["code"]: m["label"] for m in par_id[qid]["modalites"]} for k, qid in
            (("pays", "id_zone"), ("secteur", "id_secteur"), ("fonction", "id_profil")) if qid in par_id}
    libs.setdefault("fonction", {})["autre_hors"] = "Autre fonction"
    var = {k: par_id[qid]["var"] for k, qid in (("pays", "id_zone"), ("secteur", "id_secteur"), ("fonction", "id_profil")) if qid in par_id}
    entreprises = []
    for _, ligne in base.iterrows():
        codes = codes_de.get(str(ligne["_id"]))
        if codes is None:
            continue
        sc = indice_hc.score(codes, brut.get("options_d1", []))
        if sc["indice"] is None:
            continue
        e = {"id": str(ligne["_id"]), "collecteur": str(ligne.get("enqueteur", "")), **sc}
        for k, v in var.items():
            code = str(ligne.get(v, ""))
            e[k] = libs.get(k, {}).get(code, code)
        entreprises.append(e)
    if not entreprises:
        return None
    moyenne = lambda xs: sum(xs) / len(xs) if xs else None

    def groupes(cle):
        res = {}
        for e in entreprises:
            res.setdefault(e.get(cle) or "Non renseigné", []).append(e["indice"])
        return sorted(({"nom": k, "n": len(v), "moyenne": moyenne(v)} for k, v in res.items()), key=lambda x: -x["moyenne"])
    scores = sorted(e["indice"] for e in entreprises)
    return {
        "n": len(entreprises), "moyenne": moyenne(scores), "mediane": scores[len(scores) // 2] if len(scores) % 2 else (scores[len(scores) // 2 - 1] + scores[len(scores) // 2]) / 2,
        "niveau_moyen": indice_hc.niveau(moyenne(scores)),
        "niveaux": [{"niveau": k + 1, "nom": indice_hc.NIVEAUX[k], "description": indice_hc.NIV_DESC[k],
                     "n": sum(1 for e in entreprises if e["niveau"] == k + 1)} for k in range(5)],
        "piliers": [{"k": p["k"], "nom": p["nom"], "poids": p["w"], "description": p["d"],
                     "moyenne": moyenne([e["piliers"][p["k"]] for e in entreprises if e["piliers"][p["k"]] is not None])} for p in indice_hc.PILIERS],
        "par_pays": groupes("pays"), "par_secteur": groupes("secteur"), "par_fonction": groupes("fonction"),
        "entreprises": sorted(entreprises, key=lambda e: -e["indice"]),
    }
