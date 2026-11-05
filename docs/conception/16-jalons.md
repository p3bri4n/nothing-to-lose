# 16 — Jalons et périmètre

[← Sommaire](README.md)

## Phase 0 — Prototype de validation du concept [Décidé]

Avant le MVP. Une seule question : **des zombies Laya face à des survivants LLM, est-ce que ça fonctionne et est-ce intéressant à regarder ?**

**Dans le prototype** : bâtiments extrudés simples, rues, barricade, 5 quartiers et lieux nommés ; entités en capsules colorées ; combat simplifié (tir avec munitions, corps à corps) ; morsure = transformation après un délai fixe ; perception par la vue et une **alerte dans un rayon fixe** (provisoire, à la place du son) ; munitions et vivres dans des bâtiments connus ; radio en texte propre.

**Repoussé** : son en onde, odeur et vent, radio dégradée, stress, fatigue, moral, confiance, déduction sociale, exclusion, intérieurs, alphas, XP, caméras, antennes, commandant, bodycams, transparences.

| # | Jalon | Contenu | Outils de retour ([22](22-boucle-de-retour.md)) | Critère de réussite |
|---|---|---|---|---|
| PP | Préparation de l'environnement | Versions d'outils figées (`mise.toml`) ; hooks Claude Code (formatage après modification) ; hooks Git avant commit (`gitleaks`, liens de la documentation) ; circuit Git des agents (une branche et une pull request par tâche via `gh`, modèle de pull request avec liste de contrôle, modèles de tickets « bug » avec seed/tick/agent et « décision ») ; sandbox reporté après PP (décision [0015](../decisions/0015-sandbox-reporte-apres-pp.md)) | — | Un commit contenant un faux secret est bloqué ; une modification de fichier est formatée automatiquement ; une pull request de test passe la CI avec la liste de contrôle remplie ; mêmes versions d'outils en local et en CI |
| P0 | Carte minimale | Bake OSM simplifié **à partir d'un extrait daté et mis en cache**, grille de navigation à 2 m, vue Three.js de dessus | Captures d'écran automatisées (Playwright) | Le centre de Toulouse s'affiche ; rues dégagées, bâtiments bloquants ; deux bakes du même extrait donnent des fichiers identiques |
| P1 | Simulation de base | Cœur Rust (ECS minimal), steering, flow fields, combat, morsure → transformation ; survivants scriptés, zombies en IA simple ; WASM + headless | `just sim`, journal, `summary.json` **avec les versions de tout ce qui influence la partie** (commit, extrait OSM, et plus tard checkpoint Laya et modèle LLM), invariants | ~1 000 zombies fluides face à 4 survivants scriptés ; zéro violation d'invariant sur 20 seeds |
| P2 | Pont IA | Broker Python (WebSocket), contrat de décision, deadline et repli, perception quantifiée, replay ; **doublures de Laya et du LLM** (`--brain=fake` à règles simples, `--brain=replay` rejouant des réponses enregistrées dans `tests/cassettes/`, `--brain=real`) ; **trois benchmarks de la machine** (débit du LLM avec 1/4/8 requêtes, latence de Laya en batch, coût CPU d'un tick pour 1 000/3 000/5 000 agents) | `just inspect`, `targets.toml`, `just eval` et référence | Une décision externe pilote un agent ; replay identique ; la CI teste le pont IA sans GPU grâce aux doublures ; benchmarks consignés dans `docs/technique/` |
| P3 | Zombies Laya | Schéma à 6 intentions, ~500 états annotés par le LLM, fine-tuning, calibration, barres de probabilité | Évaluation Laya (précision, ECE), comparaison avec l'IA simple | Précision ≥ ~0,75 ; ≥ 95 % des décisions dans les délais ; différence visible |
| P4 | Survivants LLM | 4 héros via TabbyAPI, plan JSON, fouille, objectif simple | Taux de JSON valides, cohérence parole / action, marqueurs de retour dans le viewer | Plan < 5 s ; répliques cohérentes ; actions conformes aux annonces |
| P5 | Test du concept | 5 à 10 parties enregistrées et annotées, mesures, revue | `report.md`, `feedback/` | Décision : continuer, ajuster ou changer d'approche ; liste priorisée des systèmes à ajouter |

**PP se fait avant P0** : c'est un investissement d'une session qui évite des frictions pendant tout le prototype. Les benchmarks de P2 doivent être faits avant P3 : ils fixent les effectifs réalistes et les budgets de latence.

P3 et P4 sont indépendants une fois P2 terminé ; commencer par P3 (Laya est l'inconnue technique). L'arbre de décision des zombies du prototype : quatre déclencheurs (survivant vu, alerte entendue, cible perdue, rien depuis 10 s), options filtrées selon la situation, attaque au contact en règle fixe, hésitation sous un seuil de confiance (voir [04](04-ia-laya.md)).

## Après le prototype

Chaque jalon valide une brique technique **et** produit un contenu publiable.

| # | Jalon | Ce qu'il valide | Contenu publiable |
|---|---|---|---|
| J0 | Bake carto | OSM + BD TOPO + arbres → assets, grilles, zones | Le centre de Toulouse en diorama low-poly |
| J1 | Son FDTD (Rust/WASM, navigateur) | WASM multithread, performance, rendu des champs | Un tir place du Capitole, l'onde ricoche |
| J2 | Odeur + vent canalisé | Advection-diffusion, champs de vent | Le vent d'autan porte l'odeur dans les rues |
| J3 | Simulation et utility AI | Hordes, combat et lignes de tir, infection, quartiers et bâtiments d'intérêt, loot, stress, fatigue, moral, XP et compétences, équilibrage headless | La horde franchit la barricade |
| J4 | Laya | Dataset distillé, fine-tune, calibration, broker, overlay, options débloquées par la progression des zombies | « Le cerveau visible » |
| J4b | Zombie alpha | Schéma enrichi, chef de horde, cri de rassemblement, ruche | La naissance d'un alpha |
| J4c | Intérieurs et sièges | Génération d'intérieurs, renforcement, assaut d'alpha, combat en intérieur, rendu en coupe | Le siège d'une planque |
| J5 | Survivants LLM + radio | Pipeline radio, `***`, conseil, déduction, confiance, exclusion, juge Laya | Un malentendu radio qui tourne mal |
| J6 | Clips en deux phases + replay public | Voxtral, viewer statique | Premier épisode complet et lien rejouable |
| J7 | Piratage des caméras | Objectif, CCTV, visibilité | Le siège de l'armoire technique |
| J8 | Mode commandant live | Temps réel, bodycams, voix, brouillard serveur | « Un humain commande des IA qui n'obéissent pas toujours » |

## Périmètre [Décidé]

- **MVP : J0 à J4c**, avec les alphas (J4b) et les intérieurs et sièges (J4c). Les premiers contenus publiables sortent dès J0 et J1.
- **Saison 2 : J5 à J8.**
- **Plus tard** : Laya dans le navigateur (ONNX Runtime Web, export de la tête à valider), horde pilotée par le chat, survivant qui « écoute » avec Voxtral Mini.

## Premiers pas recommandés

1. **PP** : préparation de l'environnement (versions figées, hooks, circuit Git).
2. **P0** : extrait OSM daté du centre, bake, vue de base, captures automatisées.
3. **P1, puis P2** avec les doublures et les benchmarks, avant d'attaquer P3 (Laya) et P4 (LLM).

Après la phase 0, l'ordre des jalons J0 à J8 sera revu selon le résultat de P5.
