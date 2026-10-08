/* Page « Lancer une étude » : les éléments essentiels, saisis une fois, avec aperçu vivant */
"use strict";

const DOMAINES_JS = [
  ["Transformation numérique", /\bia\b|intelligence artificielle|digital|num[ée]rique|technolog|automatis|transformation|cyber|donn[ée]es/i, ["Indice de maturité numérique", "Usage des outils d'IA", "Satisfaction vis-à-vis des outils", "Freins à l'adoption"]],
  ["Emploi et talents", /talent|emploi|rh\b|ressources humaines|jeune|gen ?z|salari|travail|recrutement|engagement/i, ["Indice de confiance des actifs", "Satisfaction au travail", "Reconnaissance", "Intention de mobilité"]],
  ["Climat des affaires", /affaires|entreprise|commerce|conjoncture|[ée]conom|march[ée]|secteur priv|pme|industri|investiss|exportat|activit/i, ["Indice de confiance", "Niveau d'activité", "Évolution du chiffre d'affaires", "Intention d'investir"]],
];
const DIRECTION_JS = /\b(dg|pdg|dga|directeur|directrice|direction|dirigeant|responsable|manager|chef|g[ée]rant|cadre|daf|dsi|drh|ceo|patron|propri[ée]taire)/i;
const SUGG_CIBLE = ["DG", "Responsables", "Vendeurs", "Employés", "Managers", "DSI", "DRH", "Chefs de ménage"];
const SUGG_ZONES = ["Dakar", "Thiès", "Saint-Louis", "Abidjan", "Bouaké", "Bamako", "Ouagadougou", "Lomé", "Cotonou", "Douala"];
const ETAPES_ETUDE = [["Le sujet", "Thème et objectif"], ["La cible", "Profils interrogés"], ["Le terrain", "Zones, taille, durée"], ["Le lancement", "Budget et récapitulatif"]];

const E = { etape: 0, f: null };

function domaineDe(t) {
  for (const [nom, re, inds] of DOMAINES_JS) if (re.test(t)) return { nom, inds };
  return { nom: "Baromètre d'opinion", inds: ["Indice synthétique", "Situation actuelle", "Perspectives", "Attentes prioritaires"] };
}
const marge = (n) => (n >= 30 ? (1.96 * Math.sqrt(0.25 / n) * 100) : null);
function joursCollecte(duree, debut) {
  const d0 = debut ? new Date(debut) : null;
  if (!d0) return Math.max(1, Math.round(duree * 6 / 7));
  let n = 0;
  for (let k = 0; k < duree; k++) { const d = new Date(d0); d.setDate(d.getDate() + k); if (d.getDay() !== 0) n++; }
  return Math.max(1, n);
}

function ficheVide() {
  return { theme: "", objectif: "", cible: [], zones: [], secteur: "", taille: 400, duree: 15, cout: "", date_debut: "", outil: "kobo" };
}

