/* Plateforme Datatym — interface de production des baromètres */
"use strict";

// ------------------------------------------------------------------ utilitaires
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const md = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
const clone = (o) => JSON.parse(JSON.stringify(o ?? null));
const nf = (x, d = 0) => (x == null ? "–" : Number(x).toLocaleString("fr-FR", { minimumFractionDigits: d, maximumFractionDigits: d }));
const dateFr = (iso) => (iso ? new Date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" }) : "");
const heureFr = (iso) => (iso ? new Date(iso).toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "");
const jourCourt = (iso) => new Date(iso).toLocaleDateString("fr-FR", { weekday: "short", day: "2-digit", month: "2-digit" });

const I = {
  check: '<path d="M20 6 9 17l-5-5"/>', lock: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  play: '<path d="m6 4 14 8-14 8z"/>', refresh: '<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>',
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>', download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/><path d="M12 15V3"/>',
  eye: '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>', alert: '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>', plus: '<path d="M12 5v14M5 12h14"/>', trash: '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/>',
  upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5"/><path d="M12 3v12"/>', users: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8"/>',
  map: '<path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>', target: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
  clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>', coin: '<circle cx="12" cy="12" r="9"/><path d="M14.5 9a2.5 2.5 0 0 0-2.5-1.5c-1.4 0-2.5.8-2.5 2s1 1.7 2.5 2 2.5.9 2.5 2-1.1 2-2.5 2A2.6 2.6 0 0 1 9.5 15M12 6v1.5M12 16.5V18"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>', chart: '<path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/>',
  sparkle: '<path d="M12 3l1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2z"/>', back: '<path d="m15 18-6-6 6-6"/>', unlock: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 7.9-1"/>',
  base: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>', signal: '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M12 1v3M12 20v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M1 12h3M20 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"/>',
};
const ico = (n) => `<svg viewBox="0 0 24 24">${I[n] || ""}</svg>`;

const STATUTS = { verrouille: "Verrouillée", a_generer: "À générer", brouillon: "Brouillon", valide: "Validée", obsolete: "À mettre à jour" };
const ETAPES_INFO = {
  fiche: { court: "Fiche", desc: "Les sept paramètres du baromètre, saisis une seule fois." },
  cadrage: { court: "Cadrage", desc: "Contexte, objectifs, cible, champ, taille visée, durée et surtout la liste des indicateurs recherchés : la base de tout le reste.", produit: ["Note de cadrage (Word, PDF)"] },
  questionnaire: { court: "Questionnaire", desc: "Questions construites à partir des indicateurs validés, adaptées à chaque profil, avec message de consentement et durée estimée.", produit: ["Questionnaire terrain et digital", "Dictionnaire des variables", "XLSForm KoboToolbox", "Import QuestionPro"] },
  echantillonnage: { court: "Échantillonnage", desc: "Quotas zone × profil, répartition par enquêteur, calendrier jour par jour, budget de collecte, note de recrutement et formation.", produit: ["Note d'échantillonnage", "Note de recrutement", "Budget de collecte (interne)", "Calendrier et quotas (Excel)", "PowerPoint de formation", "XLSForm avec enquêteurs"] },
  methodologie: { court: "Méthodologie", desc: "Assemblage automatique des étapes précédentes : méthode, échantillonnage, questionnaire, indicateurs et modes de calcul, outils, traitement.", produit: ["Note méthodologique"] },
  collecte: { court: "Collecte", desc: "Import des soumissions (fichier Kobo/QuestionPro ou API Kobo) et tableau de bord : avancement par enquêteur, zone et quota, écarts au calendrier.", produit: ["Tableau de bord", "Base des soumissions"] },
  suivi: { court: "Note de suivi", desc: "Bilan de la collecte à partir du tableau de bord : réalisé contre prévu, taux de complétion, incidents, qualité des données, bilan financier.", produit: ["Note de suivi des enquêtes"] },
  rapport: { court: "Rapport", desc: "Calcul des indicateurs, graphiques, lecture par profil et par zone, messages clés et enseignements.", produit: ["Rapport d'analyse (Word, PDF)"] },
};
const ORDRE = ["fiche", "cadrage", "questionnaire", "echantillonnage", "methodologie", "collecte", "suivi", "rapport"];
const ONGLETS = {
  cadrage: [["apercu", "Aperçu", "eye"], ["parametres", "Indicateurs", "target"], ["redaction", "Rédaction", "edit"]],
  questionnaire: [["apercu", "Aperçu", "eye"], ["parametres", "Questions", "edit"], ["redaction", "Rédaction", "file"]],
  echantillonnage: [["apercu", "Aperçu", "eye"], ["parametres", "Paramètres", "settings"], ["recrutement", "Recrutement", "users"], ["redaction", "Rédaction", "edit"]],
  methodologie: [["apercu", "Aperçu", "eye"], ["parametres", "Paramètres", "settings"], ["redaction", "Rédaction", "edit"]],
  collecte: [["tableau", "Tableau de bord", "chart"], ["indicateurs", "Indicateurs", "target"], ["import", "Données", "upload"]],
  suivi: [["apercu", "Aperçu", "eye"], ["parametres", "Observations", "edit"], ["bilan", "Bilan financier", "coin"], ["redaction", "Rédaction", "file"]],
  rapport: [["apercu", "Aperçu", "eye"], ["redaction", "Rédaction", "edit"], ["parametres", "Paramètres", "settings"]],
};

const S = { projets: [], projet: null, etape: "fiche", onglet: null, doc: null, types: {}, params: {}, travail: null, docTravail: null, sale: false };

async function api(methode, url, corps, form) {
  const opts = { method: methode, headers: {} };
  if (form) opts.body = form;
  else if (corps !== undefined) { opts.body = JSON.stringify(corps); opts.headers["Content-Type"] = "application/json"; }
  const r = await fetch(url, opts);
  let data = null;
  try { data = await r.json(); } catch { /* réponse vide */ }
  if (!r.ok) throw new Error((data && data.erreur) || `Erreur ${r.status}`);
  return data;
}

function toast(msg, type = "") {
  const t = document.createElement("div");
  t.className = `toast ${type}`;
  t.innerHTML = md(msg);
  $("#toasts").appendChild(t);
  setTimeout(() => t.remove(), type === "erreur" ? 7000 : 3800);
}

function confirmer(titre, texte, bouton = "Confirmer", style = "btn-primaire", annuler = "Annuler") {
  return new Promise((ok) => {
    const m = $("#modale");
    m.innerHTML = `<div class="modale-boite"><h3>${esc(titre)}</h3><p>${md(texte)}</p>
      <div class="actions"><button class="btn" data-r="0">${esc(annuler)}</button><button class="btn ${style}" data-r="1">${esc(bouton)}</button></div></div>`;
    m.hidden = false;
    m.querySelector('[data-r="0"]').focus();
    const fermer = (oui) => { m.hidden = true; document.removeEventListener("keydown", echap); ok(oui); };
    const echap = (e) => { if (e.key === "Escape") fermer(false); };
    document.addEventListener("keydown", echap);
    m.onclick = (e) => {
      const r = e.target.closest("[data-r]");
      if (r || e.target === m) fermer(!!r && r.dataset.r === "1");
    };
  });
}

async function occupe(btn, fn) {
  if (btn) btn.classList.add("charge");
  try { return await fn(); }
  catch (e) { toast(e.message, "erreur"); }
  finally { if (btn) btn.classList.remove("charge"); }
}

// ------------------------------------------------------------------ navigation
const ACCENTS = { fiche: "#7096D1", cadrage: "#0087E0", questionnaire: "#334EAC", echantillonnage: "#00A3C4", methodologie: "#5B86B6", collecte: "#0077B6", suivi: "#03045E", rapport: "#081F5C" };
const MESSAGES_GEN = {
  cadrage: ["Lecture de la fiche d'entrée", "Choix des indicateurs", "Rédaction du contexte et des objectifs", "Calcul de la précision statistique"],
  questionnaire: ["Traduction des indicateurs en questions", "Adaptation aux profils", "Estimation de la durée", "Écriture du XLSForm et du dictionnaire"],
  echantillonnage: ["Calcul des quotas zone × profil", "Répartition entre enquêteurs", "Construction du calendrier", "Génération du PowerPoint de formation"],
  methodologie: ["Consolidation des étapes validées", "Mode de calcul des indicateurs", "Mise en forme de la note"],
  collecte: ["Lecture des soumissions", "Contrôle de la qualité", "Mise à jour du tableau de bord"],
  suivi: ["Bilan réalisé contre prévu", "Relevé des incidents", "Rédaction de la note"],
  rapport: ["Nettoyage de la base", "Calcul des indicateurs", "Tracé des graphiques", "Rédaction des messages clés"],
};

async function chargerListe() {
  S.projets = await api("GET", "/api/projets");
  const c = $("#nav-compte");
  if (c) c.textContent = S.projets.length || "";
}

// Rédaction assistée par Claude (clé API Anthropic) : masquée de l'interface ; passer à true pour la réafficher
const IA_VISIBLE = false;

async function chargerParams() {
  S.params = await api("GET", "/api/parametres");
  const b = $("#badge-ia");
  b.hidden = !IA_VISIBLE;
  const on = S.params.ia_active && S.params.cle_definie;
  b.className = "badge-ia" + (on ? " on" : "");
  b.textContent = on ? "IA active" : "IA inactive";
  b.title = on ? "La rédaction est assistée par Claude" : "Rédaction par règles (activer l'IA dans Paramètres)";
}

function lireRoute() {
  const brut = location.hash.replace(/^#\/?/, "");
  const [chemin, requete] = brut.split("?");
  return { h: chemin.split("/"), params: new URLSearchParams(requete || "") };
}

async function router() {
  if (S.ignorer) { S.ignorer = false; return; }
  if (S.sale && !(await confirmer("Modifications non enregistrées", "Quitter cette vue sans enregistrer vos modifications ?", "Quitter", "btn-danger"))) {
    S.ignorer = true;
    history.back();
    return;
  }
  S.sale = false;
  A.nettoyer();
  const { h, params } = lireRoute();
  const app = $("#app");
  const page = h[0] === "p" ? "projet" : h[0] || "accueil";
  document.querySelectorAll("[data-nav]").forEach((a) => a.classList.toggle("actif", a.dataset.nav === (page === "projet" ? "etudes" : page)));
  $("#nav").classList.toggle("sur-sombre", page === "accueil" || page === "projet");
  const memePage = page === "projet" && S.projet && S.projet.slug === h[1];
  if (!memePage) window.scrollTo(0, 0);
  if (page === "nouveau") { S.projet = null; await chargerListe(); return vueEtude(app, params); }
  if (page === "etudes") { S.projet = null; await chargerListe(); return vueEtudes(app); }
  if (page === "parametres") { S.projet = null; await chargerListe(); return vueParametres(app); }
  if (page === "projet" && h[1]) {
    const avant = S.etape;
    if (!memePage) {
      app.innerHTML = `<div class="chargement"></div>`;
      try { S.projet = await api("GET", `/api/projets/${h[1]}`); }
      catch (e) { toast(e.message, "erreur"); location.hash = "#/etudes"; return; }
    }
    S.etape = h[2] || etapeCourante(S.projet);
    if (!ORDRE.includes(S.etape)) S.etape = "fiche";
    S.sens = memePage ? Math.sign(ORDRE.indexOf(S.etape) - ORDRE.indexOf(avant)) : 0;
    S.onglet = h[3] || null; S.doc = null; S.travail = null; S.docTravail = null;
    chargerListe();
    return vueProjet(!memePage);
  }
  S.projet = null;
  await chargerListe();
  vueAccueil(app);
}

function etapeCourante(p) {
  for (const o of p.ordre) if (p.etapes[o.cle].statut !== "valide") return o.cle;
  return "rapport";
}

function aller(etape) { location.hash = `#/p/${S.projet.slug}/${etape}`; }

function majProjet(p, msg) {
  S.projet = p;
  S.travail = null; S.docTravail = null; S.sale = false; S.sens = 0;
  if (msg) toast(msg, "succes");
  chargerListe();
  vueProjet(false);
}

function cartePro(p, k = 0) {
  const fini = p.valides === p.total;
  return `<a class="carte carte-projet" href="#/p/${p.slug}" data-reveal="haut" data-delai="${k * 90}">
    <span class="cp-reflet"></span>
    <div class="cpj-tete"><span class="sur">${fini ? "Terminé" : `Étape ${Math.min(p.valides + 1, p.total)} sur ${p.total}`}</span>
      <span class="mini-anneau" style="--v:${(100 * p.valides) / p.total}">${p.valides}/${p.total}</span></div>
    <h4>${esc(p.theme)}</h4>
    <div class="meta">${esc(p.cible)} · ${esc(p.zones)} · ${p.taille} répondants</div>
    <div class="pastilles">${Array.from({ length: p.total }, (_, i) => `<i class="${i < p.valides ? "valide" : ""}" style="transition-delay:${i * 60}ms"></i>`).join("")}</div>
    <div class="meta" style="margin-top:8px">Mis à jour le ${heureFr(p.maj)}</div></a>`;
}

// ------------------------------------------------------------------ mes études
function vueEtudes(app) {
  document.body.dataset.page = "etudes";
  const parEtape = ORDRE.slice(1).map((c, k) => [c, S.projets.filter((p) => p.valides < p.total && p.valides === k).length]);
  app.innerHTML = `
    <section class="etudes">
      <div class="etudes-tete">
        <div><span class="sur" data-reveal="haut">Portefeuille</span>
          <h1 class="titre-section-l" data-reveal="haut" data-delai="60">Mes études</h1>
          <p class="aide-l" data-reveal="haut" data-delai="120">${S.projets.length} baromètre(s) · ${S.projets.filter((p) => p.valides === p.total).length} terminé(s)</p></div>
        <div class="etudes-outils" data-reveal="haut" data-delai="160">
          <div class="recherche">${ico("eye")}<input id="filtre" placeholder="Rechercher une étude, une zone, une cible…"></div>
          <a class="btn btn-primaire" href="#/nouveau">${ico("plus")} Nouvelle étude</a>
        </div>
      </div>
      <div class="bande-etapes" data-reveal="haut" data-delai="200">${parEtape.map(([c, n]) => `<div style="--acc:${ACCENTS[c]}"><b data-compte="${n}">0</b><span>${ETAPES_INFO[c].court}</span></div>`).join("")}</div>
      <div class="grille-projets" id="grille-etudes">${S.projets.length ? S.projets.map((p, k) => cartePro(p, k)).join("")
        : `<div class="carte vide" style="grid-column:1/-1">${ico("chart")}<div>Aucune étude pour l'instant.</div><br><a class="btn btn-primaire" href="#/nouveau">${ico("plus")} Lancer une étude</a></div>`}</div>
    </section>`;
  A.reveler(app);
  A.compter(app);
  A.incliner(".carte-projet", 9, app);
  $("#filtre").oninput = (e) => {
    const q = e.target.value.toLowerCase();
    app.querySelectorAll(".carte-projet").forEach((c) => c.classList.toggle("masque", !c.textContent.toLowerCase().includes(q)));
  };
}

// ------------------------------------------------------------------ fiche d'entrée (édition dans le projet)
const CHAMPS = [
  ["theme", "Thème du baromètre", "Climat des affaires dans le commerce formel", true, "Tous les documents"],
  ["objectif", "Objectif", "Mesurer la confiance des entreprises", true, "Cadrage, méthodologie, rapport"],
  ["cible", "Cible", "DG, responsables, vendeurs", true, "Questionnaire, échantillonnage — un profil par virgule"],
  ["zones", "Champ d'étude : pays", "Sénégal, Côte d'Ivoire, Cameroun", true, "Échantillonnage, calendrier — un pays (ou une zone) par virgule"],
  ["secteur", "Champ d'enquête : secteur", "Commerce formel", false, "Plusieurs secteurs séparés par des virgules ajoutent une question"],
  ["taille", "Taille de population souhaitée", "400", true, "Quotas, nombre d'enquêteurs"],
  ["duree", "Durée de l'enquête (jours)", "15", true, "Calendrier de collecte"],
  ["cout", "Plafond budgétaire (FCFA)", "Facultatif", false, "Sert seulement à vérifier que le coût estimé reste dans l'enveloppe"],
];

function formFiche(f = {}) {
  return `<div class="grille-2">
    ${CHAMPS.map(([k, l, ex, obl, aide], i) => `
      <div class="champ ${k === "objectif" || k === "theme" ? "plein" : ""}" data-reveal="haut" data-delai="${i * 40}">
        <label for="f-${k}"><span class="fiche-num">${i + 1}</span>${esc(l)} ${obl ? '<span class="obl">*</span>' : '<span class="ex">facultatif</span>'}</label>
        ${k === "objectif" ? `<textarea class="saisie" id="f-${k}" rows="2" placeholder="${esc(ex)}">${esc(f[k])}</textarea>`
          : `<input class="saisie" id="f-${k}" ${["taille", "duree", "cout"].includes(k) ? 'type="number" min="1"' : ""} placeholder="${esc(ex)}" value="${esc(f[k] ?? "")}">`}
        <span class="aide" style="font-size:12px">${esc(aide)}</span>
      </div>`).join("")}
    <div class="champ"><label for="f-date_debut">Début de la collecte <span class="ex">facultatif</span></label>
      <input class="saisie" type="date" id="f-date_debut" value="${esc(f.date_debut || "")}"></div>
    <div class="champ"><label for="f-outil">Outil de collecte prioritaire</label>
      <select class="saisie" id="f-outil"><option value="kobo" ${f.outil !== "questionpro" ? "selected" : ""}>KoboToolbox</option><option value="questionpro" ${f.outil === "questionpro" ? "selected" : ""}>QuestionPro</option></select></div>
  </div>`;
}

const lireFiche = () => Object.fromEntries([...CHAMPS.map((c) => c[0]), "date_debut", "outil"].map((k) => [k, $(`#f-${k}`).value]));

// ------------------------------------------------------------------ projet
function vueProjet(entree = true) {
  document.body.dataset.page = "projet";
  A.nettoyer();
  const p = S.projet;
  const f = p.fiche;
  const nbVal = p.ordre.filter((o) => p.etapes[o.cle].statut === "valide").length;
  const tot = p.ordre.length;
  const circ = 2 * Math.PI * 30;
  const faits = ORDRE.filter((c, i) => i > 0 && p.etapes[c].statut === "valide").length;
  $("#app").innerHTML = `
    <section class="projet-bandeau ${entree ? "entree" : ""}" style="--acc:${ACCENTS[S.etape]}">
      <div class="liquide calme" aria-hidden="true"><i class="goutte g1"></i><i class="goutte g3"></i></div>
      <div class="grain" aria-hidden="true"></div>
      <div class="pb-contenu">
        <div>
          <a class="fil" href="#/etudes">${ico("back")} Mes études</a>
          <h1>${esc(f.theme)}</h1>
          <div class="puces">
            <span class="puce verre">${ico("users")}${esc(f.cible)}</span>
            <span class="puce verre">${ico("map")}${esc(f.zones)}${f.secteur ? " · " + esc(f.secteur) : ""}</span>
            <span class="puce verre">${ico("target")}${f.taille} répondants</span>
            <span class="puce verre">${ico("clock")}${f.duree} jours</span>
            ${f.cout ? `<span class="puce verre">${ico("coin")}plafond ${nf(f.cout)} FCFA</span>` : ""}
          </div>
        </div>
        <div class="anneau clair"><svg viewBox="0 0 74 74"><circle cx="37" cy="37" r="30" stroke="rgba(255,255,255,.15)" stroke-width="7" fill="none"/>
          <circle class="anneau-arc" cx="37" cy="37" r="30" stroke="${nbVal === tot ? "#34D399" : "#5AC8FA"}" stroke-width="7" fill="none" stroke-linecap="round"
          stroke-dasharray="${(circ * nbVal) / tot} ${circ}"/></svg><div class="val"><div>${nbVal}/${tot}<small>validées</small></div></div></div>
      </div>
      <div class="chaine2" style="--fait:${(faits / (ORDRE.length - 1)) * 100}%">
        <div class="chaine2-rail"><i></i></div>
        ${ORDRE.map((c, i) => maillon(c, i)).join("")}
      </div>
    </section>
    <div id="zone-etape" class="zone-etape ${S.sens > 0 ? "de-droite" : S.sens < 0 ? "de-gauche" : "fondu"}" style="--acc:${ACCENTS[S.etape]}"></div>`;
  document.querySelectorAll(".maillon").forEach((m) => (m.onclick = () => aller(m.dataset.e)));
  S.etape === "fiche" ? panneauFiche() : panneauEtape(S.etape);
}

function maillon(cle, i) {
  const p = S.projet;
  const st = cle === "fiche" ? "valide" : p.etapes[cle].statut;
  const contenu = st === "valide" ? ico("check") : st === "verrouille" ? ico("lock") : st === "obsolete" ? "!" : i;
  return `<button class="maillon ${st} ${S.etape === cle ? "choisi" : ""}" data-e="${cle}" style="--acc:${ACCENTS[cle]};--i:${i}">
    <span class="rond">${contenu}</span><span class="nom">${esc(ETAPES_INFO[cle].court)}</span>
    <span class="etat">${cle === "fiche" ? "Saisie" : STATUTS[st]}</span></button>`;
}

function enteteEtape(num, titre, droite = "") {
  return `<div class="entete-etape"><span class="num-geant" aria-hidden="true">${String(num).padStart(2, "0")}</span>
    <div style="position:relative"><span class="sur">Étape ${num}</span>${titre}</div><div class="actions">${droite}</div></div>`;
}

function panneauFiche() {
  const p = S.projet;
  const engage = p.ordre.some((o) => ["valide", "brouillon"].includes(p.etapes[o.cle].statut));
  $("#zone-etape").innerHTML = `
    <div class="panneau"><div class="carte carte-etape">
      ${enteteEtape(0, "<h2>Fiche d'entrée</h2>")}
      <div class="carte-corps">
        ${engage ? `<div class="bandeau alerte">${ico("alert")}<div>Modifier la fiche marque les documents déjà produits comme <b>à mettre à jour</b>. Les rédactions manuelles sont conservées lors de la régénération.</div></div>` : ""}
        ${formFiche(p.fiche)}
        <div class="pied-form"><button class="btn btn-primaire" id="enr-fiche">${ico("check")} Enregistrer la fiche</button></div>
      </div></div>${colonneDroite()}</div>`;
  const zones = $("#f-zones");
  zones.insertAdjacentHTML("afterend", `<div class="suggestions" style="margin-top:2px">${Object.entries(ESPACES_JS).map(([e, l]) =>
    `<button type="button" data-ajout-espace="${esc(e)}">+ ${esc(e)}${l.length > 1 ? ` (${l.length} pays)` : ""}</button>`).join("")}</div>`);
  document.querySelectorAll("[data-ajout-espace]").forEach((b) => (b.onclick = () => {
    const actuels = zones.value.split(",").map((x) => x.trim()).filter(Boolean);
    ESPACES_JS[b.dataset.ajoutEspace].forEach((pays) => { if (!actuels.includes(pays)) actuels.push(pays); });
    zones.value = actuels.join(", ");
    zones.classList.remove("flash"); void zones.offsetWidth; zones.classList.add("flash");
  }));
  $("#enr-fiche").onclick = (e) => occupe(e.currentTarget, async () => {
    const r = await api("PUT", `/api/projets/${p.slug}/fiche`, lireFiche());
    majProjet(r, "Fiche enregistrée.");
  });
  lierColonne();
  A.reveler($("#zone-etape"));
}

function colonneDroite(e) {
  const p = S.projet;
  const fichiers = e ? e.fichiers || [] : [];
  return `<div class="col-droite">
    ${e ? `<div class="carte"><div class="carte-titre"><h3>Livrables</h3><span class="tag">v${e.version || 1}</span></div>
      ${fichiers.length ? fichiers.map((f) => `
        <div class="livrable"><div class="ico-fichier ${f.type}">${f.type.toUpperCase()}</div>
          <div style="min-width:0"><div class="nom">${esc(f.nom)}</div><div class="fic">${esc(f.fichier)}</div></div>
          <div class="acts">
            <a class="btn btn-fantome btn-petit" title="Télécharger" href="/api/projets/${p.slug}/fichiers/${encodeURIComponent(f.fichier)}">${ico("download")}</a>
            ${f.type === "docx" ? `<a class="btn btn-petit btn-pdf" title="Exporter en PDF" href="/api/projets/${p.slug}/fichiers/${encodeURIComponent(f.fichier)}?format=pdf">PDF</a>` : ""}
          </div></div>`).join("") : `<div class="carte-corps aide">Les fichiers apparaîtront ici après génération.</div>`}
    </div>` : ""}
    <div class="carte"><div class="carte-titre"><h3>Journal</h3></div>
      <div class="journal">${(p.journal || []).slice(0, 30).map((j) => `<div>${esc(j.message)}<time>${heureFr(j.date)}</time></div>`).join("")}</div></div>
    <button class="btn btn-fantome btn-petit btn-danger" id="suppr-projet">${ico("trash")} Supprimer ce baromètre</button>
  </div>`;
}

function lierColonne() {
  document.querySelectorAll(".btn-pdf").forEach((a) => (a.onclick = (ev) => {
    a.classList.add("charge");
    toast("Conversion PDF par Word en cours… (quelques secondes)");
    setTimeout(() => a.classList.remove("charge"), 9000);
  }));
  const s = $("#suppr-projet");
  if (s) s.onclick = async () => {
    if (!(await confirmer("Êtes-vous sûr de vouloir supprimer ce projet ?",
      `**${S.projet.fiche.theme}** : tous ses documents, versions et données seront définitivement supprimés. Cette action est irréversible.`,
      "OUI", "btn-danger", "NON"))) return;
    await api("DELETE", `/api/projets/${S.projet.slug}`);
    S.projet = null;
    toast("Baromètre supprimé.");
    location.hash = "#/";
  };
}

// ------------------------------------------------------------------ panneau d'étape
function panneauEtape(cle) {
  const p = S.projet;
  const e = p.etapes[cle];
  const num = ORDRE.indexOf(cle);
  const st = e.statut;
  const onglets = ONGLETS[cle];
  if (!S.onglet || !onglets.some((o) => o[0] === S.onglet)) S.onglet = onglets[0][0];
  const genere = ["brouillon", "valide", "obsolete"].includes(st);
  let actions = "";
  if (st === "a_generer") actions = `<button class="btn btn-primaire" data-act="generer">${ico("play")} Générer</button>`;
  if (st === "obsolete") actions = `<button class="btn btn-primaire" data-act="generer">${ico("refresh")} Mettre à jour</button>`;
  if (st === "brouillon") actions = `<button class="btn" data-act="regenerer" title="Repartir de zéro">${ico("refresh")} Régénérer</button><button class="btn btn-succes" data-act="valider">${ico("check")} Valider</button>`;
  if (st === "valide") actions = `<button class="btn" data-act="rouvrir">${ico("unlock")} Rouvrir pour corriger</button>`;
  const prec = ORDRE[num - 1];
  const redac = e.data && e.data.redaction;
  const large = genere && ["parametres", "redaction", "recrutement", "tableau"].includes(S.onglet);
  const titre = `<div style="display:flex;align-items:center;gap:10px;margin-top:3px;flex-wrap:wrap"><h2>${esc(e.libelle)}</h2><span class="statut ${st}">${STATUTS[st]}</span>
    ${redac && IA_VISIBLE ? `<span class="tag ${redac === "ia" ? "ia" : ""}">${redac === "ia" ? "Rédigé avec Claude" : "Rédaction par règles"}</span>` : ""}</div>
    ${e.valide_le && st === "valide" ? `<div class="aide" style="font-size:12px;margin-top:2px">Validée le ${heureFr(e.valide_le)}</div>` : ""}`;
  $("#zone-etape").innerHTML = `
    <div class="panneau ${large ? "large" : ""}"><div class="carte carte-etape" id="carte-etape">
      ${enteteEtape(num, titre, actions)}
      ${genere ? `<div class="onglets">${onglets.map(([k, l, ic]) => `<button class="onglet ${S.onglet === k ? "actif" : ""}" data-o="${k}">${ico(ic)}${l}</button>`).join("")}<span class="onglet-curseur" id="onglet-curseur"></span></div>` : ""}
      <div id="contenu-etape" class="contenu-etape">${genere ? "" : introEtape(cle, st, prec)}</div>
    </div>${colonneDroite(genere ? e : null)}</div>`;
  document.querySelectorAll("[data-act]").forEach((b) => (b.onclick = () => agir(b, cle, b.dataset.act)));
  document.querySelectorAll("[data-o]").forEach((b) => (b.onclick = async () => {
    if (S.sale && !(await confirmer("Modifications non enregistrées", "Changer d'onglet sans enregistrer ?", "Continuer", "btn-danger"))) return;
    S.sale = false; S.travail = null; S.docTravail = null;
    S.onglet = b.dataset.o;
    history.replaceState(null, "", `#/p/${p.slug}/${cle}/${S.onglet}`);
    panneauEtape(cle);
  }));
  placerCurseurOnglet();
  lierColonne();
  if (genere) contenuOnglet(cle);
  A.reveler($("#zone-etape"));
}

function placerCurseurOnglet() {
  const c = $("#onglet-curseur"), a = document.querySelector(".onglet.actif");
  if (!c || !a) return;
  c.style.width = `${a.offsetWidth}px`;
  c.style.transform = `translateX(${a.offsetLeft}px)`;
}

function introEtape(cle, st, prec) {
  const info = ETAPES_INFO[cle];
  const p = S.projet;
  const bloque = st === "verrouille";
  return `<div class="carte-corps intro-etape">
    ${bloque ? `<div class="bandeau alerte">${ico("lock")}<div>Cette étape démarre après validation de l'étape « <b>${esc(p.etapes[prec] ? p.etapes[prec].libelle : "")}</b> ». <a href="#/p/${p.slug}/${prec}">Y aller</a></div></div>` : ""}
    <p class="intro-desc">${esc(info.desc)}</p>
    <div class="lib" style="margin:14px 0 10px">Ce qui sera produit</div>
    <div class="produits">${(info.produit || []).map((x, k) => `<div class="produit" data-reveal="haut" data-delai="${k * 80}">${ico("file")}<span>${esc(x)}</span></div>`).join("")}</div>
    ${!bloque ? `<div style="margin-top:24px"><button class="btn btn-primaire btn-l" data-act2="generer">${ico("play")} Générer maintenant</button></div>` : ""}
  </div>`;
}

/** Voile animé sur la carte de l'étape pendant une génération. */
function voileGeneration(cle) {
  const carte = $("#carte-etape");
  if (!carte) return { fin() {} };
  const msgs = MESSAGES_GEN[cle] || ["Génération en cours"];
  const v = document.createElement("div");
  v.className = "voile-gen";
  v.innerHTML = `<div class="vg-scan"></div><div class="vg-boite"><div class="vg-feuille"><i></i><i></i><i></i><i></i><i class="c"></i></div>
    <ul>${msgs.map((m, k) => `<li class="${k ? "" : "encours"}">${esc(m)}</li>`).join("")}</ul></div>`;
  carte.appendChild(v);
  let k = 0;
  const tic = setInterval(() => {
    if (k >= msgs.length - 1) return;
    k++;
    v.querySelectorAll("li").forEach((li, i) => { li.className = i < k ? "fait" : i === k ? "encours" : ""; });
  }, 900);
  return { fin() { clearInterval(tic); v.classList.add("sort"); setTimeout(() => v.remove(), 400); } };
}

function tamponValide(btn) {
  const r = btn.getBoundingClientRect();
  A.eclat(r.left + r.width / 2, r.top + r.height / 2);
  const carte = $("#carte-etape");
  if (!carte) return;
  const t = document.createElement("div");
  t.className = "tampon";
  t.innerHTML = `<span>Validé</span><small>Version archivée</small>`;
  carte.appendChild(t);
}

async function agir(btn, cle, act) {
  const p = S.projet;
  if (S.sale && !(await confirmer("Modifications non enregistrées", "Vos modifications en cours seront perdues. Continuer ?", "Continuer", "btn-danger"))) return;
  if (act === "regenerer" && !(await confirmer("Régénérer depuis zéro ?", "Les rédactions manuelles de cette étape seront remplacées par une nouvelle version générée.", "Régénérer"))) return;
  if (act === "rouvrir") {
    const aval = ORDRE.slice(ORDRE.indexOf(cle) + 1).filter((c) => ["valide", "brouillon"].includes(p.etapes[c].statut));
    if (!(await confirmer("Rouvrir l'étape ?", `L'étape repasse en brouillon (nouvelle version).${aval.length ? ` Les étapes suivantes déjà produites (${aval.length}) devront être mises à jour : vos rédactions manuelles y seront conservées.` : ""}`, "Rouvrir"))) return;
  }
  if (act === "valider" && cle === "questionnaire" && p.etapes.questionnaire.data.alerte_duree) {
    if (!(await confirmer("Durée supérieure à 15 minutes", "Le questionnaire dépasse la durée plafond. Valider quand même ?", "Valider"))) return;
  }
  const voile = ["generer", "regenerer"].includes(act) ? voileGeneration(cle) : null;
  await occupe(btn, async () => {
    try {
      const r = await api("POST", `/api/projets/${p.slug}/etapes/${cle}/${act}`);
      const msg = { generer: "Étape générée.", regenerer: "Étape régénérée.", valider: "Étape validée. Version archivée.", rouvrir: "Étape rouverte." }[act];
      S.projet = r;
      if (voile) voile.fin();
      if (act === "valider") {
        tamponValide(btn);
        toast(msg, "succes");
        chargerListe();
        const suiv = ORDRE[ORDRE.indexOf(cle) + 1];
        await new Promise((ok) => setTimeout(ok, 1100));
        if (suiv) return aller(suiv);
      }
      majProjet(r, msg);
    } catch (err) { if (voile) voile.fin(); throw err; }
  });
}

document.addEventListener("click", (e) => {
  const b = e.target.closest("[data-act2]");
  if (b) agir(b, S.etape, b.dataset.act2);
});

function contenuOnglet(cle) {
  const z = $("#contenu-etape");
  const e = S.projet.etapes[cle];
  if (e.statut === "obsolete") z.insertAdjacentHTML("beforeend", `<div class="carte-corps" style="padding-bottom:0"><div class="bandeau alerte">${ico("alert")}<div>Une étape en amont a changé. Cliquez sur <b>Mettre à jour</b> pour reconstruire cette étape ; vos rédactions manuelles seront conservées.</div></div></div>`);
  const o = S.onglet;
  if (o === "apercu") return ongletApercu(z, e);
  if (o === "redaction") return ongletRedaction(z, cle, e);
  const f = {
    cadrage: editeurIndicateurs, questionnaire: editeurQuestions, echantillonnage: o === "recrutement" ? editeurRecrutement : editeurEchantillonnage,
    methodologie: editeurMethodo, suivi: o === "bilan" ? editeurBilan : editeurSuivi, rapport: editeurRapport, collecte: o === "import" ? ongletImport : o === "indicateurs" ? ongletIndicateurs : ongletTableau,
  }[cle];
  const div = document.createElement("div");
  z.appendChild(div);
  f(div, e, cle);
}

// ------------------------------------------------------------------ aperçu des documents
function ongletApercu(z, e) {
  const noms = Object.keys(e.docs || {});
  if (!noms.length) { z.innerHTML += `<div class="vide">Aucun document.</div>`; return; }
  if (!S.doc || !noms.includes(S.doc)) S.doc = noms[0];
  const libs = Object.fromEntries((e.fichiers || []).filter((f) => f.doc).map((f) => [f.doc, f.nom]));
  z.insertAdjacentHTML("beforeend", `${noms.length > 1 ? `<div class="choix-doc">${noms.map((n) => `<button class="btn btn-petit ${n === S.doc ? "actif" : ""}" data-doc="${n}">${esc(libs[n] || n)}</button>`).join("")}</div>` : ""}
    <div class="zone-apercu">${rendreModele(e.docs[S.doc], e.maj)}</div>`);
  z.querySelectorAll("[data-doc]").forEach((b) => (b.onclick = () => { S.doc = b.dataset.doc; panneauEtape(S.etape); }));
}

function rendreModele(m, maj) {
  const t = Date.parse(maj || "") || 0;
  let n = 0, g = 0;
  const blocs = (b) => {
    if (b.type === "p") return `<p class="${b.style || ""}">${b.style === "gras" ? "<b>" : ""}${md(b.texte)}${b.style === "gras" ? "</b>" : ""}</p>`;
    if (b.type === "liste") { const tag = b.numerotee ? "ol" : "ul"; return `<${tag}>${(b.items || []).map((i) => `<li>${md(i)}</li>`).join("")}</${tag}>`; }
    if (b.type === "tableau") return `${b.legende ? `<div class="leg">Tableau ${++n}. ${esc(b.legende)}</div>` : ""}<table><thead><tr>${b.colonnes.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>${b.lignes.map((l) => `<tr>${l.map((c) => `<td>${md(c)}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
    if (b.type === "chiffres") return `<div class="kpis">${b.items.map((i) => `<div><b>${esc(i.valeur)}</b><span>${esc(i.libelle)}</span></div>`).join("")}</div>`;
    if (b.type === "image") return `<figure><img src="/media/${esc(b.chemin.replace(/\\/g, "/"))}?t=${t}" alt="">${b.legende ? `<figcaption>Graphique ${++g}. ${esc(b.legende)}</figcaption>` : ""}</figure>`;
    return "";
  };
  return `<div class="page ${m.paysage ? "paysage" : ""}">
    <div class="pg-entete"><div class="pg-logos"><img src="/static/logo_datatym.png" alt="Datatym"><img src="/static/logo_agiltym.png" alt="Agiltym"></div><span>${esc(m.en_tete)}</span></div>
    <div class="couv"><div class="st">${esc(m.surtitre)}</div><h1>${esc(m.titre)}</h1><div class="sous">${esc(m.sous_titre)}</div>
      <div class="meta">${(m.meta || []).map(esc).join("<br>")}</div></div>
    ${m.sommaire ? `<h2>Sommaire</h2><ul>${m.sections.filter((s) => s.titre && (s.niveau || 1) === 1).map((s) => `<li>${esc(s.titre)}</li>`).join("")}</ul>` : ""}
    ${m.sections.map((s) => `<div class="${s.source === "auto" ? "sec-auto" : ""}">${s.titre ? `<h${(s.niveau || 1) + 1}>${esc(s.titre)}</h${(s.niveau || 1) + 1}>` : ""}${s.blocs.map(blocs).join("")}</div>`).join("")}
  <div class="pg-pied">${esc(m.pied || "Document interne — Confidentiel")}</div>
  </div>`;
}

// ------------------------------------------------------------------ rédaction (édition libre du document)
function ongletRedaction(z, cle, e) {
  const noms = Object.keys(e.docs || {});
  if (!S.doc || !noms.includes(S.doc)) S.doc = noms[0];
  if (!S.docTravail) S.docTravail = clone(e.docs[S.doc]);
  const m = S.docTravail;
  const libs = Object.fromEntries((e.fichiers || []).filter((f) => f.doc).map((f) => [f.doc, f.nom]));
  const lectureSeule = e.statut === "valide";
  const blocEd = (b, si, bi) => {
    if (b.type === "p") return `<textarea class="saisie" data-s="${si}" data-b="${bi}" data-k="texte" rows="${Math.min(10, Math.max(2, Math.ceil((b.texte || "").length / 110)))}">${esc(b.texte)}</textarea>`;
    if (b.type === "liste") return `<div><div class="aide" style="font-size:11.5px;margin-bottom:3px">Liste à puces — un élément par ligne</div><textarea class="saisie" data-s="${si}" data-b="${bi}" data-k="items" rows="${Math.max(3, (b.items || []).length + 1)}">${esc((b.items || []).join("\n"))}</textarea></div>`;
    if (b.type === "tableau") return `<div class="grille-tab"><table><thead><tr>${b.colonnes.map((c, ci) => `<th><input class="saisie petite" data-s="${si}" data-b="${bi}" data-col="${ci}" value="${esc(c)}"></th>`).join("")}</tr></thead>
      <tbody>${b.lignes.map((l, li) => `<tr>${l.map((c, ci) => `<td><textarea class="saisie petite" rows="1" data-s="${si}" data-b="${bi}" data-l="${li}" data-c="${ci}">${esc(c)}</textarea></td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
    if (b.type === "image") return `<div class="aide">${ico("chart")} Graphique : ${esc(b.legende)}</div>`;
    if (b.type === "chiffres") return `<div class="aide">Chiffres clés : ${b.items.map((i) => esc(i.valeur + " " + i.libelle)).join(" · ")}</div>`;
    return "";
  };
  z.insertAdjacentHTML("beforeend", `
    ${noms.length > 1 ? `<div class="choix-doc">${noms.map((n) => `<button class="btn btn-petit ${n === S.doc ? "actif" : ""}" data-doc="${n}">${esc(libs[n] || n)}</button>`).join("")}</div>` : ""}
    <div class="carte-corps">
      <div class="bandeau info">${ico("info")}<div>Les sections <b>rédigées</b> sont librement modifiables et conservées lors des mises à jour. Les sections <b>calculées</b> sont reconstruites à partir des paramètres : modifiez-les dans l'onglet de paramétrage ou, pour une retouche finale, dans le fichier Word.</div></div>
      ${lectureSeule ? `<div class="bandeau alerte">${ico("lock")}<div>Étape validée : rouvrez-la pour modifier le document.</div></div>` : ""}
      <div class="grille-2" style="margin-bottom:16px">
        <div class="champ"><label>Titre</label><input class="saisie" data-ent="titre" value="${esc(m.titre)}"></div>
        <div class="champ"><label>Sous-titre</label><input class="saisie" data-ent="sous_titre" value="${esc(m.sous_titre)}"></div>
      </div>
      ${m.sections.map((s, si) => s.source === "auto" ? `
        <div class="editeur-sec auto"><header><span style="flex:1;font-weight:700;color:var(--marine)">${esc(s.titre || "(sans titre)")}</span><span class="tag auto">Calculée</span></header></div>` : `
        <div class="editeur-sec"><header><input class="saisie petite" data-s="${si}" data-titre="1" value="${esc(s.titre)}" placeholder="(sans titre)">
          ${s.manuel ? '<span class="tag manuel">Modifiée</span>' : '<span class="tag">Rédigée</span>'}
          <button class="btn btn-fantome btn-petit" data-ajout-p="${si}" title="Ajouter un paragraphe">${ico("plus")}</button></header>
          <div class="corps">${s.blocs.map((b, bi) => blocEd(b, si, bi)).join("")}</div></div>`).join("")}
      ${lectureSeule ? "" : `<div class="pied-form"><button class="btn" id="annuler-doc">Annuler</button><button class="btn btn-primaire" id="enr-doc">${ico("check")} Enregistrer le document</button></div>`}
    </div>`);
  if (lectureSeule) z.querySelectorAll("input,textarea").forEach((i) => (i.disabled = true));
  z.querySelectorAll("[data-doc]").forEach((b) => (b.onclick = () => { S.doc = b.dataset.doc; S.docTravail = null; panneauEtape(cle); }));
  z.oninput = (ev) => {
    const t = ev.target;
    S.sale = true;
    if (t.dataset.ent) { m[t.dataset.ent] = t.value; return; }
    const s = m.sections[+t.dataset.s];
    if (!s) return;
    if (t.dataset.titre) { s.titre = t.value; return; }
    const b = s.blocs[+t.dataset.b];
    if (t.dataset.col !== undefined) b.colonnes[+t.dataset.col] = t.value;
    else if (t.dataset.l !== undefined) b.lignes[+t.dataset.l][+t.dataset.c] = t.value;
    else if (t.dataset.k === "items") b.items = t.value.split("\n");
    else b[t.dataset.k] = t.value;
  };
  z.querySelectorAll("[data-ajout-p]").forEach((b) => (b.onclick = () => {
    m.sections[+b.dataset.ajoutP].blocs.push({ type: "p", texte: "", style: "normal" });
    S.sale = true;
    rafraichirOnglet(cle);
  }));
  const a = $("#annuler-doc");
  if (a) a.onclick = () => { S.docTravail = null; S.sale = false; panneauEtape(cle); };
  const enr = $("#enr-doc");
  if (enr) enr.onclick = () => occupe(enr, async () => {
    m.sections.forEach((s) => s.blocs.forEach((b) => { if (b.type === "liste") b.items = (b.items || []).filter((x) => x.trim()); }));
    const r = await api("PUT", `/api/projets/${S.projet.slug}/etapes/${cle}/docs/${S.doc}`, m);
    S.onglet = "apercu";
    majProjet(r, "Document enregistré, fichiers Word régénérés.");
  });
}

function rafraichirOnglet(cle) {
  const z = $("#contenu-etape");
  z.innerHTML = "";
  contenuOnglet(cle);
}

function piedEnregistrer(z, cle, construire, libelle = "Enregistrer et mettre à jour les documents") {
  const e = S.projet.etapes[cle];
  if (e.statut === "valide") {
    z.querySelectorAll("input,textarea,select,button.btn-ed").forEach((i) => (i.disabled = true));
    z.insertAdjacentHTML("afterbegin", `<div class="bandeau alerte">${ico("lock")}<div>Étape validée : rouvrez-la pour modifier ces paramètres.</div></div>`);
    return;
  }
  z.insertAdjacentHTML("beforeend", `<div class="pied-form"><button class="btn" data-annuler>Annuler</button><button class="btn btn-primaire" data-enr>${ico("check")} ${esc(libelle)}</button></div>`);
  z.querySelector("[data-annuler]").onclick = () => { S.travail = null; S.sale = false; rafraichirOnglet(cle); };
  z.querySelector("[data-enr]").onclick = (ev) => occupe(ev.currentTarget, async () => {
    const r = await api("PUT", `/api/projets/${S.projet.slug}/etapes/${cle}/data`, construire());
    majProjet(r, "Paramètres enregistrés, documents mis à jour.");
  });
}

// ------------------------------------------------------------------ éditeur : indicateurs (cadrage)
const TYPES_IND = { jugement: "Jugement", evolution: "Évolution passée", perspective: "Perspective", satisfaction: "Satisfaction 1–5", intention: "Intention", multiple: "Choix multiple", unique: "Choix unique", numerique: "Numérique" };
const NIVEAUX = { tous: "Tous les profils", direction: "Direction", operationnel: "Opérationnel" };

function editeurIndicateurs(z, e) {
  if (!S.travail) S.travail = clone({ indicateurs: e.data.indicateurs, profils: e.data.profils });
  const W = S.travail;
  const blocs = [...new Set(W.indicateurs.filter((i) => i.type !== "indice").map((i) => i.bloc))];
  const soldes = W.indicateurs.filter((i) => ["jugement", "evolution", "perspective", "satisfaction"].includes(i.type));
  const indice = W.indicateurs.find((i) => i.type === "indice");
  z.className = "carte-corps";
  z.innerHTML = `
    <div class="bandeau info">${ico("info")}<div>Les indicateurs sont la base de tous les livrables. <b>Désactiver un indicateur le retire du questionnaire et du dictionnaire</b> à la prochaine mise à jour de ces étapes.</div></div>
    <div class="lib" style="margin-bottom:8px">Profils de la cible</div>
    <div class="grille-tab" style="margin-bottom:20px"><table><thead><tr><th>Profil</th><th>Code</th><th>Niveau (détermine les questions reçues)</th></tr></thead><tbody>
      ${W.profils.map((p, k) => `<tr><td><input class="saisie petite" data-pr="${k}" data-k="libelle" value="${esc(p.libelle)}"></td><td><code>${esc(p.code)}</code></td>
        <td><select class="saisie petite" data-pr="${k}" data-k="niveau"><option value="direction" ${p.niveau === "direction" ? "selected" : ""}>Direction</option><option value="operationnel" ${p.niveau === "operationnel" ? "selected" : ""}>Opérationnel</option></select></td></tr>`).join("")}
    </tbody></table></div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px"><div class="lib">Indicateurs recherchés</div>
      <button class="btn btn-petit btn-ed" id="aj-ind">${ico("plus")} Ajouter un indicateur</button></div>
    <datalist id="dl-blocs">${blocs.map((b) => `<option value="${esc(b)}">`).join("")}</datalist>
    <div class="grille-tab"><table><thead><tr><th></th><th>Code</th><th>Indicateur</th><th>Type</th><th>Bloc</th><th>Profils</th><th>Formulation de la question / options</th></tr></thead><tbody>
    ${W.indicateurs.map((ind, k) => ind.type === "indice" ? `
      <tr class="${ind.actif === false ? "inactif" : ""}"><td><input type="checkbox" data-i="${k}" data-k="actif" ${ind.actif !== false ? "checked" : ""}></td><td><b>${esc(ind.id)}</b></td>
        <td><input class="saisie petite" data-i="${k}" data-k="libelle" value="${esc(ind.libelle)}" style="min-width:180px"></td><td><span class="tag">Indice 0–100</span></td><td>Synthèse</td><td>Tous</td>
        <td><div class="aide" style="font-size:11.5px;margin-bottom:4px">Composantes de l'indice :</div>${soldes.filter((s) => s.actif !== false).map((s) => `<label class="bascule" style="display:flex;font-size:12px"><input type="checkbox" data-comp="${esc(s.id)}" ${(ind.composantes || []).includes(s.id) ? "checked" : ""}> ${esc(s.id)} ${esc(s.libelle)}</label>`).join("")}</td></tr>` : `
      <tr class="${ind.actif === false ? "inactif" : ""}"><td><input type="checkbox" title="Actif" data-i="${k}" data-k="actif" ${ind.actif !== false ? "checked" : ""}></td><td><b>${esc(ind.id)}</b></td>
        <td><textarea class="saisie petite" rows="2" data-i="${k}" data-k="libelle" style="min-width:190px">${esc(ind.libelle)}</textarea></td>
        <td><select class="saisie petite" data-i="${k}" data-k="type">${Object.entries(TYPES_IND).map(([v, l]) => `<option value="${v}" ${ind.type === v ? "selected" : ""}>${l}</option>`).join("")}</select></td>
        <td><input class="saisie petite" list="dl-blocs" data-i="${k}" data-k="bloc" value="${esc(ind.bloc)}" style="min-width:130px"></td>
        <td><select class="saisie petite" data-i="${k}" data-k="niveau">${Object.entries(NIVEAUX).map(([v, l]) => `<option value="${v}" ${(ind.niveau || "tous") === v ? "selected" : ""}>${l}</option>`).join("")}</select></td>
        <td style="min-width:300px">${["multiple", "unique"].includes(ind.type) ? `
          <input class="saisie petite" data-i="${k}" data-k="question" value="${esc(ind.question || "")}" placeholder="Question posée">
          <textarea class="saisie petite" style="margin-top:4px" rows="3" data-i="${k}" data-k="options" placeholder="Une option par ligne">${esc((ind.options || []).map((o) => (typeof o === "string" ? o : o.label)).join("\n"))}</textarea>` : `
          <input class="saisie petite" data-i="${k}" data-k="objet" value="${esc(ind.objet || "")}" placeholder="Objet mesuré, ex. le niveau d'activité de votre entreprise">
          <input class="saisie petite" style="margin-top:4px" data-i="${k}" data-k="question" value="${esc(ind.question || "")}" placeholder="Formulation libre (facultatif)">`}</td></tr>`).join("")}
    </tbody></table></div>`;
  z.oninput = z.onchange = (ev) => {
    const t = ev.target;
    S.sale = true;
    if (t.dataset.pr !== undefined) { W.profils[+t.dataset.pr][t.dataset.k] = t.value; return; }
    if (t.dataset.comp && indice) {
      const set = new Set(indice.composantes || []);
      t.checked ? set.add(t.dataset.comp) : set.delete(t.dataset.comp);
      indice.composantes = [...set];
      return;
    }
    if (t.dataset.i === undefined) return;
    const ind = W.indicateurs[+t.dataset.i];
    const k = t.dataset.k;
    if (k === "actif") { ind.actif = t.checked; t.closest("tr").classList.toggle("inactif", !t.checked); return; }
    if (k === "options") ind.options = t.value.split("\n").map((x) => x.trim()).filter(Boolean);
    else ind[k] = t.value;
    if (k === "type" && ev.type === "change") {
      if (["multiple", "unique"].includes(ind.type) && !ind.options) ind.options = ["Option 1", "Option 2"];
      ind.definition = "";
      rafraichirOnglet("cadrage");
    }
  };
  $("#aj-ind").onclick = () => {
    const max = Math.max(...W.indicateurs.map((i) => parseInt(i.id.slice(1)) || 0));
    W.indicateurs.push({ id: `I${String(max + 1).padStart(2, "0")}`, libelle: "Nouvel indicateur", type: "jugement", objet: "", bloc: blocs[0] || "Résultats", niveau: "tous", actif: true, sens: "amelioration" });
    S.sale = true;
    rafraichirOnglet("cadrage");
  };
  piedEnregistrer(z, "cadrage", () => ({ indicateurs: W.indicateurs.map((i) => (i.type === "indice" ? i : { ...i, definition: i.definition || "" })), profils: W.profils }));
}

// ------------------------------------------------------------------ éditeur : questions
const TYPES_Q = { select_one: "Choix unique", select_multiple: "Choix multiple", text: "Texte libre", integer: "Nombre", email: "E-mail" };

function editeurQuestions(z, e) {
  const d = e.data;
  if (!S.travail) S.travail = clone({ sections: d.sections, consentement: d.consentement });
  const W = S.travail;
  const profils = d.profils;
  const libP = Object.fromEntries(profils.map((p) => [p.code, p.libelle]));
  const jauge = (titre, mins) => Object.entries(mins).map(([c, v]) => `<div class="jauge"><div class="t">${esc(titre)} · ${esc(libP[c] || c)}</div><div class="v">${nf(v, 1)} min</div>
    <div class="b"><i class="${v > 15 ? "trop" : ""}" style="width:${Math.min(100, (v / 15) * 100)}%"></i></div></div>`).join("");
  z.className = "carte-corps";
  z.innerHTML = `
    ${d.alerte_duree ? `<div class="bandeau alerte">${ico("alert")}<div>La version terrain dépasse le plafond de 15 minutes pour au moins un profil. Désactivez des indicateurs dans le cadrage ou rendez des questions facultatives.</div></div>` : ""}
    ${(() => {
      const qs = W.sections.flatMap((s) => s.ids);
      const ind = qs.filter((q) => q.indicateur).length;
      return `<p class="aide" style="margin:0 0 12px">${qs.length} questions : <b>${ind} alimentent un indicateur</b>, ${qs.length - ind} servent à l'identification (quotas, lecture par profil) et à la clôture. Une question qui ne nourrit ni un indicateur ni un quota allonge l'entretien sans rien apporter au rapport.</p>`;
    })()}
    <div class="lib" style="margin-bottom:8px">Durée de remplissage estimée (plafond : 15 minutes)</div>
    <div class="jauges" style="margin-bottom:18px">${jauge("Terrain", d.duree_terrain)}${jauge("Digital", d.duree_digital)}</div>
    <div class="champ" style="margin-bottom:8px"><label>Message de consentement</label><textarea class="saisie" id="consent" rows="4">${esc(W.consentement)}</textarea></div>
    ${W.sections.map((s, si) => `
      <div class="sec-q"><h4><span>${esc(s.lettre)}</span>${esc(s.titre)}</h4>
        <div class="liste-q">${s.ids.map((q, qi) => `
          <div class="carte-q"><div class="num">${esc(q.num)}</div><div class="lignes">
            <input class="saisie" data-s="${si}" data-q="${qi}" data-k="texte" value="${esc(q.texte)}" style="font-weight:600">
            <div class="meta-q"><code>${esc(q.var)}</code>
              ${q.indicateur ? `<span class="tag">Indicateur ${esc(q.indicateur)}</span>` : q.ajoutee ? '<span class="tag manuel">Ajoutée</span>' : '<span class="tag">Identification</span>'}
              ${q.modifiee ? '<span class="tag manuel">Modifiée</span>' : ""}
              <select class="saisie petite" style="width:auto" data-s="${si}" data-q="${qi}" data-k="type">${Object.entries(TYPES_Q).map(([v, l]) => `<option value="${v}" ${q.type === v ? "selected" : ""}>${l}</option>`).join("")}</select>
              <label class="bascule"><input type="checkbox" data-s="${si}" data-q="${qi}" data-k="obligatoire" ${q.obligatoire !== false ? "checked" : ""}> Obligatoire</label>
              ${q.condition ? `<span>${ico("info")} ${esc(q.condition)}</span>` : ""}
              ${q.ajoutee ? `<button class="btn btn-fantome btn-petit btn-danger btn-ed" data-suppr="${si}:${qi}">${ico("trash")}</button>` : ""}
            </div>
            ${["select_one", "select_multiple"].includes(q.type) ? `<textarea class="saisie petite" rows="${Math.min(9, (q.modalites || []).length + 1)}" data-s="${si}" data-q="${qi}" data-k="modalites" title="code = libellé, une modalité par ligne">${esc((q.modalites || []).map((m) => `${m.code} = ${m.label}`).join("\n"))}</textarea>` : ""}
            <input class="saisie petite" data-s="${si}" data-q="${qi}" data-k="consigne" value="${esc(q.consigne || "")}" placeholder="Consigne pour l'enquêteur (facultatif)">
            ${!q.fixe ? `<div class="meta-q">Posée à : ${profils.map((p) => `<label class="bascule"><input type="checkbox" data-s="${si}" data-q="${qi}" data-prof="${p.code}" ${!q.profils || q.profils.includes(p.code) ? "checked" : ""}> ${esc(p.libelle)}</label>`).join("")}</div>` : ""}
          </div></div>`).join("")}
        </div>
        ${s.lettre !== "A" && si < W.sections.length - 1 ? `<button class="btn btn-petit btn-fantome btn-ed" style="margin-top:8px" data-ajq="${si}">${ico("plus")} Ajouter une question dans « ${esc(s.titre)} »</button>` : ""}
      </div>`).join("")}`;
  z.oninput = z.onchange = (ev) => {
    const t = ev.target;
    S.sale = true;
    if (t.id === "consent") { W.consentement = t.value; W.consentModifie = true; return; }
    if (t.dataset.s === undefined) return;
    const q = W.sections[+t.dataset.s].ids[+t.dataset.q];
    q.modifiee = true;
    if (t.dataset.prof) {
      let set = new Set(q.profils || profils.map((p) => p.code));
      t.checked ? set.add(t.dataset.prof) : set.delete(t.dataset.prof);
      q.profils = set.size === profils.length ? null : [...set];
      return;
    }
    const k = t.dataset.k;
    if (k === "obligatoire") q.obligatoire = t.checked;
    else if (k === "modalites") q.modalites = t.value.split("\n").filter((l) => l.trim()).map((l) => {
      const [code, ...lab] = l.split("=");
      return lab.length ? { code: code.trim().toLowerCase().replace(/[^a-z0-9_]/g, "_"), label: lab.join("=").trim() } : { code: l.trim().toLowerCase().normalize("NFD").replace(/[^a-z0-9]+/g, "_").slice(0, 18), label: l.trim() };
    });
    else q[k] = t.value;
    if (k === "type" && ev.type === "change" && ["select_one", "select_multiple"].includes(q.type) && !(q.modalites || []).length) q.modalites = [{ code: "oui", label: "Oui" }, { code: "non", label: "Non" }];
    if (k === "type" && ev.type === "change") rafraichirOnglet("questionnaire");
  };
  z.querySelectorAll("[data-ajq]").forEach((b) => (b.onclick = () => {
    const s = W.sections[+b.dataset.ajq];
    s.ids.push({ id: `aj_${Date.now()}`, texte: "Nouvelle question", type: "select_one", modalites: [{ code: "oui", label: "Oui" }, { code: "non", label: "Non" }],
      ajoutee: true, modifiee: true, bloc: s.titre, obligatoire: true, profils: null, consigne: "", num: "…", var: "…" });
    S.sale = true;
    rafraichirOnglet("questionnaire");
  }));
  z.querySelectorAll("[data-suppr]").forEach((b) => (b.onclick = () => {
    const [si, qi] = b.dataset.suppr.split(":").map(Number);
    W.sections[si].ids.splice(qi, 1);
    S.sale = true;
    rafraichirOnglet("questionnaire");
  }));
  piedEnregistrer(z, "questionnaire", () => {
    const corps = { sections: W.sections };
    if (W.consentModifie) corps.consentement = W.consentement;
    return corps;
  });
}

// ------------------------------------------------------------------ éditeur : échantillonnage
function editeurEchantillonnage(z, e) {
  const d = e.data;
  if (!S.travail) S.travail = clone({ params: d.params, recrutement: d.recrutement });
  const P = S.travail.params;
  const libP = Object.fromEntries(d.profils.map((p) => [p.code, p.libelle]));
  const q = Object.fromEntries(d.quotas.map(([z_, c, v]) => [`${z_}|${c}`, v]));
  z.className = "carte-corps";
  z.innerHTML = `
    <div class="kpis-tb" style="grid-template-columns:repeat(4,1fr)">
      ${[["Questionnaires", S.projet.fiche.taille], ["Enquêteurs", d.nb_enqueteurs], ["Jours de collecte", d.jours.length], ["Par jour (total)", nf(S.projet.fiche.taille / d.jours.length, 0)]]
        .map(([t, v]) => `<div class="carte kpi"><div class="t">${t}</div><div class="v">${v}</div></div>`).join("")}
    </div>
    <div class="grille-3" style="margin-bottom:18px">
      <div class="champ"><label>Questionnaires par enquêteur et par jour</label><input class="saisie" type="number" step="0.5" min="1" data-p="rendement" value="${P.rendement}"></div>
      <div class="champ"><label>Taux de réalisation attendu</label><input class="saisie" type="number" step="0.05" min="0.3" max="1" data-p="marge" value="${P.marge}"><span class="aide" style="font-size:12px">0,9 = marge de 10 % pour les refus</span></div>
      <div class="champ"><label>Début de la collecte</label><input class="saisie" type="date" data-p="date_debut" value="${P.date_debut}"></div>
      <div class="champ"><label class="bascule" style="margin-top:26px"><input type="checkbox" data-p="sans_dimanche" ${P.sans_dimanche ? "checked" : ""}> Pas de collecte le dimanche</label></div>
      <div class="champ plein"><label>Liste réelle des enquêteurs <span class="ex">un nom par ligne — vide : Enq1, Enq2…</span></label>
        <textarea class="saisie" rows="3" data-p="noms_enqueteurs" placeholder="Awa Diop&#10;Moussa Ndiaye">${esc((P.noms_enqueteurs || []).join("\n"))}</textarea></div>
    </div>
    <div class="grille-2" style="margin-bottom:18px">
      <div><div class="lib" style="margin-bottom:6px">Poids des zones</div>${Object.entries(P.poids_zones).map(([k, v]) => `<div style="display:flex;gap:8px;align-items:center;margin-bottom:6px"><span style="flex:1">${esc(k)}</span><input class="saisie petite" style="width:90px" type="number" min="0" step="0.5" data-pz="${esc(k)}" value="${v}"></div>`).join("")}</div>
      <div><div class="lib" style="margin-bottom:6px">Poids des profils</div>${Object.entries(P.poids_profils).map(([k, v]) => `<div style="display:flex;gap:8px;align-items:center;margin-bottom:6px"><span style="flex:1">${esc(libP[k] || k)}</span><input class="saisie petite" style="width:90px" type="number" min="0" step="0.5" data-pp="${esc(k)}" value="${v}"></div>`).join("")}</div>
    </div>
    <div class="lib" style="margin-bottom:6px">Quotas calculés</div>
    <div class="grille-tab" style="margin-bottom:18px"><table><thead><tr><th>Zone</th>${d.profils.map((p) => `<th>${esc(p.libelle)}</th>`).join("")}<th>Total</th><th>Enquêteurs</th></tr></thead><tbody>
      ${d.zones.map((z_) => `<tr><td><b>${esc(z_)}</b></td>${d.profils.map((p) => `<td>${q[`${z_}|${p.code}`]}</td>`).join("")}<td><b>${d.tot_zone[z_]}</b></td><td>${d.enqueteurs.filter((m) => m.zone === z_).map((m) => esc(m.nom)).join(", ")}</td></tr>`).join("")}
    </tbody></table></div>
    ${blocBudget(d, P)}`;
  z.oninput = z.onchange = (ev) => {
    const t = ev.target;
    S.sale = true;
    if (t.dataset.p) {
      const k = t.dataset.p;
      P[k] = k === "sans_dimanche" ? t.checked : k === "noms_enqueteurs" ? t.value.split("\n").map((x) => x.trim()).filter(Boolean) : ["rendement", "marge"].includes(k) ? Number(t.value) : t.value;
    } else if (t.dataset.pz) P.poids_zones[t.dataset.pz] = Number(t.value);
    else if (t.dataset.pp) P.poids_profils[t.dataset.pp] = Number(t.value);
    else if (t.dataset.cu !== undefined) P.couts[+t.dataset.cu].valeur = Number(t.value);
    else if (t.dataset.hyp) P.hypotheses[t.dataset.hyp] = Number(t.value);
  };
  piedEnregistrer(z, "echantillonnage", () => ({ params: P }), "Recalculer et mettre à jour les documents");
}

const HYPOTHESES_BUDGET = [["jours_formation", "Jours de formation"], ["enq_par_superviseur", "Enquêteurs par superviseur"], ["part_rappels", "Rappels de contrôle (%)"],
  ["jours_preparation", "Jours de conception et coordination"], ["jours_analyse", "Jours de traitement et d'analyse"], ["imprevus", "Imprévus (% du sous-total)"]];

/** Coûts unitaires, hypothèses et budget calculé (document interne « Budget de collecte »). */
function blocBudget(d, P) {
  const b = d.budget;
  const est = S.projet.etapes.cadrage.data.estimation;
  const plafond = S.projet.fiche.cout;
  // étude créée avant le budget de collecte : il apparaît à la prochaine mise à jour de l'étape
  if (!P.couts) return `<div class="bandeau info">${ico("info")}<div>Le budget de collecte sera calculé à la prochaine mise à jour de cette étape (bouton <b>Mettre à jour</b>, ou rouvrir puis régénérer).</div></div>`;
  return `<div class="lib" style="margin-bottom:6px">Budget de collecte <span class="ex">document interne, recalculé à partir du plan</span></div>
    ${b ? `<div class="kpis-tb" style="grid-template-columns:repeat(4,1fr)">
      ${[["Coût de revient", `${nf(b.total)} FCFA`], ["Par questionnaire validé", `${nf(b.par_questionnaire)} FCFA`], ["Part du terrain", `${nf(b.part_terrain)} %`], ["100 questionnaires de plus", `${nf(b.marginal_100)} FCFA`]]
        .map(([t, v]) => `<div class="carte kpi"><div class="t">${t}</div><div class="v" style="font-size:20px">${v}</div></div>`).join("")}
    </div>
    ${est ? `<p class="aide">Estimation du cadrage : ${nf(est.bas)} à ${nf(est.haut)} FCFA${plafond ? ` · plafond : ${nf(plafond)} FCFA${b.total > plafond ? ` <b style="color:var(--rouge)">dépassé de ${nf(b.total - plafond)} FCFA</b>` : ""}` : ""}</p>` : ""}` : ""}
    <div class="grille-2" style="margin-bottom:18px;align-items:start">
      <div class="grille-tab"><table><thead><tr><th>Coût unitaire</th><th>Unité</th><th>FCFA</th></tr></thead><tbody>
        ${P.couts.map((c, k) => `<tr><td>${esc(c.libelle)}</td><td class="aide">${esc(c.unite)}</td><td><input class="saisie petite" style="width:110px" type="number" min="0" step="500" data-cu="${k}" value="${c.valeur}"></td></tr>`).join("")}
      </tbody></table></div>
      <div>${HYPOTHESES_BUDGET.map(([k, l]) => `<div style="display:flex;gap:8px;align-items:center;margin-bottom:6px"><span style="flex:1">${esc(l)}</span><input class="saisie petite" style="width:90px" type="number" min="0" step="1" data-hyp="${k}" value="${P.hypotheses[k]}"></div>`).join("")}</div>
    </div>
    ${b ? `<div class="grille-tab"><table><thead><tr><th>Poste</th><th>Base de calcul</th><th>Montant</th></tr></thead><tbody>
      ${b.lignes.map((l) => `<tr><td>${esc(l.poste)}</td><td class="aide">${esc(l.base)}</td><td>${nf(l.montant)} FCFA</td></tr>`).join("")}
      <tr><td>Imprévus</td><td class="aide">${nf(b.taux_imprevus)} % du sous-total</td><td>${nf(b.imprevus)} FCFA</td></tr>
      <tr><td><b>Total</b></td><td></td><td><b>${nf(b.total)} FCFA</b></td></tr>
    </tbody></table></div>` : ""}`;
}

/** Dépenses réelles par poste, comparées au budget de collecte. */
function editeurBilan(z) {
  const b = S.projet.etapes.echantillonnage.data.budget;
  z.className = "carte-corps";
  if (!b) {
    z.innerHTML = `<div class="bandeau info">${ico("info")}<div>Aucun budget de collecte : mettez à jour l'étape Échantillonnage pour le calculer.</div></div>`;
    return;
  }
  if (!S.travail) S.travail = clone({ depenses: S.projet.etapes.suivi.data.depenses || {} });
  const D = S.travail.depenses;
  const postes = [...b.lignes, { cle: "imprevus", poste: "Imprévus", montant: b.imprevus }];
  const saisi = (c) => D[c] !== undefined && D[c] !== "";
  z.innerHTML = `
    <div class="bandeau info">${ico("info")}<div>Saisissez les dépenses réellement engagées, poste par poste. Le bilan financier de la note de suivi compare le réalisé au budget de collecte ; un poste laissé vide n'entre pas dans le calcul.</div></div>
    <div class="grille-tab"><table><thead><tr><th>Poste</th><th>Prévu</th><th>Réalisé (FCFA)</th><th>Écart</th></tr></thead><tbody>
      ${postes.map((p) => `<tr><td>${esc(p.poste)}</td><td>${nf(p.montant)} FCFA</td>
        <td><input class="saisie petite" style="width:130px" type="number" min="0" step="1000" data-dep="${p.cle}" value="${D[p.cle] ?? ""}" placeholder="non saisi"></td>
        <td data-ecart="${p.cle}"></td></tr>`).join("")}
      <tr><td><b>Total</b></td><td><b>${nf(b.total)} FCFA</b></td><td><b id="dep-total"></b></td><td></td></tr>
    </tbody></table></div>`;
  const peindre = () => {
    postes.forEach((p) => {
      const c = z.querySelector(`[data-ecart="${p.cle}"]`);
      if (!saisi(p.cle)) { c.textContent = "–"; c.style.color = ""; return; }
      const e = Number(D[p.cle]) - p.montant;
      c.textContent = `${e > 0 ? "+" : ""}${nf(e)} FCFA`;
      c.style.color = e > 0 ? "var(--rouge)" : "var(--vert)";
    });
    $("#dep-total").textContent = `${nf(postes.reduce((a, p) => a + (saisi(p.cle) ? Number(D[p.cle]) : 0), 0))} FCFA`;
  };
  z.oninput = (ev) => {
    const t = ev.target;
    if (!t.dataset.dep) return;
    S.sale = true;
    if (t.value === "") delete D[t.dataset.dep]; else D[t.dataset.dep] = Number(t.value);
    peindre();
  };
  peindre();
  piedEnregistrer(z, "suivi", () => ({ depenses: D }), "Enregistrer et mettre à jour la note de suivi");
}


function editeurRecrutement(z, e) {
  if (!S.travail) S.travail = clone({ params: e.data.params, recrutement: e.data.recrutement });
  const R = S.travail.recrutement;
  const champ = (k, l, type = "input", plein = false) => `<div class="champ ${plein ? "plein" : ""}"><label>${esc(l)}</label>${type === "area" ? `<textarea class="saisie" rows="4" data-r="${k}">${esc(Array.isArray(R[k]) ? R[k].join("\n") : R[k])}</textarea>` : `<input class="saisie" ${type === "date" ? 'type="date"' : ""} data-r="${k}" value="${esc(R[k])}">`}</div>`;
  z.className = "carte-corps";
  z.innerHTML = `<div class="grille-2">
    ${champ("intitule", "Intitulé de l'annonce", "input", true)}
    ${champ("experience", "Expérience d'enquête minimale")}${champ("diplome", "Diplôme minimum")}
    ${champ("date_limite", "Date limite de candidature", "date")}${champ("contact", "Lien de dépôt des candidatures")}
    ${champ("presentation", "Présentation de Datatym", "area", true)}
    ${champ("mission", "Mission proposée", "area", true)}
    ${champ("taches", "Tâches (une par ligne)", "area", true)}
    ${champ("competences", "Compétences (une par ligne)", "area", true)}
    ${champ("dossier", "Pièces du dossier (une par ligne)", "area", true)}
  </div>`;
  z.oninput = (ev) => {
    const t = ev.target;
    if (!t.dataset.r) return;
    S.sale = true;
    R[t.dataset.r] = Array.isArray(R[t.dataset.r]) ? t.value.split("\n").filter((x) => x.trim()) : t.value;
  };
  piedEnregistrer(z, "echantillonnage", () => ({ recrutement: R }));
}

function editeurListes(z, cle, champs) {
  const d = S.projet.etapes[cle].data;
  if (!S.travail) S.travail = clone(Object.fromEntries(champs.map(([k]) => [k, d[k]])));
  const W = S.travail;
  z.className = "carte-corps";
  z.innerHTML = champs.map(([k, l, type, opts]) => `<div class="champ" style="margin-bottom:16px"><label>${esc(l)}</label>${
    type === "select" ? `<select class="saisie" data-w="${k}">${opts.map((o) => `<option ${W[k] === o ? "selected" : ""}>${esc(o)}</option>`).join("")}</select>`
      : type === "input" ? `<input class="saisie" data-w="${k}" value="${esc(W[k])}">`
        : `<textarea class="saisie" rows="5" data-w="${k}" data-liste="1">${esc((W[k] || []).join("\n"))}</textarea><span class="aide" style="font-size:12px">Un élément par ligne</span>`}</div>`).join("");
  z.oninput = z.onchange = (ev) => {
    const t = ev.target;
    if (!t.dataset.w) return;
    S.sale = true;
    W[t.dataset.w] = t.dataset.liste ? t.value.split("\n").filter((x) => x.trim()) : t.value;
  };
  piedEnregistrer(z, cle, () => W);
}

const editeurMethodo = (z) => editeurListes(z, "methodologie", [["logiciel", "Logiciel de traitement et d'analyse", "select", ["Python (VS Code)", "R (RStudio ou VS Code)", "Stata"]], ["limites", "Limites de l'étude", "liste"]]);
const editeurSuivi = (z) => editeurListes(z, "suivi", [["observations", "Observations de terrain", "liste"], ["recommandations", "Recommandations pour la prochaine édition", "liste"]]);
function editeurRapport(z, e) {
  editeurListes(z, "rapport", [["titre", "Titre du rapport", "input"], ["sous_titre", "Sous-titre", "input"]]);
  z.insertAdjacentHTML("afterbegin", `<div class="bandeau info">${ico("info")}<div>Pour recalculer les indicateurs après un nouvel import de données, utilisez <b>Mettre à jour</b> (ou <b>Régénérer</b> pour réécrire aussi les textes).</div></div>`);
}

// ------------------------------------------------------------------ collecte
function ongletImport(z, e) {
  const d = e.data;
  z.className = "carte-corps";
  z.innerHTML = `
    ${d.source ? `<div class="bandeau succes">${ico("check")}<div>Source actuelle : <b>${esc(d.source)}</b>${d.stats ? ` — ${d.stats.brut} formulaires reçus, ${d.stats.realise} valides.` : ""}</div></div>` : ""}
    <div class="sources">
      ${(() => {
        const kobo = `<div class="source" data-outil-source="kobo"><div class="source-tete"><span class="source-logo kobo">K</span><div><b>KoboToolbox</b><small>Synchronisation par l'API v2</small></div></div>
          <input class="saisie petite" id="k-serveur" value="${esc((d.kobo || {}).serveur || "https://kf.kobotoolbox.org")}" placeholder="Serveur">
          <input class="saisie petite" id="k-asset" value="${esc((d.kobo || {}).lien || (d.kobo || {}).asset || "")}" placeholder="Lien du formulaire (ee.kobotoolbox.org/x/…) ou asset UID">
          <input class="saisie petite" id="k-jeton" type="password" placeholder="${S.params.kobo_jeton_defini ? "Jeton mémorisé sur ce poste (laisser vide)" : "Jeton API"}">
          <label class="bascule" style="font-size:12.5px"><input type="checkbox" id="k-memo" checked> Mémoriser le jeton sur ce poste</label>
          <small class="aide">Jeton : sur Kobo, menu du compte › <b>Paramètres du compte › Sécurité › Clé API</b>.</small>
          <button class="btn btn-petit" id="k-sync">${ico("refresh")} Synchroniser</button></div>`;
        const qp = `<div class="source" data-outil-source="questionpro"><div class="source-tete"><span class="source-logo qp">QP</span><div><b>QuestionPro</b><small>Synchronisation par l'API v2</small></div></div>
          <div style="display:flex;gap:8px"><input class="saisie petite" id="q-enquete" value="${esc((d.questionpro || {}).enquete || "")}" placeholder="Identifiant de l'enquête, ex. 13825453">
            <input class="saisie petite" id="q-env" list="dl-env" style="width:76px" value="${esc((d.questionpro || {}).env || "com")}" title="Centre de données : com, eu, ca…"></div>
          <small class="aide">Le numéro de l'enquête, pas le lien de réponse (…/t/…) : il apparaît dans QuestionPro, dans l'adresse de l'enquête ouverte en édition (<code>surveyID=…</code>).</small>
          <datalist id="dl-env"><option value="com"><option value="eu"><option value="ca"></datalist>
          <input class="saisie petite" id="q-cle" type="password" placeholder="${S.params.questionpro_cle_definie ? "Clé mémorisée sur ce poste (laisser vide)" : "Clé API"}">
          <label class="bascule" style="font-size:12.5px"><input type="checkbox" id="q-memo" checked> Mémoriser la clé sur ce poste</label>
          <button class="btn btn-petit" id="q-sync">${ico("refresh")} Synchroniser</button>
          <small class="aide">Enquêteur : partagez le lien avec <code>?custom1=enq1</code>, <code>enq2</code>… pour le suivi par enquêteur.</small></div>`;
        const fichier = `<div class="source"><div class="source-tete"><span class="source-logo fic">${ico("upload")}</span><div><b>Fichier d'export</b><small>CSV ou Excel, Kobo ou QuestionPro</small></div></div>
          <label class="depot" id="depot"><div style="font-weight:600">Déposer un fichier</div><div class="aide" style="font-size:12px">ou cliquer pour choisir</div>
          <input type="file" id="fic" accept=".csv,.xlsx,.xls" hidden></label></div>`;
        return S.projet.fiche.outil === "questionpro" ? qp + kobo + fichier : kobo + qp + fichier;
      })()}
    </div>
    <div style="margin-top:22px;padding-top:18px;border-top:1px solid var(--bord)">
      <div class="lib" style="margin-bottom:4px">Tester la chaîne avec des données simulées</div>
      <p class="aide" style="margin:0 0 10px">Génère des soumissions cohérentes avec les quotas et le questionnaire, pour vérifier le tableau de bord, la note de suivi et le rapport avant le terrain.</p>
      <div class="actions"><button class="btn btn-petit" data-sim="0.3">Collecte à 30 %</button><button class="btn btn-petit" data-sim="0.6">Collecte à 60 %</button><button class="btn btn-petit" data-sim="1">Collecte terminée</button></div>
    </div>`;
  const slug = S.projet.slug;
  const envoyer = (fichier) => occupe($("#depot"), async () => {
    const f = new FormData();
    f.append("fichier", fichier);
    const r = await api("POST", `/api/projets/${slug}/collecte/import`, undefined, f);
    S.onglet = "tableau";
    majProjet(r, "Soumissions importées.");
  });
  $("#fic").onchange = (ev) => ev.target.files[0] && envoyer(ev.target.files[0]);
  const dep = $("#depot");
  dep.ondragover = (ev) => { ev.preventDefault(); dep.classList.add("survol"); };
  dep.ondragleave = () => dep.classList.remove("survol");
  dep.ondrop = (ev) => { ev.preventDefault(); dep.classList.remove("survol"); ev.dataTransfer.files[0] && envoyer(ev.dataTransfer.files[0]); };
  $("#q-sync").onclick = (ev) => occupe(ev.currentTarget, async () => {
    const r = await api("POST", `/api/projets/${slug}/collecte/questionpro`, { enquete: $("#q-enquete").value, env: $("#q-env").value, cle: $("#q-cle").value, memoriser: $("#q-memo").checked });
    chargerParams();
    S.onglet = "tableau";
    majProjet(r, "Synchronisation QuestionPro réussie.");
  });
  $("#k-sync").onclick = (ev) => occupe(ev.currentTarget, async () => {
    const r = await api("POST", `/api/projets/${slug}/collecte/kobo`, { serveur: $("#k-serveur").value, asset: $("#k-asset").value, jeton: $("#k-jeton").value, memoriser: $("#k-memo").checked });
    chargerParams();
    S.onglet = "tableau";
    majProjet(r, "Synchronisation KoboToolbox réussie.");
  });
  z.querySelectorAll("[data-sim]").forEach((b) => (b.onclick = () => occupe(b, async () => {
    const r = await api("POST", `/api/projets/${slug}/collecte/simuler`, { taux: Number(b.dataset.sim) });
    S.onglet = "tableau";
    majProjet(r, "Données de test générées.");
  })));
}

function ongletTableau(z, e) {
  const s = e.data.stats;
  z.className = "carte-corps";
  if (!s) {
    z.innerHTML = `<div class="vide">${ico("chart")}<div>Aucune soumission importée.</div><br><button class="btn btn-primaire" id="vers-import">${ico("upload")} Importer des données</button></div>`;
    $("#vers-import").onclick = () => { S.onglet = "import"; panneauEtape("collecte"); };
    return;
  }
  const api_ = ["API KoboToolbox", "API QuestionPro"].includes(e.data.source);
  const auto = (e.data.source === "API KoboToolbox" && S.params.kobo_jeton_defini) || (e.data.source === "API QuestionPro" && S.params.questionpro_cle_definie);
  const ecart = s.realise - s.prevu_a_date;
  const coul = (t) => (t >= 100 ? "#0E9F6E" : t >= 75 ? "#5AAEE8" : t >= 40 ? "#F5C26B" : "#F2A07B");
  const barre = (lbl, r, obj, prevu) => {
    const t = obj ? (100 * r) / obj : 0;
    const cls = prevu != null ? (r >= prevu ? "ok" : r < 0.8 * prevu ? "retard" : "") : t >= 100 ? "ok" : "";
    return `<div class="barre-l"><span class="lbl" title="${esc(lbl)}">${esc(lbl)}</span><span class="piste"><i class="${cls}" style="width:${Math.min(100, t)}%"></i>${prevu != null && obj ? `<span class="repere" style="left:${Math.min(100, (100 * prevu) / obj)}%" title="Prévu à date : ${prevu}"></span>` : ""}</span><span class="chf">${obj ? `${r} / ${obj}` : r}</span></div>`;
  };
  const qc = s.controle_qualite !== false;
  const croix = s.croisement || [];
  const zones = [...new Set(croix.map((q) => q.zone))];
  const sects = [...new Set(croix.map((q) => q.secteur))];
  const court = (l) => l.split(/ – | \(/)[0];
  const absentes = s.variables_absentes || [];
  z.innerHTML = `
    ${s.donnees_perimees || (s.donnees_perimees == null && absentes.length >= Math.max(3, 0.1 * (s.nb_variables || 0))) ? `<div class="bandeau alerte">${ico("alert")}<div><b>Ces données ont été collectées avec une version antérieure du questionnaire</b> (avant un changement de thème ou d'indicateurs) : les réponses ne correspondent plus aux questions actuelles. Réimportez les données du formulaire à jour, ou régénérez les données de test, avant la note de suivi et le rapport.</div></div>` : ""}
    <div class="aide" style="margin-bottom:12px;font-size:12.5px">Situation au ${dateFr(s.reference)} · jour ${s.jour_index} sur ${s.nb_jours} · dernière synchronisation ${heureFr(s.maj)}
      ${api_ ? `· <b>${esc(e.data.source)}</b>${auto ? " · resynchronisation automatique toutes les 5 minutes" : " · mémorisez le jeton pour la resynchronisation automatique"}` : ""}
      <button class="btn btn-fantome btn-petit" id="maj-tb">${ico("refresh")} ${api_ ? "Synchroniser maintenant" : "Recalculer"}</button>
      <label class="bascule" style="display:inline-flex;margin-left:6px" title="Activé : réponses hors cible et entretiens trop rapides écartés"><input type="checkbox" id="tb-qc" ${qc ? "checked" : ""} ${e.statut === "valide" ? "disabled" : ""}> Contrôle qualité</label></div>
    <div class="kpis-tb kpis-5">
      <div class="carte kpi"><div class="t">Questionnaires reçus</div><div class="v" data-compte="${s.brut}">0</div><div class="s">${[qc && s.hors_cible && `${s.hors_cible} hors cible`, s.refus && `${s.refus} refus`, qc && s.rapides && `${s.rapides} trop rapides`].filter(Boolean).join(" · ") || "tous exploitables"}</div></div>
      <div class="carte kpi"><div class="t">${qc ? "Questionnaires valides" : "Questionnaires renseignés"}</div><div class="v"><span data-compte="${s.realise}">0</span><span style="font-size:15px;color:var(--texte-3)"> / ${s.objectif}</span></div><div class="s">${nf(s.taux, 1)} % de l'objectif</div></div>
      <div class="carte kpi"><div class="t">Écart au calendrier</div><div class="v" data-compte="${ecart}" data-prefixe="${ecart > 0 ? "+" : ""}">0</div><div class="s ${ecart >= 0 ? "pos" : "neg"}">${s.prevu_a_date} prévus à date</div></div>
      <div class="carte kpi"><div class="t">Taux de complétion</div><div class="v" data-compte="${s.taux_completion}" data-dec="1" data-suffixe=" %">0</div><div class="s">${s.brut} reçus · ${s.refus} refus${qc ? ` · ${s.rapides} rapides` : ""}</div></div>
      <div class="carte kpi"><div class="t">Durée médiane</div><div class="v" ${s.duree_mediane != null ? `data-compte="${s.duree_mediane}" data-dec="1" data-suffixe=" min"` : ""}>–</div><div class="s">plafond 15 min</div></div>
    </div>
    <div class="carte" style="margin-bottom:16px"><div class="carte-titre"><h3>Avancement cumulé</h3>
      <div class="legende-graph"><span><i style="background:var(--marine)"></i>Prévu</span><span><i style="background:var(--bleu)"></i>Réalisé</span></div></div>
      <div class="carte-corps">${graphCumul(s)}</div></div>
    ${(s.par_zone || []).some((x) => typeof CARTE_AFRIQUE !== "undefined" && CARTE_AFRIQUE.pays[x.code]) ? `
    <div class="grille-tb grille-carte">
      <div class="carte"><div class="carte-titre"><h3>Carte des pays</h3><span class="aide" style="font-size:11.5px">part de l'objectif atteinte</span></div>
        <div class="carte-corps">${carteSuivi(s.par_zone)}</div></div>
      <div class="carte"><div class="carte-titre"><h3>Par pays</h3></div>
        <div class="carte-corps barres">${[...s.par_zone].sort((a, b) => b.taux - a.taux).map((x) => barre(x.zone, x.realise, x.objectif)).join("")}</div></div>
    </div>` : ""}
    <div class="grille-tb">
      ${(s.par_secteur || []).length ? `<div class="carte"><div class="carte-titre"><h3>Par secteur</h3><span class="aide" style="font-size:11.5px">objectif réparti à parts égales</span></div>
        <div class="carte-corps barres">${[...s.par_secteur].sort((a, b) => b.realise - a.realise).map((x) => barre(x.secteur, x.realise, x.objectif)).join("")}</div></div>` : ""}
      <div class="carte"><div class="carte-titre"><h3>Par profil de dirigeant</h3></div>
        <div class="carte-corps barres">${s.par_profil.map((x) => barre(x.profil, x.realise, x.objectif)).join("")}
          ${qc && s.hors_cible ? `<p class="aide" style="margin:6px 0 0;font-size:12px">${s.hors_cible} réponse(s) hors cible (autre fonction ou entreprise sous le seuil), non comptées.</p>` : ""}</div></div>
    </div>
    ${(s.par_collecteur || []).length ? `<div class="carte" style="margin-bottom:16px"><div class="carte-titre"><h3>Collecteurs</h3><span class="aide" style="font-size:11.5px">tels qu'enregistrés dans les réponses</span></div>
      <div class="carte-corps"><div class="grille-tab"><table><thead><tr><th>Collecteur</th><th style="text-align:right">${qc ? "Valides" : "Renseignés"}</th><th style="text-align:right">Reçus</th>${qc ? '<th style="text-align:right">Écartés</th>' : ""}<th>Pays principaux</th><th>Dernier envoi</th></tr></thead><tbody>
        ${s.par_collecteur.map((c) => `<tr><td><b>${esc(c.nom)}</b></td><td style="text-align:right">${c.valides}</td><td style="text-align:right">${c.recus}</td>${qc ? `<td style="text-align:right">${c.ecartes || "–"}</td>` : ""}<td>${esc(c.pays.join(", ")) || "–"}</td><td>${c.dernier ? dateFr(c.dernier) : "–"}</td></tr>`).join("")}
      </tbody></table></div></div></div>` : ""}
    <div class="grille-tb">
      ${s.par_enqueteur.length ? `<div class="carte"><div class="carte-titre"><h3>Par enquêteur du plan</h3><span class="aide" style="font-size:11.5px">trait = prévu à date</span></div>
        <div class="carte-corps barres">${s.par_enqueteur.map((x) => barre(`${x.nom} · ${x.zone}`, x.realise, x.objectif, x.prevu)).join("")}</div></div>` : ""}
      ${croix.length ? `<div class="carte"><div class="carte-titre"><h3>Croisement pays × secteur</h3><span class="aide" style="font-size:11.5px">réalisé / objectif</span></div>
        <div class="carte-corps"><div class="grille-tab"><table class="carte-chaleur"><thead><tr><th></th>${sects.map((p) => `<th title="${esc(p)}">${esc(court(p))}</th>`).join("")}<th>Total</th></tr></thead><tbody>
          ${zones.map((zn) => { const l = croix.filter((x) => x.zone === zn); const r = l.reduce((a, x) => a + x.realise, 0), o = l.reduce((a, x) => a + x.objectif, 0);
            return `<tr><th>${esc(zn)}</th>${sects.map((p) => { const q = l.find((x) => x.secteur === p); return `<td style="background:${coul(q.taux)}22;color:${q.taux >= 100 ? "#0A6B4B" : "#1B2333"}" title="${esc(zn)} · ${esc(p)} : ${q.realise} / ${q.objectif}">${q.realise}/${q.objectif}</td>`; }).join("")}<td><b>${r}/${o}</b></td></tr>`; }).join("")}
        </tbody></table></div></div></div>` : ""}
    </div>
    ${qc ? `<div class="carte"><div class="carte-titre"><h3>Incidents et qualité des données</h3></div>
      <div class="carte-corps">${s.incidents.length ? `<ul class="incidents" style="margin:0;padding-left:18px">${s.incidents.map((i) => `<li>${esc(i)}</li>`).join("")}</ul>` : `<span class="aide">Aucun incident relevé.</span>`}</div></div>` : ""}`;
  z.classList.add("tb-anime");
  A.compter(z);
  z.querySelectorAll(".carte-chaleur td").forEach((td, k) => (td.style.animationDelay = `${Math.min(k * 12, 900)}ms`));
  z.querySelectorAll(".barre-l .piste i").forEach((b, k) => (b.style.animationDelay = `${200 + k * 50}ms`));
  const synchroniser = async () => {
    const avant = s.brut;
    const r = await api("POST", `/api/projets/${S.projet.slug}/collecte/actualiser`);
    const apres = (r.etapes.collecte.data.stats || {}).brut || 0;
    return { r, nouveaux: apres - avant };
  };
  $("#tb-qc").onchange = (ev) => occupe(ev.currentTarget, async () => {
    const r = await api("PUT", `/api/projets/${S.projet.slug}/etapes/collecte/data`, { controle_qualite: ev.currentTarget.checked });
    majProjet(r, ev.currentTarget.checked ? "Contrôle qualité activé : hors cible et entretiens trop rapides écartés." : "Suivi seul : toutes les réponses renseignées sont comptées.");
  });
  $("#maj-tb").onclick = (ev) => occupe(ev.currentTarget, async () => {
    const { r, nouveaux } = await synchroniser();
    majProjet(r, api_ ? (nouveaux > 0 ? `${nouveaux} nouvelle(s) soumission(s) reçue(s).` : "Aucune nouvelle soumission.") : "Tableau de bord recalculé.");
  });
  // resynchronisation automatique tant que le tableau de bord reste affiché (onglet visible, rien en cours d'édition)
  if (auto) A.intervalle(async () => {
    if (document.hidden || S.sale || S.etape !== "collecte" || S.onglet !== "tableau") return;
    try {
      const { r, nouveaux } = await synchroniser();
      if (nouveaux > 0) majProjet(r, `${nouveaux} nouvelle(s) soumission(s) reçue(s).`);
    } catch (err) { /* nouvel essai au prochain passage */ }
  }, 5 * 60 * 1000);
}

// Carte de suivi : part de l'objectif atteinte par pays, une seule teinte du clair au foncé
const PALIERS_CARTE = [[25, "#DCEBFA"], [50, "#A6CFF3"], [75, "#5FA9E8"], [100, "#1F7FD1"], [Infinity, "#0B4F8A"]];
function carteSuivi(parZone) {
  const C = CARTE_AFRIQUE;
  const etude = Object.fromEntries(parZone.filter((x) => C.pays[x.code]).map((x) => [x.code, x]));
  const teinte = (t) => PALIERS_CARTE.find(([max]) => t < max)[1];
  // cadrage sur les pays de l'étude, avec une marge
  const boites = Object.keys(etude).map((c) => C.pays[c].match(/-?\d+(\.\d+)?,-?\d+(\.\d+)?/g).map((p) => p.split(",").map(Number)));
  const xs = boites.flat().map((p) => p[0]), ys = boites.flat().map((p) => p[1]);
  const m = 30, x0 = Math.max(0, Math.min(...xs) - m), y0 = Math.max(0, Math.min(...ys) - m);
  const w = Math.min(C.largeur, Math.max(...xs) + m) - x0, h = Math.min(C.hauteur, Math.max(...ys) + m) - y0;
  const fond = Object.entries(C.pays).filter(([c]) => !etude[c]).map(([c, d]) => `<path d="${d}" class="cs-fond"><title>${esc(C.noms[c])}</title></path>`).join("");
  const pays = Object.entries(etude).map(([c, x]) => `<path d="${C.pays[c]}" class="cs-pays" style="fill:${teinte(x.taux)}"><title>${esc(x.zone)} : ${x.realise} / ${x.objectif} (${nf(x.taux)} %)</title></path>`).join("");
  const etiq = Object.entries(etude).map(([c, x]) => { const [cx, cy] = C.centres[c]; return `<text x="${cx}" y="${cy}" class="cs-etiq${x.taux >= 75 ? " clair" : ""}">${nf(x.taux)} %</text>`; }).join("");
  const legende = PALIERS_CARTE.map(([max, coul], k) => `<span><i style="background:${coul}"></i>${k === 0 ? "< 25 %" : max === Infinity ? "≥ 100 %" : `${PALIERS_CARTE[k - 1][0]}–${max} %`}</span>`).join("");
  return `<svg class="carte-suivi" viewBox="${x0} ${y0} ${w} ${h}" role="img" aria-label="Carte de l'avancement par pays">${fond}${pays}${etiq}</svg>
    <div class="legende-carte">${legende}</div>`;
}

// Indicateurs de la note de cadrage calculés en direct sur les réponses renseignées
async function ongletIndicateurs(z, e, cle, filtre = S.filtreInd || "") {
  z.className = "carte-corps";
  z.innerHTML = `<div class="chargement"></div>`;
  let d;
  try { d = await api("GET", `/api/projets/${S.projet.slug}/collecte/indicateurs?filtre=${encodeURIComponent(filtre)}`); }
  catch (err) { z.innerHTML = `<div class="bandeau alerte">${ico("alert")}<div>${esc(err.message)}</div></div>`; return; }
  if (!d.n && !filtre) {
    z.innerHTML = `<div class="vide">${ico("target")}<div>Aucune réponse importée : les indicateurs se calculeront dès la première synchronisation.</div></div>`;
    return;
  }
  const noms = { zone: "Pays", profil: "Fonction", secteur: "Secteur" };
  const select = `<select class="saisie petite" id="ind-filtre" style="width:auto;min-width:220px"><option value="">Ensemble des répondants</option>
    ${Object.entries(d.options).map(([k, l]) => `<optgroup label="${noms[k]}">${l.map((m) => `<option value="${k}:${esc(m.code)}" ${filtre === `${k}:${m.code}` ? "selected" : ""}>${esc(m.label)}</option>`).join("")}</optgroup>`).join("")}</select>`;
  const inds = d.indicateurs.filter((i) => i.type !== "indice");
  const avec = inds.filter((i) => i.n), sans = inds.filter((i) => !i.n);
  const blocs = [...new Set(avec.map((i) => i.bloc))];
  const carte = (i) => {
    const mods = i.type === "multiple" ? [...i.modalites].sort((a, b) => b.pct - a.pct) : i.modalites;
    const max = Math.max(...mods.map((m) => m.pct), 1);
    return `<div class="ind-carte">
      <div class="ind-tete"><span class="ind-num">${esc(i.num)}</span><div><b>${esc(i.libelle)}</b><small>${esc(i.question)}</small></div>
        <span class="ind-n ${i.n < 30 ? "faible" : ""}" title="${i.n < 30 ? "Moins de 30 réponses : à lire comme une tendance" : ""}">n = ${i.n}</span></div>
      ${i.solde != null ? `<div class="ind-solde">Solde d'opinion <b>${i.solde > 0 ? "+" : ""}${nf(i.solde)}</b></div>` : ""}
      <div class="ind-barres">${mods.map((m) => `<div class="ind-l" title="${esc(m.label)} : ${nf(m.pct, 1)} %"><span class="lbl">${esc(m.label)}</span>
        <span class="piste"><i style="width:${(100 * m.pct) / max}%"></i></span><span class="v">${nf(m.pct)} %</span></div>`).join("")}</div>
      ${i.type === "multiple" ? `<small class="aide">Plusieurs réponses possibles : le total dépasse 100 %.</small>` : ""}
    </div>`;
  };
  const indice = d.indicateurs.find((i) => i.type === "indice");
  z.innerHTML = `
    <div class="ind-entete">${select}
      <span class="aide">${d.n} répondant(s) ${d.controle_qualite ? "valides" : "renseignés"} · <b>${avec.length} indicateurs calculés</b>${sans.length ? ` · ${sans.length} sans données` : ""} · calcul à la date de la dernière synchronisation</span></div>
    ${indice ? `<div class="bandeau info">${ico("info")}<div><b>${esc(indice.libelle)}</b> : ${indice.valeur != null ? `<b>${nf(indice.valeur)} / 100</b>` : "pas encore calculé, ses poids et son codage restent à valider après le pré-test."}</div></div>` : ""}
    ${blocs.map((b) => `<h3 class="ind-bloc">${esc(b)}</h3><div class="ind-grille">${avec.filter((i) => i.bloc === b).map(carte).join("")}</div>`).join("")}
    ${sans.length ? `<h3 class="ind-bloc">Pas encore de données</h3>
      <p class="aide" style="margin-top:0">Ces questions n'apparaissent pas dans les réponses reçues : elles sont absentes de l'enquête en ligne, posées sous une autre forme, ou soumises à une condition qu'aucun répondant n'a remplie.</p>
      <div class="ind-sans">${sans.map((i) => `<span title="${esc(i.question)}"><b>${esc(i.num)}</b> ${esc(i.libelle)}</span>`).join("")}</div>` : ""}`;
  $("#ind-filtre").onchange = (ev) => { S.filtreInd = ev.target.value; ongletIndicateurs(z, e, cle, ev.target.value); };
}

function graphCumul(s) {
  const W = 760, H = 230, g = 38, b = 26;
  const j = s.par_jour;
  const max = Math.max(s.objectif, ...j.map((x) => x.cumul_realise)) * 1.05;
  const x = (i) => g + (i * (W - g - 10)) / Math.max(1, j.length - 1);
  const y = (v) => H - b - (v * (H - b - 10)) / max;
  const ligne = (pts) => pts.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join("");
  const prev = j.map((d, i) => [x(i), y(d.cumul_prevu)]);
  const reel = j.filter((d) => d.passe).map((d, i) => [x(i), y(d.cumul_realise)]);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => Math.round(s.objectif * t));
  return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;stroke-width:1">
    ${ticks.map((t) => `<line x1="${g}" x2="${W - 10}" y1="${y(t)}" y2="${y(t)}" stroke="#E3E8EF"/><text x="${g - 6}" y="${y(t) + 4}" text-anchor="end" font-size="10" fill="#8A93A5" stroke="none">${t}</text>`).join("")}
    ${j.map((d, i) => (i % Math.ceil(j.length / 8) === 0 || i === j.length - 1 ? `<text x="${x(i)}" y="${H - 8}" text-anchor="middle" font-size="10" fill="#8A93A5" stroke="none">${jourCourt(d.date)}</text>` : "")).join("")}
    ${reel.length ? `<path d="${ligne(reel)}L${reel[reel.length - 1][0]},${y(0)}L${reel[0][0]},${y(0)}Z" fill="rgba(0,135,224,.10)" stroke="none"/>` : ""}
    <path class="trace-prevu" d="${ligne(prev)}" fill="none" stroke="#19243E" stroke-width="2" stroke-dasharray="5 4"/>
    ${reel.length ? `<path class="trace" pathLength="1" d="${ligne(reel)}" fill="none" stroke="#0087E0" stroke-width="2.5"/>${reel.map((p, k) => `<circle class="point" style="animation-delay:${600 + k * 60}ms" cx="${p[0]}" cy="${p[1]}" r="3" fill="#0087E0" stroke="#fff" stroke-width="1.5"/>`).join("")}` : ""}
  </svg>`;
}

// ------------------------------------------------------------------ paramètres
function vueParametres(app) {
  document.body.dataset.page = "parametres";
  const P = S.params;
  app.innerHTML = `
    <div class="parametres">
      <div class="engrenages" aria-hidden="true"><i></i><i></i><i></i></div>
      <span class="sur" data-reveal="haut">Configuration</span><h1 class="titre-section-l" data-reveal="haut" data-delai="60">Paramètres</h1>
      <p class="aide-l" data-reveal="haut" data-delai="120" style="margin-bottom:22px">${IA_VISIBLE ? "Rédaction assistée, textes de présentation du cabinet et coûts unitaires de référence." : "Textes de présentation du cabinet et coûts unitaires de référence."}</p>
      <div class="carte neon" style="margin-bottom:16px" ${IA_VISIBLE ? "" : "hidden"}><div class="carte-titre"><h3>${ico("sparkle")} Rédaction assistée par Claude</h3><span class="badge-ia ${P.ia_active && P.cle_definie ? "on" : ""}">${P.ia_active && P.cle_definie ? "Active" : "Inactive"}</span></div>
        <div class="carte-corps">
          <p class="aide" style="margin-top:0">Sans IA, la plateforme rédige à partir de règles et d'une banque d'indicateurs Datatym. Avec une clé API Anthropic, Claude propose des indicateurs et des textes adaptés au thème, puis rédige les messages clés du rapport. Tout reste relu et validé par le cabinet.</p>
          <div class="grille-2">
            <div class="champ plein"><label class="bascule"><input type="checkbox" id="p-ia" ${P.ia_active ? "checked" : ""}> Activer la rédaction assistée par l'IA</label></div>
            <div class="champ"><label>Clé API Anthropic</label><input class="saisie" id="p-cle" type="password" value="${esc(P.anthropic_api_key)}" placeholder="sk-ant-…"></div>
            <div class="champ"><label>Modèle</label><select class="saisie" id="p-modele">${[["claude-opus-5-5", "Claude Opus 5.5 (recommandé)"], ["claude-sonnet-5-5", "Claude Sonnet 5.5 (plus rapide)"]].map(([v, l]) => `<option value="${v}" ${P.modele === v ? "selected" : ""}>${l}</option>`).join("")}</select></div>
          </div>
          <div class="actions" style="margin-top:12px"><button class="btn btn-petit" id="p-test">${ico("sparkle")} Tester la connexion</button><span id="p-res" class="aide" style="align-self:center"></span></div>
        </div></div>
      <div class="carte"><div class="carte-titre"><h3>Textes Datatym</h3></div><div class="carte-corps">
        <div class="champ" style="margin-bottom:14px"><label>Présentation de Datatym (notes de recrutement, formation)</label><textarea class="saisie" id="p-pres" rows="5">${esc(P.presentation_datatym)}</textarea></div>
        <div class="champ"><label>Lien de dépôt des candidatures par défaut</label><input class="saisie" id="p-contact" value="${esc(P.contact_recrutement)}"></div>
        <div class="pied-form"><button class="btn btn-primaire" data-enr-params>${ico("check")} Enregistrer</button></div>
      </div></div>
      <div class="carte" style="margin-top:16px"><div class="carte-titre"><h3>${ico("coin")} Coûts unitaires de référence</h3></div><div class="carte-corps">
        <p class="aide" style="margin-top:0">Ils servent à l'estimation du coût dans la note de cadrage et au budget de collecte de chaque nouvelle étude, où ils restent modifiables. Valeurs indicatives à remplacer par les tarifs de Datatym.</p>
        <div class="grille-tab"><table><thead><tr><th>Poste</th><th>Unité</th><th>FCFA</th></tr></thead><tbody>
          ${P.couts_unitaires.map((c, k) => `<tr><td>${esc(c.libelle)}</td><td class="aide">${esc(c.unite)}</td><td><input class="saisie petite" style="width:120px" type="number" min="0" step="500" data-cu-ref="${k}" value="${c.valeur}"></td></tr>`).join("")}
        </tbody></table></div>
        <div class="pied-form"><button class="btn btn-primaire" data-enr-params>${ico("check")} Enregistrer</button></div>
      </div></div>
    </div>`;
  A.reveler(app);
  const lire = () => ({ ia_active: $("#p-ia").checked, anthropic_api_key: $("#p-cle").value, modele: $("#p-modele").value, presentation_datatym: $("#p-pres").value, contact_recrutement: $("#p-contact").value,
    couts_unitaires: P.couts_unitaires.map((c, k) => ({ cle: c.cle, valeur: Number(app.querySelector(`[data-cu-ref="${k}"]`).value) || 0 })) });
  app.querySelectorAll("[data-enr-params]").forEach((b) => (b.onclick = (e) => occupe(e.currentTarget, async () => {
    await api("PUT", "/api/parametres", lire());
    await chargerParams();
    toast("Paramètres enregistrés.", "succes");
    vueParametres(app);
  })));
  $("#p-test").onclick = (e) => occupe(e.currentTarget, async () => {
    await api("PUT", "/api/parametres", lire());
    await chargerParams();
    const r = await api("POST", "/api/parametres/tester");
    $("#p-res").textContent = r.message;
    $("#p-res").style.color = r.ok ? "var(--vert)" : "var(--rouge)";
  });
}

