/* Boîte à outils d'animation — partagée par toutes les pages, nettoyée à chaque changement de vue */
"use strict";

const A = (() => {
  const reduit = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let nettoyages = [];

  const garder = (fn) => nettoyages.push(fn);
  function nettoyer() {
    nettoyages.forEach((f) => { try { f(); } catch { /* déjà nettoyé */ } });
    nettoyages = [];
  }

  function surDefilement(fn) {
    let attente = false;
    const h = () => {
      if (attente) return;
      attente = true;
      requestAnimationFrame(() => { attente = false; fn(); });
    };
    window.addEventListener("scroll", h, { passive: true });
    window.addEventListener("resize", h);
    garder(() => { window.removeEventListener("scroll", h); window.removeEventListener("resize", h); });
    fn();
  }

  function intervalle(fn, ms) { const id = setInterval(fn, ms); garder(() => clearInterval(id)); return id; }
  function delai(fn, ms) { const id = setTimeout(fn, ms); garder(() => clearTimeout(id)); return id; }

  /** Apparition au défilement : [data-reveal="haut|gauche|droite|zoom|flou"] + data-delai (ms). */
  function reveler(racine = document) {
    const els = racine.querySelectorAll("[data-reveal]:not(.vu)");
    if (reduit) { els.forEach((e) => e.classList.add("vu")); return; }
    const io = new IntersectionObserver((entrees) => {
      entrees.forEach((en) => {
        if (!en.isIntersecting) return;
        const el = en.target;
        el.style.transitionDelay = `${el.dataset.delai || 0}ms`;
        el.classList.add("vu");
        io.unobserve(el);
      });
    }, { threshold: 0.15, rootMargin: "0px 0px -6% 0px" });
    els.forEach((e) => io.observe(e));
    garder(() => io.disconnect());
  }

  /** Compteurs : [data-compte="12.5"] data-dec="1" data-suffixe=" %" */
  function compter(racine = document) {
    const els = racine.querySelectorAll("[data-compte]");
    const lancer = (el) => {
      const cible = parseFloat(el.dataset.compte) || 0;
      const dec = +(el.dataset.dec || 0);
      const suf = el.dataset.suffixe || "";
      const pre = el.dataset.prefixe || "";
      const fmt = (v) => pre + v.toLocaleString("fr-FR", { minimumFractionDigits: dec, maximumFractionDigits: dec }) + suf;
      if (reduit) { el.textContent = fmt(cible); return; }
      const t0 = performance.now(), duree = +(el.dataset.duree || 1400);
      const pas = (t) => {
        const p = Math.min(1, (t - t0) / duree);
        const e = 1 - Math.pow(1 - p, 4);
        el.textContent = fmt(cible * e);
        if (p < 1) requestAnimationFrame(pas);
      };
      requestAnimationFrame(pas);
    };
    const io = new IntersectionObserver((en) => en.forEach((x) => { if (x.isIntersecting) { lancer(x.target); io.unobserve(x.target); } }), { threshold: 0.4 });
    els.forEach((e) => io.observe(e));
    garder(() => io.disconnect());
  }

  /** Inclinaison 3D d'une carte qui suit la souris. */
  function incliner(selecteur, force = 8, racine = document) {
    if (reduit) return;
    racine.querySelectorAll(selecteur).forEach((el) => {
      const move = (e) => {
        const r = el.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width - 0.5;
        const y = (e.clientY - r.top) / r.height - 0.5;
        el.style.transform = `perspective(900px) rotateX(${-y * force}deg) rotateY(${x * force}deg) translateY(-4px)`;
        el.style.setProperty("--mx", `${(x + 0.5) * 100}%`);
        el.style.setProperty("--my", `${(y + 0.5) * 100}%`);
      };
      const sortie = () => { el.style.transform = ""; };
      el.addEventListener("mousemove", move);
      el.addEventListener("mouseleave", sortie);
      garder(() => { el.removeEventListener("mousemove", move); el.removeEventListener("mouseleave", sortie); });
    });
  }

  /** Parallaxe à la souris : chaque [data-profondeur] se décale selon sa profondeur. */
  function parallaxe(zone) {
    if (reduit || !zone) return;
    const els = zone.querySelectorAll("[data-profondeur]");
    const move = (e) => {
      const r = zone.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width - 0.5;
      const y = (e.clientY - r.top) / r.height - 0.5;
      els.forEach((el) => {
        const p = +el.dataset.profondeur;
        el.style.setProperty("--px", `${x * p}px`);
        el.style.setProperty("--py", `${y * p}px`);
      });
    };
    zone.addEventListener("mousemove", move);
    garder(() => zone.removeEventListener("mousemove", move));
  }

  /** Bouton magnétique : attiré par le curseur. */
  function magnetique(selecteur, racine = document) {
    if (reduit) return;
    racine.querySelectorAll(selecteur).forEach((b) => {
      const move = (e) => {
        const r = b.getBoundingClientRect();
        b.style.transform = `translate(${(e.clientX - r.left - r.width / 2) * 0.25}px, ${(e.clientY - r.top - r.height / 2) * 0.35}px)`;
      };
      const sortie = () => { b.style.transform = ""; };
      b.addEventListener("mousemove", move);
      b.addEventListener("mouseleave", sortie);
      garder(() => { b.removeEventListener("mousemove", move); b.removeEventListener("mouseleave", sortie); });
    });
  }

  /** Machine à écrire qui fait tourner des formulations. */
  function machineAEcrire(el, mots, pause = 1900) {
    if (!el) return;
    if (reduit) { el.textContent = mots[0]; return; }
    let i = 0, n = 0, efface = false;
    const tic = () => {
      const mot = mots[i % mots.length];
      n += efface ? -1 : 1;
      el.textContent = mot.slice(0, n);
      let attente = efface ? 28 : 55;
      if (!efface && n === mot.length) { efface = true; attente = pause; }
      else if (efface && n === 0) { efface = false; i++; attente = 300; }
      delai(tic, attente);
    };
    tic();
  }

  /** Découpe un titre en mots animables (classe .mot, délai progressif). */
  function decouper(el, pas = 70) {
    if (!el) return;
    const mots = el.textContent.trim().split(/\s+/);
    el.innerHTML = mots.map((m, k) => `<span class="mot-cache"><span class="mot" style="animation-delay:${k * pas}ms">${m}</span></span>`).join(" ");
  }

  /** Halo lumineux qui suit le curseur sur les zones sombres. */
  function halo(actif) {
    const h = document.getElementById("halo");
    if (!h) return;
    h.classList.toggle("on", !!actif && !reduit);
    if (!actif || reduit) return;
    const move = (e) => { h.style.transform = `translate(${e.clientX - 300}px, ${e.clientY - 300}px)`; };
    window.addEventListener("mousemove", move);
    garder(() => { window.removeEventListener("mousemove", move); h.classList.remove("on"); });
  }

  /** Progression d'un élément dans la fenêtre (0 → 1). */
  function progression(el) {
    const r = el.getBoundingClientRect();
    const total = r.height - window.innerHeight;
    return Math.min(1, Math.max(0, -r.top / Math.max(1, total)));
  }

  /** Confettis bleus (validation d'une étape). */
  function eclat(x, y, n = 26) {
    if (reduit) return;
    const couleurs = ["#0087E0", "#00B4D8", "#7096D1", "#D0E3FF", "#0E9F6E"];
    for (let k = 0; k < n; k++) {
      const p = document.createElement("i");
      p.className = "eclat";
      const ang = (Math.PI * 2 * k) / n + Math.random() * 0.4;
      const dist = 70 + Math.random() * 90;
      p.style.cssText = `left:${x}px;top:${y}px;background:${couleurs[k % couleurs.length]};--dx:${Math.cos(ang) * dist}px;--dy:${Math.sin(ang) * dist - 30}px;--r:${Math.random() * 360}deg`;
      document.body.appendChild(p);
      setTimeout(() => p.remove(), 1100);
    }
  }

  return { reduit, nettoyer, garder, surDefilement, intervalle, delai, reveler, compter, incliner, parallaxe, magnetique, machineAEcrire, decouper, halo, progression, eclat };
})();