function vueEtude(app, params) {
  document.body.dataset.page = "etude";
  E.etape = 0;
  E.f = ficheVide();
  const m = MODELES.find((x) => x.cle === params.get("modele"));
  if (m) appliquerModele(m, false);
  app.innerHTML = `
  <section class="etude">
    <div class="soie" aria-hidden="true">
      <svg viewBox="0 0 1440 900" preserveAspectRatio="none">
        <path class="ruban r1" d="M-100 620 C 250 420, 520 820, 860 560 S 1380 380, 1560 520 L1560 900 L-100 900Z"/>
        <path class="ruban r2" d="M-100 700 C 300 560, 600 900, 980 660 S 1400 560, 1560 640 L1560 900 L-100 900Z"/>
        <path class="ruban r3" d="M-100 300 C 220 160, 560 420, 900 240 S 1300 80, 1560 200 L1560 0 L-100 0Z"/>
      </svg>
    </div>
    <div class="etude-tete">
      <span class="sur" data-reveal="haut">Nouvelle étude</span>
      <h1 class="titre-section-l" data-reveal="haut" data-delai="80">Les éléments essentiels pour lancer le baromètre.</h1>
      <p class="aide-l" data-reveal="haut" data-delai="160">Partir d'un modèle Datatym, ou saisir librement. Tout reste modifiable ensuite.</p>
      <div class="modeles">${MODELES.map((x, k) => `<button class="modele ${m && m.cle === x.cle ? "actif" : ""}" data-modele="${x.cle}" style="--f1:${x.fond[0]};--f2:${x.fond[1]}" data-reveal="haut" data-delai="${220 + k * 70}"><span>${esc(x.sur)}</span><b>${esc(x.titre)}</b></button>`).join("")}</div>
    </div>
    <div class="etude-corps">
      <div class="assistant carte-verre" data-reveal="haut" data-delai="200">
        <div class="ass-etapes">${ETAPES_ETUDE.map(([t, s], k) => `<button class="ass-etape" data-aller="${k}"><span class="ae-num">${k + 1}</span><span><b>${t}</b><small>${s}</small></span></button>`).join("")}
          <div class="ass-liquide"><i id="ass-liquide"></i></div></div>
        <div class="ass-fenetre"><div class="ass-rail" id="ass-rail">
          ${[panneauSujet(), panneauCible(), panneauTerrain(), panneauLancement()].map((h, k) => `<div class="ass-panneau" data-p="${k}">${h}</div>`).join("")}
        </div></div>
        <div class="ass-pied">
          <button class="btn" id="ass-prec">${ico("back")} Précédent</button>
          <span class="ass-compte" id="ass-compte">1 / 4</span>
          <button class="btn btn-primaire" id="ass-suiv">Suivant <span style="display:inline-flex;transform:scaleX(-1)">${ico("back")}</span></button>
        </div>
      </div>
      <aside class="apercu-vivant" data-reveal="droite" data-delai="300">
        <div class="av-papier" id="av-papier"></div>
        <div class="av-jauges" id="av-jauges"></div>
        <div class="av-chaine" id="av-chaine"></div>
      </aside>
    </div>
  </section>`;
  lierEtude(app);
  A.reveler(app);
  A.incliner(".modele", 10, app);
  rafraichirEtude(true);
}

function champ(id, label, html, aide = "") {
  return `<div class="champ"><label for="${id}">${label}</label>${html}${aide ? `<span class="aide" style="font-size:12px">${aide}</span>` : ""}</div>`;
}

function panneauSujet() {
  return `<h2 class="ass-titre">De quoi parle ce baromètre&nbsp;?</h2>
    ${champ("e-theme", 'Thème du baromètre <span class="obl">*</span>', `<input class="saisie saisie-xl" id="e-theme" data-f="theme" placeholder="Climat des affaires dans le commerce formel">`)}
    ${champ("e-objectif", 'Objectif <span class="obl">*</span>', `<textarea class="saisie" id="e-objectif" data-f="objectif" rows="3" placeholder="Mesurer la confiance des entreprises"></textarea>`)}
    <div class="domaine" id="e-domaine"></div>`;
}

function panneauCible() {
  return `<h2 class="ass-titre">Qui interroge-t-on&nbsp;?</h2>
    ${champ("e-cible-in", 'Profils de la cible <span class="obl">*</span>', `<div class="puces-saisie" data-liste="cible"><input id="e-cible-in" placeholder="Saisir un profil puis Entrée"></div>`, "Les dirigeants et les profils opérationnels ne reçoivent pas les mêmes questions.")}
    <div class="suggestions" data-sugg="cible">${SUGG_CIBLE.map((s) => `<button data-ajout="${esc(s)}">+ ${esc(s)}</button>`).join("")}</div>
    <div class="profils-niveaux" id="e-niveaux"></div>`;
}

