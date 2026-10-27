/* Page d'accueil : le cabinet et le parcours complet d'une étude baromètre */
"use strict";

const MODELES = [
  { cle: "affaires", sur: "Conjoncture", titre: "Climat des affaires", mot: "CONFIANCE",
    desc: "Mesurer la confiance des entreprises, l'activité, la trésorerie et les intentions d'investissement, profil par profil.",
    theme: "Climat des affaires dans le commerce formel", objectif: "Mesurer la confiance des entreprises et anticiper l'évolution de leur activité",
    cible: "DG, responsables, vendeurs", secteur: "Commerce formel", fond: ["#081F5C", "#0087E0", "#00B4D8"], indicateurs: ["Indice de confiance", "Solde d'activité", "Perspectives d'emploi", "Contraintes"] },
  { cle: "numerique", sur: "Transformation", titre: "Numérique et IA", mot: "MATURITÉ",
    desc: "Suivre l'adoption de l'IA, le niveau de digitalisation, les freins et les priorités d'investissement des organisations.",
    theme: "Adoption de l'IA et transformation numérique des entreprises", objectif: "Mesurer la maturité numérique et l'adoption de l'IA dans les organisations",
    cible: "Dirigeants, DSI, employés", secteur: "", fond: ["#000F22", "#334EAC", "#7096D1"], indicateurs: ["Indice de maturité", "Usage de l'IA", "Freins", "Intentions 2027"] },
  { cle: "emploi", sur: "Capital humain", titre: "Emploi et talents", mot: "ENGAGEMENT",
    desc: "Comprendre la satisfaction, la reconnaissance, le pouvoir d'achat et les intentions de mobilité des actifs.",
    theme: "Engagement et mobilité des talents", objectif: "Mesurer la satisfaction, l'engagement et les intentions de mobilité des actifs",
    cible: "Salariés, managers, DRH", secteur: "", fond: ["#03045E", "#0077B6", "#90E0EF"], indicateurs: ["Indice de confiance des actifs", "Satisfaction", "Intention de départ", "Attentes"] },
  { cle: "opinion", sur: "Société", titre: "Opinion et consommation", mot: "PERCEPTION",
    desc: "Suivre la perception des ménages sur le pouvoir d'achat, les prix et les services, édition après édition.",
    theme: "Pouvoir d'achat et perception des ménages", objectif: "Suivre la perception des ménages sur le pouvoir d'achat et les services",
    cible: "Chefs de ménage, jeunes actifs", secteur: "", fond: ["#081F5C", "#5B86B6", "#C0E6FD"], indicateurs: ["Indice synthétique", "Situation actuelle", "Perspectives", "Attentes"] },
];

const PHASES = [
  { n: "01", mot: "CADRER", titre: "Note de cadrage", desc: "Contexte, objectifs, cible, champ et taille visée. Surtout : la liste des indicateurs recherchés, base de tout le reste.", liv: ["Note de cadrage", "Indicateurs", "Précision statistique"], ic: "target", c: "#0087E0" },
  { n: "02", mot: "QUESTIONNER", titre: "Questionnaire", desc: "Des questions simples tirées des indicateurs, adaptées à chaque profil, en version terrain et digitale, en 15 minutes au plus.", liv: ["Terrain et digital", "Dictionnaire", "XLSForm Kobo", "QuestionPro"], ic: "edit", c: "#334EAC" },
  { n: "03", mot: "ÉCHANTILLONNER", titre: "Plan de terrain", desc: "Quotas par zone et par profil, répartition par enquêteur, calendrier jour par jour, budget, recrutement et formation.", liv: ["Quotas", "Calendrier", "Budget de collecte", "Recrutement", "Formation PowerPoint"], ic: "users", c: "#00B4D8" },
  { n: "04", mot: "DOCUMENTER", titre: "Note méthodologique", desc: "La méthode consolidée automatiquement : échantillonnage, questionnaire, mode de calcul de chaque indicateur, outils.", liv: ["Note méthodologique"], ic: "file", c: "#7096D1" },
  { n: "05", mot: "COLLECTER", titre: "Suivi de la collecte", desc: "Les soumissions alimentent un tableau de bord : avancement par enquêteur, par zone et par quota, écarts au calendrier.", liv: ["Tableau de bord", "Base des soumissions"], ic: "chart", c: "#0077B6" },
  { n: "06", mot: "CONTRÔLER", titre: "Note de suivi", desc: "Réalisé contre prévu, taux de complétion, refus, entretiens trop rapides, incidents : la qualité des données, documentée.", liv: ["Note de suivi des enquêtes"], ic: "check", c: "#081F5C" },
  { n: "07", mot: "ANALYSER", titre: "Rapport d'analyse", desc: "Indicateurs calculés, graphiques, lecture par profil et par zone, messages clés et enseignements pour la décision.", liv: ["Rapport d'analyse", "Graphiques", "Messages clés"], ic: "sparkle", c: "#000F22" },
];

