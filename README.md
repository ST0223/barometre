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
Le serveur se recharge tout seul quand le code Python est modifié : pas besoin de relancer après une mise à jour.
Si la plateforme tourne déjà, un second lancement ouvre simplement le navigateur sur l'instance existante :
pour prendre en compte une mise à jour du code, fermez d'abord la fenêtre du serveur en cours.

## Les pages

| Page | Rôle |
|---|---|
| **Accueil** | Présente le cabinet et tout le parcours d'une étude baromètre : fond liquide animé, pile de documents en 3D, les 5 piliers Datatym (Data, Insight, Signal, Decision, Execution), cartes de phases empilées au défilement, piliers de méthode, carrousel minuté des modèles de baromètres |
| **Lancer une étude** | Assistant en 4 temps (sujet, cible, terrain, lancement) avec modèles Datatym, sélection des pays par espace (UEMOA, CEMAC, Guinée, RD Congo) ou pays par pays, saisie libre de tout autre pays, alerte si moins de 30 répondants par pays, aperçu vivant de la note de cadrage, marge d'erreur et nombre d'enquêteurs calculés en direct, séquence de lancement plein écran |
| **Importer une note de cadrage** | Depuis « Lancer une étude » : note Word déjà rédigée, avec ou sans son questionnaire (format technique ou terrain) ; écran de vérification, puis étude créée, note validée et questionnaire généré ; documents d'origine conservés dans les livrables |
| **Mes études** | Portefeuille filtrable, répartition des études par étape, cartes inclinables |
| **Étude** (projet) | Bandeau à la couleur de l'étape, chaîne des 8 étapes, transitions directionnelles, voile animé pendant la génération, tampon « Validé », tableau de bord de collecte animé |
| **Paramètres** | Textes du cabinet et coûts unitaires de référence |

Les animations respectent le réglage système « réduire les animations ».
Thème clair ou sombre : Paramètres › Apparence, ou bouton dans le menu (Auto suit le réglage de Windows) ; les aperçus de documents restent sur fond blanc.

## La chaîne de production