function panneauTerrain() {
  return `<h2 class="ass-titre">Où et combien&nbsp;?</h2>
    ${champ("e-zones-in", 'Zones d\'enquête <span class="obl">*</span>', `<div class="puces-saisie" data-liste="zones"><input id="e-zones-in" placeholder="Saisir une zone puis Entrée"></div>`)}
    <div class="suggestions" data-sugg="zones">${SUGG_ZONES.map((s) => `<button data-ajout="${esc(s)}">+ ${esc(s)}</button>`).join("")}</div>
    <div class="grille-2" style="margin-top:14px">
      ${champ("e-secteur", "Secteur", `<input class="saisie" id="e-secteur" data-f="secteur" placeholder="Commerce formel">`, "Plusieurs secteurs séparés par des virgules ajoutent une question.")}
      ${champ("e-date", "Début de la collecte", `<input class="saisie" type="date" id="e-date" data-f="date_debut">`, "Par défaut : le lundi dans trois semaines.")}
    </div>
    <div class="curseurs">
      <div class="curseur"><div class="cu-tete"><label for="e-taille">Taille visée</label><b><span id="v-taille"></span> répondants</b></div>
        <input type="range" id="e-taille" data-f="taille" min="50" max="2000" step="10"></div>
      <div class="curseur"><div class="cu-tete"><label for="e-duree">Durée de l'enquête</label><b><span id="v-duree"></span> jours</b></div>
        <input type="range" id="e-duree" data-f="duree" min="3" max="60" step="1"></div>
    </div>
    <div class="lib" style="margin:16px 0 8px">Outil de collecte prioritaire</div>
    <div class="choix-outil">
      <button class="outil" data-outil="kobo"><b>KoboToolbox</b><span>XLSForm, KoboCollect hors ligne, API de suivi</span></button>
      <button class="outil" data-outil="questionpro"><b>QuestionPro</b><span>Import du questionnaire, application hors ligne</span></button>
    </div>`;
}

function panneauLancement() {
  return `<h2 class="ass-titre">Prêt à lancer&nbsp;?</h2>
    ${champ("e-cout", 'Estimation du coût total <span class="ex">facultatif</span>', `<div class="saisie-unite"><input class="saisie saisie-xl" id="e-cout" data-f="cout" inputmode="numeric" placeholder="12 000 000"><span>FCFA</span></div>`, "Sans montant, la répartition budgétaire est simplement omise des documents.")}
    <div class="recap" id="e-recap"></div>
    <button class="btn btn-lumiere btn-lancer" id="e-lancer">${ico("play")} Lancer l'étude et générer la note de cadrage</button>`;
}

function appliquerModele(m, anime = true) {
  Object.assign(E.f, { theme: m.theme, objectif: m.objectif, cible: m.cible.split(",").map((x) => x.trim()), secteur: m.secteur });
  if (anime) {
    document.querySelectorAll(".modele").forEach((b) => b.classList.toggle("actif", b.dataset.modele === m.cle));
    ["e-theme", "e-objectif", "e-secteur"].forEach((id) => { const el = $("#" + id); if (el) { el.value = E.f[el.dataset.f]; el.classList.remove("flash", "erreur"); void el.offsetWidth; el.classList.add("flash"); } });
    rafraichirEtude(true);
  }
}

