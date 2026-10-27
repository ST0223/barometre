"""Étape 5 — Collecte : import des soumissions et tableau de bord de suivi."""
import hashlib
import json
import random
import re
import urllib.request
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from ..banque import NSP_CODE, code_zone, slug
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
            par_label = {_norm(m["label"]): m["code"] for m in q.get("modalites", [])}
            for v in valeurs:
                val = v.get("value") or {}
                if q["type"] in ("select_one", "select_multiple"):
                    code = par_label.get(_norm(v.get("answerText")))
                    if code is None and _norm(v.get("answerText")).startswith("autre"):
                        code = "autre"
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
    return pd.DataFrame(lignes).fillna(""), ecartees, sorted(ignorees)


def importer_questionpro(projet, quest, env, cle_api, enquete):
    reponses = _lire_questionpro(env, cle_api, enquete)
    df, ecartees, ignorees = convertir_questionpro(reponses, quest)
    enregistrer(projet, df)
    return len(df), ecartees, ignorees


def simuler(projet, quest, ech, taux=1.0, graine=7):
    """Génère des soumissions de test cohérentes avec les quotas et le questionnaire."""
    rnd = random.Random(graine)
    v_enq, v_zone, v_prof = variables_cles(quest)
    jours = [date.fromisoformat(j) for j in ech["jours"]]
    n_jours = max(1, round(len(jours) * taux))
    # biais propres à chaque question pour produire des résultats contrastés
    biais = {q["var"]: [(0.04 if m["code"] == NSP_CODE else rnd.random() ** 1.6 + 0.05) for m in q.get("modalites", [])] for q in quest["questions_plates"]}
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
                        elif q.get("condition_sur"):
                            l[var] = "contact@exemple.com" if l.get(next((x["var"] for x in quest["questions_plates"] if x["id"] == q["condition_sur"][0]), ""), "") == q["condition_sur"][1] else ""
                        elif q["type"] in ("select_one", "select_multiple"):
                            mods = [mm for mm in q["modalites"] if mm["code"] != "autre_hors"]
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
    duree = pd.to_numeric(d.get("duree_minutes", pd.Series(dtype=float)), errors="coerce")
    if duree.notna().any():
        seuil = 0.4 * duree.median()
        d = d[~(duree < seuil)]
    return d


def tableau_de_bord(projet, quest, ech):
    df = lire(projet)
    if df is None or df.empty:
        return None
    v_enq, v_zone, v_prof = variables_cles(quest)
    lib = {pr["code"]: pr["libelle"] for pr in quest["profils"]}
    jours = [date.fromisoformat(j) for j in ech["jours"]]
    total_brut = len(df)
    refus = int((df.get("consentement", pd.Series(dtype=str)).str.lower() == "non").sum())
    hors = int((df.get(v_prof, pd.Series(dtype=str)) == "autre_hors").sum())
    duree = pd.to_numeric(df.get("duree_minutes", pd.Series(dtype=float)), errors="coerce")
    ok_cons = df.get("consentement", pd.Series(["oui"] * len(df))).str.lower().isin(["oui", "1", "yes"])
    med = float(duree[ok_cons].median()) if duree[ok_cons].notna().any() else None
    rapides = int(((duree < 0.4 * med) & ok_cons).sum()) if med else 0
    v = valides(df, quest)
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
    par_zone = [{"zone": z, "objectif": ech["tot_zone"][z], "realise": sum(q["realise"] for q in quotas if q["zone"] == z)} for z in ech["zones"]]
    par_profil = [{"profil": lib[c], "code": c, "objectif": sum(q["objectif"] for q in quotas if q["code"] == c),
                   "realise": sum(q["realise"] for q in quotas if q["code"] == c)} for c in lib]
    for x in par_zone + par_profil:
        x["taux"] = round(100 * x["realise"] / x["objectif"], 1) if x["objectif"] else 0
    par_jour, cr, cp = [], 0, 0
    for i, j in enumerate(jours):
        r = int(sum(1 for d in dates if d == j))
        prev = ech["calendrier"][i]["total"]
        cr += r
        cp += prev
        par_jour.append({"date": j.isoformat(), "realise": r, "prevu": prev, "cumul_realise": cr, "cumul_prevu": cp, "passe": i <= idx_ref})

    incidents = []
    for e in par_enq:
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
        "par_enqueteur": par_enq, "par_zone": par_zone, "par_profil": par_profil, "quotas": quotas, "par_jour": par_jour,
        "incidents": incidents,
        # questions du questionnaire actuel sans colonne dans les données (données importées avant une modification)
        "variables_absentes": [q["var"] for q in quest["questions_plates"] if q["var"] not in df.columns],
        "donnees_perimees": donnees_perimees(projet, quest),
        "nb_variables": len(quest["questions_plates"]),
    }


def generer(projet, precedent=None):
    prec = precedent or {}
    return {"source": prec.get("source", ""), "kobo": prec.get("kobo", {"serveur": "https://kf.kobotoolbox.org", "asset": ""}),
            "stats": prec.get("stats")}