| Étape | Livrables produits |
|---|---|
| 0. Fiche d'entrée | Thème, objectif, cible, zones/secteur, taille, durée, plafond budgétaire (facultatif) |
| 1. Note de cadrage | Note de cadrage (.docx/.pdf) avec la liste des indicateurs et l'estimation préliminaire du coût (fourchette basse, centrale, haute) |
| 2. Questionnaire | Versions terrain et digitale, dictionnaire des variables, XLSForm Kobo complet (groupes de consentement et d'éligibilité, enquêteur lu dans `liste_enqueteurs.csv`, apparences, exclusivités, indicateurs calculés), import QuestionPro ; conditions d'affichage entre questions, questions de profil avec exclusion (ex. chiffre d'affaires sous le seuil) |
| 3. Échantillonnage | Note d'échantillonnage, note de recrutement adressée aux RH (besoin par pays, profil, calendrier, consignes et exemple de remplissage), fichier Excel des enquêteurs à renseigner par les RH, calendrier et quotas (.xlsx), PowerPoint de formation, `liste_enqueteurs.csv` avec les noms définitifs, budget de collecte (interne) |
| 4. Méthodologie | Note méthodologique, assemblée depuis les étapes 1 à 3 |
| 5. Collecte | Tableau de bord alimenté par l'API KoboToolbox, l'API QuestionPro, un fichier CSV/Excel, ou des données de test simulées : avancement cumulé, carte des pays, suivi par pays, par secteur, par profil et par collecteur, quotas, incidents |
| 6. Note de suivi | Réalisé contre prévu, complétion, incidents, qualité, bilan financier prévu contre réalisé |
| 7. Rapport d'analyse | Indicateurs calculés, graphiques, lecture par profil et par zone, messages clés |
| 8. Clôture | Bilan des étapes, historique complet ; bouton BOUCLER : une archive ZIP (livrables, versions validées, base des soumissions, historique) à télécharger |

Chaque étape propose : **Aperçu** (rendu fidèle du document), **Paramètres** (indicateurs, questions, quotas…),
**Rédaction** (édition libre des sections rédigées), téléchargement Word et export PDF (via Microsoft Word).

Règles de propagation :
- Valider une étape archive ses fichiers dans `projets/<baromètre>/versions/<étape>_v<N>/`.
- Rouvrir une étape (ou modifier la fiche) marque les étapes suivantes « à mettre à jour ».
- Les sections rédigées à la main sont conservées lors des mises à jour ; les sections calculées
  (tableaux d'indicateurs, quotas, résultats) sont toujours reconstruites à partir des paramètres.
- Un indicateur désactivé dans le cadrage disparaît du questionnaire et du dictionnaire.

## Le coût d'une étude

Le coût de revient est construit poste par poste (quantité tirée du plan × coût unitaire), en trois temps :

| Moment | Ce qui est produit |
|---|---|
| Note de cadrage | Fourchette basse, centrale, haute calculée à partir de la fiche ; figée à la génération, c'est la référence annoncée |
| Échantillonnage | Budget de collecte détaillé (document interne), à partir des quotas, enquêteurs, superviseurs, jours et zones ; coûts unitaires et hypothèses modifiables dans l'onglet Paramètres ; chaque poste peut être décoché (exclu du budget) et des postes forfaitaires peuvent être ajoutés |
| Note de suivi | Dépenses réelles saisies dans l'onglet « Bilan financier » ; écarts par poste, coût réel par questionnaire validé, coût des questionnaires écartés |

Le plafond budgétaire de la fiche ne sert qu'à vérifier que l'estimation reste dans l'enveloppe. Aucun montant
ne figure dans la note d'échantillonnage, la note de recrutement ni la formation, qui peuvent circuler hors de Datatym.
Les coûts unitaires livrés sont indicatifs : à remplacer par les tarifs de Datatym dans **Paramètres**.

## Recruter les enquêteurs

1. Étape **Échantillonnage › Paramètres** : bouton « Fichier à envoyer aux RH ». L'envoyer aux RH avec la note
   de recrutement (besoin par pays, profil, calendrier, consignes de remplissage avec un exemple de deux lignes).
2. Les RH renvoient le fichier avec une ligne par enquêteur retenu : Nom, Prénom, Pays de résidence, Ville,
   Téléphone (avec l'indicatif du pays), Mail.
3. « Importer la liste des RH » : la plateforme contrôle le fichier (pays hors de l'étude, mails invalides,
   doublons, nombre d'enquêteurs par pays comparé au besoin, indicatif ajouté s'il manque), puis, à l'enregistrement,
   attribue les identifiants enq1, enq2… pays par pays et met à jour quotas, calendrier, formation et `liste_enqueteurs.csv`.

L'adresse de retour de la liste se règle dans **Paramètres** (repris dans chaque note de recrutement).

## Déployer le formulaire sur KoboToolbox

1. Importer le fichier `…_XLSForm_Kobo_vN.xlsx` comme nouveau projet.
2. Dans **Paramètres › Médias**, joindre `liste_enqueteurs.csv` (nom à conserver tel quel) : il alimente la
   question « Enquêteur » et les champs calculés nom, superviseur et catégorie.
3. Déployer. Le fichier a été contrôlé avec `pyxform`, le convertisseur utilisé par KoboToolbox.

## Synchroniser la collecte avec KoboToolbox

Onglet **Collecte › Données**, carte KoboToolbox : coller le **lien de saisie** du formulaire
(`https://ee.kobotoolbox.org/x/…`), l'adresse du projet ou son identifiant (asset UID), et le **jeton API**
(Kobo : menu du compte › Paramètres du compte › Sécurité › Clé API ; non conservé). La plateforme retrouve
le projet correspondant au lien, puis récupère les soumissions.

## Synchroniser la collecte avec QuestionPro

Onglet **Collecte › Données** : identifiant de l'enquête (survey ID), centre de données (`com`, `eu`, `ca`…)
et clé API QuestionPro (non conservée). Seules les réponses complétées sont importées.

- Les questions sont reconnues par leur code (a2, b1…) s'il est renseigné dans QuestionPro, sinon par le
  numéro « A2. » placé en tête de chaque question par le fichier d'import généré à l'étape Questionnaire.
- Les libellés des réponses sont retraduits en codes (1, 2, 99…) ; les réponses « Autre » sont conservées.
- Pour le suivi par enquêteur, chaque enquêteur partage le lien de l'enquête avec `?custom1=enq1`, `enq2`…

## Rédaction assistée par Claude (masquée)

La rédaction s'appuie sur des règles et une banque d'indicateurs (climat des affaires, numérique/IA,
emploi/talents, générique) : aucune clé API n'est nécessaire. La rédaction assistée par Claude (clé API
Anthropic) est masquée de l'interface ; pour la réafficher, passer `IA_VISIBLE` à `true` dans `static/app.js`.
Claude propose alors des indicateurs et des textes adaptés au thème, et rédige les messages clés du rapport.

## Organisation du code

```
app.py                 serveur web (API + interface)
datatym/
  config.py            chemins, couleurs, paramètres locaux
  charte.py            charte Word : Times New Roman 12, interligne 1,5, justifié, logos Datatym et Agiltym
  banque.py            types d'indicateurs, questions, modalités, modes de calcul
  moteur.py            génération, validation, propagation, versions, export PDF
  budget.py            coût de revient : fourchette du cadrage, budget de collecte, bilan financier
  indice_hc.py         Indice H&C de Maturité IA : barème validé, 5 piliers, 5 niveaux, score par entreprise
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
Resources/             documents de référence, hors Git (confidentiels)
  exemplaires/         modèles fournis par le cabinet (cadrage, questionnaires, XLSForm, formation)
  rapports-reference/  rapports Gen Z (Côte d'Ivoire, Sénégal) servant de modèle au rapport
  logos/               logos d'origine Datatym et Agiltym
  inspirations/        visuels d'inspiration de l'interface
```

## Points à confirmer avec le cabinet

- Format d'import QuestionPro : le fichier texte suit la convention « une question par paragraphe,
  une réponse par ligne » ; à vérifier sur le compte QuestionPro de Datatym.
- Modèles : les mises en page reprennent la structure des exemplaires fournis (note de cadrage,
  questionnaire, rapport Gen Z, formation). Les exemplaires de note d'échantillonnage, méthodologique
  et de suivi n'ayant pas été fournis, leur structure est une proposition.
- Règle de nommage `Barometre_Theme_Document_vN` : proposition de la feuille de route, à confirmer.