function lierEtude(app) {
  const f = E.f;
  app.querySelectorAll("[data-f]").forEach((el) => {
    el.value = f[el.dataset.f] ?? "";
    el.addEventListener("input", () => {
      let v = el.value;
      if (el.dataset.f === "cout") { v = v.replace(/\D/g, ""); el.value = v ? Number(v).toLocaleString("fr-FR") : ""; }
      f[el.dataset.f] = ["taille", "duree"].includes(el.dataset.f) ? +v : v;
      el.classList.remove("erreur");
      rafraichirEtude();
    });
  });
  app.querySelectorAll("[data-modele]").forEach((b) => (b.onclick = () => appliquerModele(MODELES.find((x) => x.cle === b.dataset.modele))));
  app.querySelectorAll(".puces-saisie").forEach((box) => {
    const cle = box.dataset.liste;
    const inp = box.querySelector("input");
    box.onclick = () => inp.focus();
    inp.addEventListener("keydown", (e) => {
      if ((e.key === "Enter" || e.key === ",") && inp.value.trim()) { e.preventDefault(); ajouterPuce(cle, inp.value); inp.value = ""; }
      else if (e.key === "Backspace" && !inp.value && f[cle].length) { f[cle].pop(); rafraichirEtude(); }
    });
    inp.addEventListener("blur", () => { if (inp.value.trim()) { ajouterPuce(cle, inp.value); inp.value = ""; } });
  });
  app.querySelectorAll("[data-sugg]").forEach((s) => s.addEventListener("click", (e) => {
    const b = e.target.closest("[data-ajout]");
    if (b) ajouterPuce(s.dataset.sugg, b.dataset.ajout);
  }));
  app.addEventListener("click", (e) => {
    const x = e.target.closest("[data-retirer]");
    if (!x) return;
    const [cle, k] = x.dataset.retirer.split(":");
    f[cle].splice(+k, 1);
    rafraichirEtude();
  });
  app.querySelectorAll("[data-outil]").forEach((b) => (b.onclick = () => { f.outil = b.dataset.outil; rafraichirEtude(); }));
  app.querySelectorAll("[data-aller]").forEach((b) => (b.onclick = () => allerEtape(+b.dataset.aller)));
  $("#ass-prec").onclick = () => allerEtape(E.etape - 1);
  $("#ass-suiv").onclick = () => allerEtape(E.etape + 1);
  $("#e-lancer").onclick = lancerEtude;
}

function ajouterPuce(cle, v) {
  v = v.replace(/,$/, "").trim();
  if (!v || E.f[cle].some((x) => x.toLowerCase() === v.toLowerCase())) return;
  E.f[cle].push(v);
  document.querySelector(`[data-liste="${cle}"]`).classList.remove("erreur");
  rafraichirEtude();
}

function manquants(etape) {
  const f = E.f, m = [];
  if (etape >= 0) { if (!f.theme.trim()) m.push("e-theme"); if (!f.objectif.trim()) m.push("e-objectif"); }
  if (etape >= 1 && !f.cible.length) m.push("e-cible-in");
  if (etape >= 2 && !f.zones.length) m.push("e-zones-in");
  return m;
}

function signalerManquants(m) {
  const panneaux = [...document.querySelectorAll(".ass-panneau")];
  const p0 = panneaux.findIndex((p) => p.contains($("#" + m[0])));
  if (p0 >= 0) E.etape = p0;
  rafraichirEtude();
  m.forEach((id) => {
    const el = $("#" + id);
    const cible = el.closest(".puces-saisie") || el;
    cible.classList.add("erreur", "secoue");
    setTimeout(() => cible.classList.remove("secoue"), 500);
  });
  toast("Complétez les éléments essentiels avant de continuer.", "erreur");
}

function allerEtape(k) {
  if (k < 0 || k > 3) return;
  if (k > E.etape) {
    const m = manquants(Math.min(k - 1, 2));
    if (m.length) return signalerManquants(m);
  }
  E.etape = k;
  rafraichirEtude();
}