const PILIERS = [
  { nom: "Data", ic: "base", c: "#00B4D8", desc: "Collecter des données fiables : enquêtes par quotas, bases nettoyées, documentées et déposées sur l'espace DATA." },
  { nom: "Insight", ic: "eye", c: "#0087E0", desc: "Faire parler les données : indicateurs calculés, lecture par profil, par zone et par secteur." },
  { nom: "Signal", ic: "signal", c: "#334EAC", desc: "Repérer ce qui change : tendances d'une édition à l'autre, écarts significatifs, alertes." },
  { nom: "Decision", ic: "target", c: "#081F5C", desc: "Traduire les résultats en messages clés et en options claires pour les décideurs." },
  { nom: "Execution", ic: "play", c: "#000F22", desc: "Accompagner la mise en œuvre, puis mesurer son effet à l'édition suivante." },
];

const PRINCIPES = [
  ["Quotas raisonnés", "Zone × profil, marges d'erreur affichées, aucun chiffre publié sous 30 répondants."],
  ["15 minutes", "Des formulations simples, une durée estimée et plafonnée pour chaque profil."],
  ["Validation humaine", "Aucune étape ne démarre sans l'accord du cabinet sur la précédente."],
  ["Contrôle qualité", "Entretiens trop rapides écartés, cohérence vérifiée, rappels de contrôle."],
  ["Reconductible", "Mêmes indicateurs, mêmes échelles : chaque édition devient une tendance."],
];

function miniDoc(type) {
  if (type === "cadrage") return `<div class="md-titre">Note de cadrage</div><div class="md-l l90"></div><div class="md-l l70"></div><div class="md-l l80"></div><div class="md-tab">${"<i></i>".repeat(9)}</div><div class="md-l l60"></div>`;
  if (type === "questionnaire") return `<div class="md-titre">Questionnaire</div>${[1, 2, 3].map(() => `<div class="md-q"><b></b><span><i></i><i></i><i></i><i></i></span></div>`).join("")}`;
  if (type === "tableau") return `<div class="md-titre">Tableau de bord</div><div class="md-kpis"><i></i><i></i><i></i></div><svg viewBox="0 0 200 70" class="md-courbe"><path d="M0 60 L30 52 L60 46 L90 34 L120 30 L150 18 L200 8" /><path class="pv" d="M0 62 L200 4" /></svg>`;
  return `<div class="md-titre">Rapport d'analyse</div><div class="md-barres">${[62, 84, 45, 70, 92, 55].map((h) => `<i style="height:${h}%"></i>`).join("")}</div><div class="md-l l80"></div><div class="md-l l60"></div>`;
}

