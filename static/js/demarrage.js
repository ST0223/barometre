/* Démarrage : chargé en dernier, une fois toutes les vues définies */
"use strict";
window.addEventListener("hashchange", router);
window.addEventListener("beforeunload", (e) => { if (S.sale) { e.preventDefault(); e.returnValue = ""; } });
window.addEventListener("resize", () => placerCurseurOnglet());
window.addEventListener("scroll", () => {
  document.getElementById("nav").classList.toggle("defile", window.scrollY > 20);
}, { passive: true });
chargerParams().catch(() => {}).finally(router);
