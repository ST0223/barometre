# Plateforme Datatym — automatisation des baromètres

De la fiche d'entrée (7 paramètres) au rapport d'analyse : chaque livrable est généré au format Datatym,
modifiable dans l'interface ou dans Word, validé avant de lancer le suivant. Une correction faite en amont
se répercute sur les documents suivants.

## Démarrer

Double-cliquer sur `lancer.bat`, ou :

```
pip install -r requirements.txt
python app.py
```

L'interface s'ouvre sur http://127.0.0.1:8765 (port modifiable avec la variable `PORT`).

## Les pages

| Page | Rôle |
|---|---|
| **Accueil** | Présente le cabinet et tout le parcours d'une étude baromètre : fond liquide animé, pile de documents en 3D, cartes de phases empilées au défilement, piliers de méthode, carrousel minuté des modèles de baromètres |
| **Lancer une étude** | Assistant en 4 temps (sujet, cible, terrain, lancement) avec modèles Datatym, aperçu vivant de la note de cadrage, marge d'erreur et nombre d'enquêteurs calculés en direct, séquence de lancement plein écran |
| **Mes études** | Portefeuille filtrable, répartition des études par étape, cartes inclinables |
| **Étude** (projet) | Bandeau à la couleur de l'étape, chaîne des 8 étapes, transitions directionnelles, voile animé pendant la génération, tampon « Validé », tableau de bord de collecte animé |
| **Paramètres** | Rédaction assistée par Claude (cadre lumineux animé) et textes du cabinet |

Les animations respectent le réglage système « réduire les animations ».

## La chaîne de production

| Étape | Livrables produits |
|---|---|
| 0. Fiche d'entrée | Thème, objectif, cible, zones/secteur, taille, durée, coût (facultatif) |
| 1. Note de cadrage | Note de cadrage (.docx/.pdf) avec la liste des indicateurs |
| 2. Questionnaire | Versions terrain et digitale, dictionnaire des variables, XLSForm Kobo, import QuestionPro |
| 3. Échantillonnage | Note d'échantillonnage, note de recrutement, calendrier et quotas (.xlsx), PowerPoint de formation, XLSForm avec la liste des enquêteurs |
| 4. Méthodologie | Note méthodologique, assemblée depuis les étapes 1 à 3 |
| 5. Collecte | Tableau de bord (import CSV/Excel, API KoboToolbox, ou données de test simulées) |
| 6. Note de suivi | Réalisé contre prévu, complétion, incidents, qualité |
| 7. Rapport d'analyse | Indicateurs calculés, graphiques, lecture par profil et par zone, messages clés |

Chaque étape propose : **Aperçu** (rendu fidèle du document), **Paramètres** (indicateurs, questions, quotas…),
**Rédaction** (édition libre des sections rédigées), téléchargement Word et export PDF (via Microsoft Word).

Règles de propagation :
- Valider une étape archive ses fichiers dans `projets/<baromètre>/versions/<étape>_v<N>/`.
- Rouvrir une étape (ou modifier la fiche) marque les étapes suivantes « à mettre à jour ».
- Les sections rédigées à la main sont conservées lors des mises à jour ; les sections calculées
  (tableaux d'indicateurs, quotas, résultats) sont toujours reconstruites à partir des paramètres.
- Un indicateur désactivé dans le cadrage disparaît du questionnaire et du dictionnaire.

## Rédaction assistée par Claude (facultatif)

Sans clé API, la rédaction s'appuie sur des règles et une banque d'indicateurs (climat des affaires,
numérique/IA, emploi/talents, générique). Dans **Paramètres**, une clé API Anthropic permet à Claude
de proposer des indicateurs et des textes adaptés au thème, et de rédiger les messages clés du rapport.

## Organisation du code

```
app.py                 serveur web (API + interface)
datatym/
  config.py            chemins, couleurs, paramètres locaux
  charte.py            charte Word : Times New Roman 12, interligne 1,5, justifié, logos Datatym et Agiltym
  banque.py            types d'indicateurs, questions, modalités, modes de calcul
  moteur.py            génération, validation, propagation, versions, export PDF
  formulaires.py       dictionnaire, XLSForm, import QuestionPro
  formation.py         PowerPoint de formation des enquêteurs
  llm.py               appel à Claude (facultatif)
  etapes/              une logique par livrable (cadrage … rapport)
static/                interface sans dépendance
  app.css, pages.css   styles communs et identité de chaque page
  app.js               cœur : API, projet, éditeurs, tableau de bord
  js/anim.js           apparitions, compteurs, parallaxe, inclinaison 3D, éclats
  js/accueil.js        page d'accueil
  js/etude.js          assistant « Lancer une étude »
projets/               un dossier par baromètre : projet.json, livrables, versions, données, graphiques
```

## Points à confirmer avec le cabinet

- Format d'import QuestionPro : le fichier texte suit la convention « une question par paragraphe,
  une réponse par ligne » ; à vérifier sur le compte QuestionPro de Datatym.
- Modèles : les mises en page reprennent la structure des exemplaires fournis (note de cadrage,
  questionnaire, rapport Gen Z, formation). Les exemplaires de note d'échantillonnage, méthodologique
  et de suivi n'ayant pas été fournis, leur structure est une proposition.
- Règle de nommage `Barometre_Theme_Document_vN` : proposition de la feuille de route, à confirmer.