function vueAccueil(app) {
  document.body.dataset.page = "accueil";
  const presentation = S.params.presentation_datatym || "";
  const enCours = S.projets.slice(0, 3);
  app.innerHTML = `
  <section class="hero2" id="hero">
    <div class="liquide" aria-hidden="true"><i class="goutte g1"></i><i class="goutte g2"></i><i class="goutte g3"></i><i class="goutte g4"></i><i class="goutte g5"></i></div>
    <div class="grain" aria-hidden="true"></div>
    <div class="hero2-contenu">
      <div class="hero2-texte">
        <span class="pastille-live" data-reveal="haut"><i></i> Cabinet d'études, de données et d'IA appliquée</span>
        <h1 class="titre-geant" id="titre-hero">Des baromètres qui éclairent les décisions.</h1>
        <p class="hero2-sous" data-reveal="haut" data-delai="500">Nous mesurons pour <span class="ecrit" id="ecrit"></span><span class="caret"></span></p>
        <div class="hero2-actions" data-reveal="haut" data-delai="650">
          <a class="btn btn-lumiere magn" href="#/nouveau">Lancer une étude ${ico("play")}</a>
          <button class="btn btn-verre" data-defile="cabinet">Découvrir le cabinet</button>
        </div>
        <div class="hero2-chiffres">
          ${[[7, "paramètres à saisir"], [16, "livrables produits"], [6, "formats générés : Word, PDF, Excel, PowerPoint…"], [100, "% des documents modifiables"]]
            .map(([v, l], k) => `<div data-reveal="haut" data-delai="${800 + k * 90}"><b data-compte="${v}">0</b><span>${l}</span></div>`).join("")}
        </div>
      </div>
      <div class="pile3d" id="pile" aria-hidden="true">
        <div class="pile-scene" data-profondeur="36">
          ${["rapport", "tableau", "questionnaire", "cadrage"].map((t, k) => `<div class="feuille f${k}">${miniDoc(t)}</div>`).join("")}
          <div class="pile-ombre"></div>
        </div>
        <div class="bulle b1" data-profondeur="-50">${ico("check")} Cadrage validé</div>
        <div class="bulle b2" data-profondeur="-30"><b>±4,9</b> pts de marge</div>
      </div>
    </div>
    <button class="defiler-indice" data-defile="cabinet" aria-label="Défiler"><span></span></button>
  </section>

  <div class="defilant" aria-hidden="true"><div class="piste-def">${Array(2).fill([...PILIERS.map((p) => p.nom), "Études quantitatives", "Baromètres", "Data science", "IA appliquée", "KoboToolbox", "QuestionPro", "Tableaux de bord", "Python · R · Stata", "Afrique de l'Ouest et centrale"].map((x) => `<span>${x}</span><i>✦</i>`).join("")).join("")}</div></div>

  <section class="cabinet" id="cabinet">
    <div class="cabinet-gauche">
      <span class="sur" data-reveal="haut">Le cabinet</span>
      <h2 class="titre-section-xl"><span data-reveal="gauche">Discerner.</span><span data-reveal="gauche" data-delai="120">Décider.</span><span data-reveal="gauche" data-delai="240" class="degrade-texte">Disrupter.</span></h2>
    </div>
    <div class="cabinet-droite">
      <p class="cabinet-intro" data-reveal="haut">${esc(presentation)}</p>
    </div>
    <div class="piliers5">
      <span class="sur" data-reveal="haut">Les 5 piliers Datatym</span>
      <div class="piliers">
        ${PILIERS.map((p, k) => `<div class="pilier" style="--c:${p.c}" data-reveal="haut" data-delai="${k * 120}"><span class="pilier-num">0${k + 1}</span><div class="pilier-ic">${ico(p.ic)}</div><h3>${p.nom}</h3><p>${p.desc}</p></div>`).join("")}
      </div>
    </div>
  </section>

  <section class="empile" id="parcours" style="height:${(PHASES.length + 1) * 75}vh">
    <div class="empile-scene">
      <div class="mot-fond" id="mot-fond">${PHASES[0].mot}</div>
      <div class="empile-entete">
        <span class="sur">Ce que nous faisons pour une étude baromètre</span>
        <div class="empile-compteur"><b id="ph-num">01</b> / 0${PHASES.length}</div>
      </div>
      <div class="empile-cartes">
        ${PHASES.map((ph, k) => `
          <article class="carte-phase" style="--c:${ph.c};z-index:${k + 1}">
            <div class="cp-num">${ph.n}</div>
            <div class="cp-corps">
              <span class="cp-mot">${ph.mot}</span>
              <h3>${ph.titre}</h3>
              <p>${ph.desc}</p>
              <div class="cp-livrables">${ph.liv.map((l) => `<span>${esc(l)}</span>`).join("")}</div>
            </div>
            <div class="cp-ic">${ico(ph.ic)}</div>
          </article>`).join("")}
      </div>
      <div class="empile-progres"><i id="empile-barre"></i></div>
    </div>
  </section>

  <section class="methode">
    <div class="methode-texte">
      <span class="sur" data-reveal="haut">Notre méthode</span>
      <h2 class="titre-section-l" data-reveal="haut" data-delai="80">Cinq principes, appliqués à chaque édition.</h2>
      <p class="aide-l" data-reveal="haut" data-delai="160">Survolez un pilier pour le déplier.</p>
    </div>
    <div class="palette" data-reveal="groupe">
      ${PRINCIPES.map(([t, d], k) => `<div class="pilule p${k}" style="--d:${k * 120}ms" tabindex="0"><span class="pl-num">0${k + 1}</span><b>${t}</b><p>${d}</p></div>`).join("")}
    </div>
  </section>

  <section class="vitrine" id="vitrine">
    <div class="vitrine-scene" id="vitrine-scene">
      <div class="vitrine-fond" id="vitrine-fond"></div>
      <div class="grain" aria-hidden="true"></div>
      <div class="vitrine-geant" id="vitrine-geant"></div>
      <div class="vitrine-texte" id="vitrine-texte"></div>
      <div class="vitrine-cartes" id="vitrine-cartes"></div>
      <div class="vitrine-nav">
        <button class="rond-nav" data-vit="-1" aria-label="Précédent">${ico("back")}</button>
        <button class="rond-nav" data-vit="1" aria-label="Suivant" style="transform:scaleX(-1)">${ico("back")}</button>
        <span class="vitrine-num" id="vitrine-num">01</span>
      </div>
    </div>
  </section>

  ${enCours.length ? `
  <section class="encours">
    <div class="encours-tete"><div><span class="sur" data-reveal="haut">Vos études</span><h2 class="titre-section-l" data-reveal="haut">Reprendre là où vous en étiez</h2></div>
      <a class="btn" href="#/etudes" data-reveal="haut">Toutes les études ${ico("back").replace("<svg", '<svg style="transform:scaleX(-1)"')}</a></div>
    <div class="grille-projets">${enCours.map((p, k) => cartePro(p, k)).join("")}</div>
  </section>` : ""}

  <section class="appel">
    <div class="liquide calme" aria-hidden="true"><i class="goutte g1"></i><i class="goutte g3"></i><i class="goutte g5"></i></div>
    <div class="grain" aria-hidden="true"></div>
    <a class="cadre-crochets" href="#/nouveau">
      <i class="cr hg"></i><i class="cr hd"></i><i class="cr bg"></i><i class="cr bd"></i>
      <span class="cc-gauche">(LANCER)</span><span class="cc-centre">${ico("play")}</span><span class="cc-droite">UNE ÉTUDE</span>
    </a>
    <p data-reveal="haut">Sept paramètres. Seize livrables. Zéro ressaisie.</p>
  </section>

  <footer class="pied">
    <img src="/static/logo_datatym_blanc.png" alt="Datatym">
    <span>Plateforme de production des baromètres · Discerner. Décider. Disrupter.</span>
  </footer>`;

  // animations propres à l'accueil
  A.decouper($("#titre-hero"), 90);
  A.machineAEcrire($("#ecrit"), ["mesurer la confiance.", "suivre l'opinion.", "anticiper les tendances.", "éclairer les décisions."]);
  A.reveler(app);
  A.compter(app);
  A.parallaxe($("#hero"));
  A.magnetique(".magn", app);
  A.incliner(".pilier", 10, app);
  A.incliner(".carte-projet", 7, app);
  A.halo(true);
  app.querySelectorAll("[data-defile]").forEach((b) => (b.onclick = () => document.getElementById(b.dataset.defile).scrollIntoView({ behavior: "smooth" })));

  // cartes empilées pilotées par le défilement
  const sec = $("#parcours");
  const cartes = [...sec.querySelectorAll(".carte-phase")];
  const motFond = $("#mot-fond");
  let courant = -1;
  A.surDefilement(() => {
    const n = PHASES.length;
    const prog = A.progression(sec) * (n - 1);
    cartes.forEach((c, k) => {
      const p = k === 0 ? 1 : Math.min(1, Math.max(0, prog - (k - 1)));
      const dessus = Math.max(0, Math.floor(prog) - k);
      const ty = (1 - p) * 115;
      const rot = (1 - p) * (k % 2 ? -7 : 7);
      const ech = 1 - dessus * 0.045;
      c.style.transform = `translate(-50%, calc(-50% + ${ty}vh - ${dessus * 18}px)) rotate(${rot}deg) scale(${ech})`;
      c.style.filter = dessus ? `brightness(${1 - dessus * 0.08})` : "";
    });
    const idx = Math.min(n - 1, Math.max(0, Math.round(prog)));
    if (idx !== courant) {
      courant = idx;
      motFond.classList.remove("change");
      void motFond.offsetWidth;
      motFond.textContent = PHASES[idx].mot;
      motFond.classList.add("change");
      $("#ph-num").textContent = PHASES[idx].n;
    }
    $("#empile-barre").style.width = `${(A.progression(sec) * 100).toFixed(1)}%`;
    const nav = $("#nav");
    nav.classList.toggle("sur-sombre", window.scrollY < window.innerHeight - 80);
  });

  // carrousel minuté des baromètres
  let iv = 0;
  const peindre = (sens = 1) => {
    const m = MODELES[iv];
    const scene = $("#vitrine-scene");
    scene.style.setProperty("--f1", m.fond[0]); scene.style.setProperty("--f2", m.fond[1]); scene.style.setProperty("--f3", m.fond[2]);
    $("#vitrine-geant").innerHTML = `<span class="entre">${m.mot}</span>`;
    $("#vitrine-texte").innerHTML = `<div class="entre"><span class="sur">${esc(m.sur)}</span><h2>${esc(m.titre)}</h2><p>${esc(m.desc)}</p>
      <div class="vt-ind">${m.indicateurs.map((x) => `<span>${esc(x)}</span>`).join("")}</div>
      <a class="btn btn-lumiere" href="#/nouveau?modele=${m.cle}">Lancer ce baromètre ${ico("play")}</a></div>`;
    const autres = [1, 2, 3].map((d) => MODELES[(iv + d) % MODELES.length]);
    $("#vitrine-cartes").innerHTML = autres.map((o, k) => `
      <button class="vc ${sens > 0 ? "glisse" : "glisse-inv"}" style="--f1:${o.fond[0]};--f2:${o.fond[1]};animation-delay:${k * 80}ms" data-aller="${MODELES.indexOf(o)}">
        <span class="vc-sur">${esc(o.sur)}</span><b>${esc(o.titre)}</b>${k === 0 ? '<i class="vc-progres"></i>' : ""}</button>`).join("");
    $("#vitrine-num").textContent = `0${iv + 1}`;
    $("#vitrine-cartes").querySelectorAll("[data-aller]").forEach((b) => (b.onclick = () => { iv = +b.dataset.aller; peindre(1); relancer(); }));
  };
  let minuterie;
  const relancer = () => { clearInterval(minuterie); if (!A.reduit) minuterie = setInterval(() => { iv = (iv + 1) % MODELES.length; peindre(1); }, 6500); };
  A.garder(() => clearInterval(minuterie));
  app.querySelectorAll("[data-vit]").forEach((b) => (b.onclick = () => { iv = (iv + +b.dataset.vit + MODELES.length) % MODELES.length; peindre(+b.dataset.vit); relancer(); }));
  peindre();
  relancer();
}
