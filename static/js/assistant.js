/* Assistant BAROMAKER : bouton flottant en bas à droite et panneau de discussion avec Claude.
   Sans clé API, l'assistant s'affiche et répond qu'il n'est pas encore branché. */
(function () {
  const IA = { messages: [], ouvert: false, attente: false };

  const ETAPES = { fiche: "fiche de l'étude", cadrage: "note de cadrage", questionnaire: "questionnaire", echantillonnage: "échantillonnage",
    methodologie: "note méthodologique", collecte: "collecte", suivi: "suivi des enquêtes", apurement: "apurement", rapport: "rapport d'analyse" };

  // page ouverte : libellé pour Claude, étude éventuelle et suggestions adaptées
  function ecran() {
    const { h } = lireRoute();
    const page = h[0] === "p" ? "projet" : h[0] || "accueil";
    if (page === "projet" && h[1]) {
      const etape = h[2] || "";
      const lib = ETAPES[etape] || "tableau de l'étude";
      const sugg = etape === "questionnaire"
        ? ["Relis mon questionnaire et signale les défauts", "Propose 5 questions sur l'accès au financement", "Quelles questions manquent pour mes objectifs ?"]
        : etape === "rapport"
          ? ["Quels sont les 3 messages clés à retenir ?", "Comment présenter ces résultats au client ?"]
          : ["Résume l'état de cette étude", "Quelle est la prochaine étape ?", `Que dois-je vérifier sur ${lib === "tableau de l'étude" ? "cette étude" : "la " + lib} ?`];
      return { page: `Étude ouverte, écran ${lib}`, slug: h[1], sugg };
    }
    if (page === "nouveau" || page === "importer") return { page: "Lancer une étude", sugg: [
      "Aide-moi à formuler l'objectif de mon baromètre", "Quelle taille d'échantillon pour 3 pays ?", "Quels profils interroger pour un baromètre sur l'emploi ?"] };
    if (page === "etudes") return { page: "Mes études", sugg: ["Comment comparer deux éditions d'un baromètre ?", "Comment reprendre une étude en cours ?"] };
    if (page === "parametres") return { page: "Paramètres", sugg: ["Comment activer l'assistant IA ?", "Comment fixer les coûts unitaires ?"] };
    return { page: "Accueil", sugg: ["Que fait BAROMAKER ?", "Comment lancer une nouvelle étude ?", "Quelles sont les étapes d'un baromètre ?"] };
  }

  // rendu léger : gras, listes à puces, retours à la ligne
  function rendu(texte) {
    const lignes = esc(texte).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").split("\n");
    let html = "", liste = false;
    for (const l of lignes) {
      const puce = l.match(/^\s*(?:[-•*]|\d+[.)])\s+(.*)$/);
      if (puce) { if (!liste) { html += "<ul>"; liste = true; } html += `<li>${puce[1]}</li>`; continue; }
      if (liste) { html += "</ul>"; liste = false; }
      html += l.trim() ? `<p>${l}</p>` : "";
    }
    return html + (liste ? "</ul>" : "");
  }

  const ETOILE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2.5l2.2 6.6 6.8 2.4-6.8 2.4L12 20.5l-2.2-6.6L3 11.5l6.8-2.4z"/><path d="M19 2.5l.8 2.1 2.2.8-2.2.8-.8 2.1-.8-2.1-2.2-.8 2.2-.8z" opacity=".75"/></svg>';

  const FERMER = '<svg viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12"/></svg>';
  const ENVOYER = '<svg viewBox="0 0 24 24"><path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4z"/></svg>';

  function construire() {
    const fab = document.createElement("button");
    fab.type = "button"; fab.id = "ia-fab"; fab.className = "ia-fab";
    fab.setAttribute("aria-label", "Ouvrir l'assistant BAROMAKER");
    fab.title = "Assistant BAROMAKER";
    fab.innerHTML = ETOILE;
    const pan = document.createElement("section");
    pan.id = "ia-panneau"; pan.className = "ia-panneau"; pan.hidden = true;
    pan.setAttribute("aria-label", "Assistant BAROMAKER");
    pan.innerHTML = `
      <header class="ia-tete">
        <span class="ia-avatar">${ETOILE}</span>
        <div class="ia-titre"><b>Assistant BAROMAKER</b><span id="ia-etat"></span></div>
        <button type="button" class="ia-btn" id="ia-vider" title="Nouvelle conversation" aria-label="Nouvelle conversation">${ico("plus")}</button>
        <button type="button" class="ia-btn" id="ia-fermer" title="Fermer" aria-label="Fermer">${FERMER}</button>
      </header>
      <div class="ia-fil" id="ia-fil" aria-live="polite"></div>
      <form class="ia-saisie" id="ia-form">
        <textarea id="ia-texte" rows="1" placeholder="Pose ta question…" aria-label="Message"></textarea>
        <button type="submit" class="ia-envoyer" aria-label="Envoyer">${ENVOYER}</button>
      </form>`;
    document.body.append(fab, pan);
    fab.classList.toggle("actif", actif());
    fab.onclick = () => basculer(!IA.ouvert);
    $("#ia-fermer").onclick = () => basculer(false);
    $("#ia-vider").onclick = () => { IA.messages = []; dessiner(); $("#ia-texte").focus(); };
    $("#ia-form").onsubmit = (e) => { e.preventDefault(); envoyer($("#ia-texte").value); };
    const ta = $("#ia-texte");
    ta.oninput = () => { ta.style.height = "auto"; ta.style.height = Math.min(ta.scrollHeight, 130) + "px"; };
    ta.onkeydown = (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); envoyer(ta.value); } };
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && IA.ouvert) basculer(false); });
    window.addEventListener("hashchange", () => { if (IA.ouvert) dessiner(); });
  }

  function actif() { return !!(S.params && S.params.ia_active && S.params.cle_definie); }

  function basculer(ouvrir) {
    IA.ouvert = ouvrir;
    $("#ia-panneau").hidden = !ouvrir;
    $("#ia-fab").classList.toggle("ouvert", ouvrir);
    document.body.classList.toggle("ia-ouvert", ouvrir);  // les notes passent à côté du panneau
    $("#ia-fab").setAttribute("aria-expanded", String(ouvrir));
    if (ouvrir) { dessiner(); setTimeout(() => $("#ia-texte").focus(), 60); }
  }

  function dessiner() {
    const on = actif();
    $("#ia-etat").innerHTML = on ? "" :`<i class="ia-point"></i>Non branché — <a href="#/parametres">activer</a>`;
    const fil = $("#ia-fil");
    const accueil = `<div class="ia-msg ia-bot">${rendu(`Bonjour ! Je suis l'assistant de BAROMAKER. Je peux t'aider à formuler une étude, rédiger ou relire des questions, choisir une taille d'échantillon ou lire un résultat.${on ? "" : "\n**Je ne suis pas encore branché** : il faut une clé API Anthropic dans Paramètres pour que je réponde vraiment."}`)}</div>`;
    const sugg = IA.messages.length ? "" : `<div class="ia-sugg">${ecran().sugg.map((s) => `<button type="button" data-ia-sugg="${esc(s)}">${esc(s)}</button>`).join("")}</div>`;
    fil.innerHTML = accueil + IA.messages.map((m) => `<div class="ia-msg ${m.role === "user" ? "ia-moi" : "ia-bot"}${m.erreur ? " ia-erreur" : ""}">${m.role === "user" ? `<p>${esc(m.content).replace(/\n/g, "<br>")}</p>` : rendu(m.content)}${m.lien ? `<a class="ia-lien" href="#/parametres">Ouvrir Paramètres</a>` : ""}</div>`).join("")
      + (IA.attente ? `<div class="ia-msg ia-bot ia-attente"><i></i><i></i><i></i></div>` : "") + sugg;
    fil.querySelectorAll("[data-ia-sugg]").forEach((b) => { b.onclick = () => envoyer(b.dataset.iaSugg); });
    fil.querySelectorAll("a[href='#/parametres']").forEach((a) => { a.onclick = () => basculer(false); });
    fil.scrollTop = fil.scrollHeight;
  }

  async function envoyer(texte) {
    texte = (texte || "").trim();
    if (!texte || IA.attente) return;
    $("#ia-texte").value = ""; $("#ia-texte").style.height = "auto";
    IA.messages.push({ role: "user", content: texte });
    IA.attente = true; dessiner();
    const e = ecran();
    const historique = IA.messages.filter((m) => !m.local).map((m) => ({ role: m.role, content: m.content }));
    try {
      const r = await api("POST", "/api/assistant", { messages: historique, page: e.page, slug: e.slug || null });
      if (!r.actif) IA.messages.push({ role: "assistant", local: true, lien: true,
        content: "Je ne suis pas encore branché, donc je ne peux pas répondre pour l'instant. Pour m'activer : colle une clé API Anthropic dans **Paramètres**, coche « Activer la rédaction assistée par l'IA », puis repose ta question." });
      else IA.messages.push({ role: "assistant", content: r.texte || "(réponse vide)" });
    } catch (err) {
      IA.messages.push({ role: "assistant", local: true, erreur: true, content: err.message });
    }
    IA.attente = false; dessiner();
  }

  document.addEventListener("DOMContentLoaded", construire);
})();