function rafraichirEtude(complet) {
  const f = E.f;
  const n = f.taille || 0;
  const jours = joursCollecte(f.duree || 1, f.date_debut);
  const nEnq = Math.max(f.zones.length || 1, Math.ceil(n / (6 * jours * 0.9)));
  const dom = domaineDe(`${f.theme} ${f.objectif}`);
  const mg = marge(n);
  const mgProfil = f.cible.length ? marge(Math.floor(n / f.cible.length)) : null;

  // assistant
  $("#ass-rail").style.transform = `translateX(-${E.etape * 100}%)`;
  document.querySelectorAll(".ass-panneau").forEach((p, k) => p.classList.toggle("actif", k === E.etape));
  document.querySelectorAll(".ass-etape").forEach((b, k) => { b.classList.toggle("actif", k === E.etape); b.classList.toggle("fait", k < E.etape); });
  $("#ass-liquide").style.width = `${((E.etape + 1) / 4) * 100}%`;
  $("#ass-compte").textContent = `${E.etape + 1} / 4`;
  $("#ass-prec").style.visibility = E.etape ? "visible" : "hidden";
  $("#ass-suiv").style.display = E.etape === 3 ? "none" : "";
  $("#v-taille").textContent = n.toLocaleString("fr-FR");
  $("#v-duree").textContent = f.duree;
  ["e-taille", "e-duree"].forEach((id) => { const el = $("#" + id); el.value = f[el.dataset.f]; el.style.setProperty("--p", `${((el.value - el.min) / (el.max - el.min)) * 100}%`); });
  document.querySelectorAll("[data-outil]").forEach((b) => b.classList.toggle("actif", b.dataset.outil === f.outil));
  document.querySelectorAll(".puces-saisie").forEach((box) => {
    const cle = box.dataset.liste;
    box.querySelectorAll(".puce-e").forEach((x) => x.remove());
    const inp = box.querySelector("input");
    f[cle].forEach((v, k) => inp.insertAdjacentHTML("beforebegin", `<span class="puce-e ${cle === "cible" ? (DIRECTION_JS.test(v) ? "dir" : "ope") : ""}">${esc(v)}<button data-retirer="${cle}:${k}" aria-label="Retirer">×</button></span>`));
  });
  $("#e-domaine").innerHTML = f.theme.trim() ? `<div class="dom-tete">${ico("sparkle")} Domaine détecté : <b>${esc(dom.nom)}</b></div>
    <div class="dom-inds">${dom.inds.map((x, k) => `<span style="animation-delay:${k * 70}ms">${esc(x)}</span>`).join("")}</div><small>Indicateurs proposés dans la note de cadrage, à ajuster ensuite.</small>` : "";
  $("#e-niveaux").innerHTML = f.cible.length ? `<div class="niv-col"><span class="niv dir">Direction</span>${f.cible.filter((c) => DIRECTION_JS.test(c)).map((c) => `<em>${esc(c)}</em>`).join("") || "<em class='vide-n'>—</em>"}</div>
    <div class="niv-col"><span class="niv ope">Opérationnel</span>${f.cible.filter((c) => !DIRECTION_JS.test(c)).map((c) => `<em>${esc(c)}</em>`).join("") || "<em class='vide-n'>—</em>"}</div>` : "";
  $("#e-recap").innerHTML = [["Thème", f.theme], ["Objectif", f.objectif], ["Cible", f.cible.join(", ")], ["Zones", f.zones.join(", ")],
    ["Secteur", f.secteur || "Secteur formel"], ["Taille", `${n} répondants`], ["Durée", `${f.duree} jours`], ["Outil", f.outil === "kobo" ? "KoboToolbox" : "QuestionPro"],
    ["Budget", f.cout ? `${f.cout} FCFA` : "Non renseigné"]].map(([k, v]) => `<div><span>${k}</span><b class="${v ? "" : "manque"}">${esc(v || "à compléter")}</b></div>`).join("");

  // aperçu vivant
  $("#av-papier").innerHTML = `<div class="avp-entete"><img src="/static/logo_datatym.png" alt=""><img src="/static/logo_agiltym.png" alt=""></div>
    <div class="avp-sur">Baromètre Datatym</div>
    <div class="avp-titre ${f.theme ? "" : "fantome"}">${esc(f.theme || "Thème du baromètre")}</div>
    <div class="avp-obj ${f.objectif ? "" : "fantome"}">${esc(f.objectif || "Objectif de l'étude")}</div>
    <div class="avp-trait"></div>
    <div class="avp-meta">${n} répondants · ${esc(f.zones.join(", ") || "zones")} · ${f.duree} jours</div>
    <div class="avp-lignes"><i></i><i></i><i></i><i class="court"></i></div>`;
  $("#av-jauges").innerHTML = [
    [mg ? `±${mg.toFixed(1).replace(".", ",")}` : "–", "pts de marge globale"],
    [mgProfil ? `±${mgProfil.toFixed(1).replace(".", ",")}` : "–", "pts par profil"],
    [nEnq, "enquêteurs estimés"],
    [Math.ceil(n / jours), "questionnaires par jour"],
  ].map(([v, l]) => `<div class="avj"><b>${v}</b><span>${l}</span></div>`).join("");
  const livr = ["Note de cadrage", "Questionnaire et formulaires", "Échantillonnage et formation", "Note méthodologique", "Tableau de bord", "Note de suivi", "Rapport d'analyse"];
  const remplis = [f.theme && f.objectif, f.cible.length, f.zones.length, true].filter(Boolean).length;
  $("#av-chaine").innerHTML = `<div class="avc-titre">Ce qui sera produit</div>` + livr.map((l, k) => `<div class="avc ${k < remplis + 2 ? "pret" : ""}" style="transition-delay:${k * 60}ms"><i></i>${l}</div>`).join("");
}

