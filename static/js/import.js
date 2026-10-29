/* Lancer une étude à partir d'une note de cadrage déjà rédigée (Word), avec ou sans son questionnaire */
"use strict";

function vueImport(app) {
  document.body.dataset.page = "etude";
  app.innerHTML = `
  <section class="import">
    <span class="sur" data-reveal="haut">Nouvelle étude</span>
    <h1 class="titre-section-l" data-reveal="haut" data-delai="60">Importer une note de cadrage</h1>
    <p class="aide-l" data-reveal="haut" data-delai="120">La note est lue, vous vérifiez ce qui a été compris, puis l'étude est créée. Joignez le questionnaire s'il est déjà rédigé :
      ses questions, leurs codes et leurs conditions sont repris tels quels. Les documents d'origine restent disponibles dans l'étude.</p>
    <div id="import-zone"></div>
  </section>`;
  A.reveler(app);
  depotImport();
}

function depotImport() {
  const z = $("#import-zone");
  const fichier = (id, titre, aide, obligatoire) => `
    <label class="depot" for="${id}">
      <input type="file" id="${id}" accept=".docx">
      <span class="depot-ico">${ico("file")}</span>
      <b>${titre} ${obligatoire ? '<span class="obl">*</span>' : '<span class="ex">facultatif</span>'}</b>
      <small id="${id}-nom">${aide}</small>
    </label>`;
  z.innerHTML = `
    <div class="carte"><div class="carte-corps">
      <div class="depots">
        ${fichier("imp-note", "Note de cadrage", "Document Word (.docx) déjà rédigé et validé", true)}
        ${fichier("imp-quest", "Questionnaire", "Document Word (.docx) : format technique (N°, Variable, Question, Modalités…) ou terrain (Code, Question, Consigne, Réponses)", false)}
      </div>
      <div class="pied-form"><a class="btn" href="#/nouveau">Saisir la fiche à la place</a>
        <button class="btn btn-primaire" id="imp-analyser">${ico("eye")} Analyser les documents</button></div>
    </div></div>`;
  ["imp-note", "imp-quest"].forEach((id) => {
    $("#" + id).onchange = (ev) => {
      const f = ev.target.files[0];
      $(`#${id}-nom`).innerHTML = f ? `<b>${esc(f.name)}</b>` : "";
      ev.target.closest(".depot").classList.toggle("rempli", !!f);
    };
  });
  $("#imp-analyser").onclick = (ev) => occupe(ev.currentTarget, async () => {
    const note = $("#imp-note").files[0];
    if (!note) return toast("Choisissez d'abord la note de cadrage (Word).", "erreur");
    const form = new FormData();
    form.append("note", note);
    const q = $("#imp-quest").files[0];
    if (q) form.append("questionnaire", q);
    verifImport(await api("POST", "/api/import/analyser", undefined, form));
  });
}

function verifImport(r) {
  const p = r.proposition;
  const z = $("#import-zone");
  const blocs = {};
  p.indicateurs.forEach((i) => (blocs[i.bloc || "Résultats"] = blocs[i.bloc || "Résultats"] || []).push(i));
  const origine = { questionnaire: "repris du questionnaire, une question par indicateur", note: "repris du tableau de la note", aucune: "aucun : ceux de la banque Datatym seront proposés" }[p.origine_indicateurs];
  const nbCond = p.indicateurs.filter((i) => i.condition).length;
  z.innerHTML = `
    <div class="carte" style="margin-bottom:16px"><div class="carte-titre"><h3>${ico("check")} Ce qui a été compris</h3>
      <span class="aide">${esc(r.fichiers.note)}${r.fichiers.questionnaire ? ` + ${esc(r.fichiers.questionnaire)}` : ""}</span></div>
      <div class="carte-corps">
        <div class="imp-chiffres">
          ${[[p.contexte.length, "paragraphes de contexte"], [p.objectifs.length, "objectifs spécifiques"], [p.indicateurs.length, "indicateurs"], [nbCond, "conditions d'affichage"]]
            .map(([v, l]) => `<div><b>${v}</b><span>${l}</span></div>`).join("")}
        </div>
        <p class="aide">Indicateurs ${origine}.</p>
        ${r.notes.length ? `<div class="bandeau alerte">${ico("alert")}<div><b>À vérifier :</b><ul style="margin:6px 0 0;padding-left:18px">${r.notes.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div></div>` : ""}
        ${p.indicateurs.length ? `<details class="imp-details"><summary>Voir les indicateurs par bloc</summary>
          ${Object.entries(blocs).map(([b, l]) => `<h4>${esc(b)} <span class="aide">${l.length}</span></h4><ul>${l.map((i) => `<li>${esc(i.libelle)}${i.condition ? ' <span class="tag">conditionnelle</span>' : ""}${i.exclut ? ' <span class="tag">exclusion</span>' : ""}</li>`).join("")}</ul>`).join("")}
        </details>` : ""}
      </div></div>
    <div class="carte"><div class="carte-titre"><h3>${ico("edit")} Fiche de l'étude</h3><span class="aide">pré-remplie à partir des documents, modifiable</span></div>
      <div class="carte-corps">
        ${formFiche(p.fiche)}
        <label class="bascule" style="margin-top:14px"><input type="checkbox" id="imp-valider" checked> La note est déjà validée : la valider dans la plateforme et générer le questionnaire</label>
        <div class="pied-form"><button class="btn" id="imp-retour">${ico("back")} Changer de documents</button>
          <button class="btn btn-primaire" id="imp-creer">${ico("play")} Créer l'étude</button></div>
      </div></div>`;
  A.reveler(z);
  $("#imp-retour").onclick = depotImport;
  $("#imp-creer").onclick = (ev) => occupe(ev.currentTarget, async () => {
    const valider = $("#imp-valider").checked;
    const projet = await api("POST", "/api/import/creer", { id: r.id, fiche: lireFiche(), valider });
    S.projet = projet;
    toast(valider ? "Étude créée : note validée, questionnaire généré." : "Étude créée à partir de la note.", "succes");
    location.hash = `#/p/${projet.slug}/${valider ? "questionnaire" : "cadrage"}`;
  });
}