async function lancerEtude(ev) {
  const m = manquants(2);
  if (m.length) return signalerManquants(m);
  const f = E.f;
  const fiche = { ...f, cible: f.cible.join(", "), zones: f.zones.join(", "), cout: String(f.cout || "").replace(/\D/g, "") };
  const r = rideauLancement();
  try {
    let p = await api("POST", "/api/projets", fiche);
    r.avancer(1);
    p = await api("POST", `/api/projets/${p.slug}/etapes/cadrage/generer`);
    r.avancer(2);
    await new Promise((ok) => setTimeout(ok, 900));
    S.projet = p;
    r.fermer(() => { location.hash = `#/p/${p.slug}/cadrage`; });
  } catch (e) {
    r.fermer();
    toast(e.message, "erreur");
  }
}

/** Séquence plein écran pendant la création de l'étude. */
function rideauLancement() {
  const R = $("#rideau");
  const lignes = ["Enregistrement de la fiche d'entrée", "Détection du domaine et choix des indicateurs", "Rédaction de la note de cadrage", "Mise en forme à la charte Datatym"];
  R.innerHTML = `<div class="liquide" aria-hidden="true"><i class="goutte g1"></i><i class="goutte g2"></i><i class="goutte g4"></i></div><div class="grain"></div>
    <div class="rid-contenu"><div class="rid-anneau"><svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="52"/><circle class="arc" cx="60" cy="60" r="52"/></svg><img src="/static/favicon.svg" alt=""></div>
    <h2>Lancement de l'étude</h2><ul id="rid-l">${lignes.map((l, k) => `<li class="${k ? "" : "encours"}">${l}</li>`).join("")}</ul></div>`;
  R.hidden = false;
  requestAnimationFrame(() => R.classList.add("ouvert"));
  let k = 0;
  const tic = setInterval(() => { if (k < 2) { k++; maj(); } }, 1100);
  function maj() { R.querySelectorAll("#rid-l li").forEach((li, i) => { li.className = i < k ? "fait" : i === k ? "encours" : ""; }); }
  return {
    avancer(n) { k = Math.max(k, n + 1); maj(); },
    fermer(apres) {
      clearInterval(tic);
      k = lignes.length; maj();
      setTimeout(() => { R.classList.remove("ouvert"); R.classList.add("sortie"); setTimeout(() => { R.hidden = true; R.className = "rideau"; if (apres) apres(); }, 650); }, apres ? 500 : 0);
    },
  };
}
