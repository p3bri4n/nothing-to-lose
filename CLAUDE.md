# Nothing To Lose — instructions pour Claude Code

**Nothing To Lose** — démonstrateur d'IA : invasion zombie dans le centre de Toulouse (le jeu est centré sur Toulouse, mais par portabilité rien de spécifique à Toulouse ne doit être codé en dur hors des données de la carte). Les zombies sont pilotés par **Laya** (modèle de décision de Convai Innovations, « System 1 »), les survivants par un **LLM local** (« System 2 »). Objectif : un démonstrateur novateur pour les réseaux sociaux.

**Toute la conception est dans [`docs/conception/`](docs/conception/README.md).** La lire avant toute décision d'architecture. Ne pas contredire une décision marquée **[Décidé]** sans l'accord explicite de l'utilisateur. Les décisions structurantes sont toujours posées à l'utilisateur (voir plus bas).

## Phase actuelle

**Phase 0 — prototype (PP, puis P0 à P5)**, en commençant par **PP, la préparation de l'environnement** : voir [`docs/conception/16-jalons.md`](docs/conception/16-jalons.md). Mécaniques simplifiées, rendu minimal. Ne pas implémenter ce que la phase 0 repousse (son en onde, odeur, radio dégradée, stress, social, intérieurs, alphas…) sans demande explicite.

## Répartition des modèles

La session principale utilise `opusplan` (voir `.claude/settings.json`) : **Opus en mode plan** (décisions, planification), **Sonnet en exécution**. Le travail est délégué aux sous-agents de `.claude/agents/` :

| Sous-agent | Modèle | Quand l'utiliser |
|---|---|---|
| `explorateur` | Haiku | Trouver des fichiers, du code, des usages ; lecture seule |
| `synthetiseur` | Haiku | Résumer des sorties longues : `runs/`, `report.md`, `violations.txt`, logs, `feedback/` |
| `relecteur` | Haiku | Première relecture d'un diff : conventions, oublis évidents, tests manquants |
| `chercheur-web` | Haiku | Recherches sur le web : documentation, versions, API, licences, messages d'erreur, jeux de données ; faits sourcés et datés, notes dans `docs/recherches/` |
| `documentaliste` | Haiku | Base documentaire : journal de développement, documentation technique, fiches de décision, index de `docs/` |
| `executant` | Haiku | Tâches simples et mécaniques : renommages, formatage, code passe-partout, déplacements, documentation, configuration, petits scripts, commandes avec compte rendu |
| `developpeur` | Sonnet | Implémenter une étape d'un plan validé |
| `testeur` | Sonnet | Écrire les tests, transformer un bug en test de non-régression, lancer `just eval` |
| `architecte` | Opus | Décision d'architecture, plan d'un jalon, arbitrage entre options, revue d'un changement risqué |
| `debogueur` | Opus | Bug difficile : non reproduit, non-déterminisme, cause inconnue |

**Règles d'escalade** :
- Un même test échoue deux fois de suite après correction → `debogueur`.
- Toute modification du déterminisme, du contrat de décision, du journal ou du pare-feu d'information → revue par `architecte`.
- Haiku ne touche jamais à la logique de simulation, au déterminisme, au contrat de décision, au journal, au broker, à la construction des prompts ni au pare-feu d'information. Seul `executant` modifie des fichiers, pour des tâches mécaniques, et ses changements passent par `just check` puis par `relecteur`. Les conclusions des autres sous-agents Haiku (lecture seule) sont vérifiées par la session principale.
- Une tâche confiée à `executant` qui se révèle moins simple que prévu repart vers `developpeur`.
- Avant d'utiliser une bibliothèque, une API ou une version que tu n'as pas vérifiée récemment, fais-la vérifier par `chercheur-web` plutôt que de te fier à ta mémoire. Une information de confiance faible se revérifie avant toute décision.
- Une relecture du `relecteur` qui signale un doute sérieux → `architecte`.

**Ne jamais définir `CLAUDE_CODE_SUBAGENT_MODEL`** : cette variable écrase le champ `model` de tous les sous-agents.

## Décisions structurantes : toujours posées à l'utilisateur

**Aucun agent ne prend seul une décision structurante.** Est structurant tout ce qui :
- change une règle de jeu ou une mécanique, ou en ajoute une ;
- remet en cause un élément marqué **[Décidé]** dans `docs/conception/` ;
- tranche une question de `docs/conception/17-questions-ouvertes.md` ;
- change l'architecture : découpage en modules ou services, contrat de décision, format du journal, règles de déterminisme, pare-feu d'information ;
- ajoute une dépendance importante (moteur, framework, modèle d'IA, service externe) ou change une licence ;
- change le périmètre d'un jalon ou l'ordre des jalons ;
- a un effet visible sur ce qui sera publié (style visuel, contenu sensible, données réelles).

Procédure :
1. Préparer la question (au besoin avec `architecte`) : contexte court, 2 à 4 options avec leurs compromis, recommandation.
2. **Poser la question à l'utilisateur** (outil de question à choix multiple) et attendre sa réponse. Ne pas commencer l'implémentation avant.
3. Faire enregistrer la réponse par `documentaliste` : fiche dans `docs/decisions/`, report dans `docs/conception/`.

Les choix techniques mineurs (nom d'une fonction, structure interne d'un module, choix d'une petite bibliothèque utilitaire) sont pris en autonomie, puis notés dans le journal de la session avec leur raison. **En cas de doute sur le caractère structurant : poser la question.**

## Base documentaire

Toute la documentation est sous [`docs/`](docs/README.md) et doit refléter l'état réel du projet :
- `docs/conception/` : ce qui est voulu (mis à jour après chaque décision de l'utilisateur) ;
- `docs/decisions/` : registre des décisions structurantes ;
- `docs/journal/` : journal de développement ;
- `docs/technique/` : le code tel qu'il existe (formats, modules, commandes) ;
- `docs/plans/` : plans de jalons et de fonctionnalités ;
- `docs/recherches/` : notes de recherche sourcées.

Un changement de code qui modifie un format, une commande ou le comportement d'un module s'accompagne de la mise à jour de `docs/technique/` **dans la même session**. Un écart entre le code et la documentation est un défaut.

## Journal de développement

- **En début de session** : lire les deux ou trois dernières entrées de `docs/journal/`, puis `feedback/`.
- **En fin de session** (ou avant de s'arrêter sur une tâche longue) : faire écrire l'entrée du jour par `documentaliste`, à partir d'un compte rendu factuel : ce qui a été fait, résultats de `just check` / `just eval`, décisions posées à l'utilisateur, choix mineurs pris en autonomie, problèmes ouverts, prochaines étapes.

## Commandes

Définies dans `justfile`. Celles marquées (à venir) n'existent pas encore et sont à créer au jalon indiqué.

| Commande | Rôle | Jalon |
|---|---|---|
| `just bake` | Extraire et préparer la carte (OSM) | P0 (à venir) |
| `just viewer` | Lancer le viewer local | P0 (à venir) |
| `just shots` | Captures d'écran automatisées (Playwright) dans `shots/` | P0 (à venir) |
| `just sim --seed N --minutes M --out runs/N/` | Partie headless : `journal.jsonl`, `summary.json`, `violations.txt` | P1 (à venir) |
| `just check` | Contrôle complet : pour l'instant `just lint` seul ; P1 y ajoute tests, non-régression, invariants, mini-partie | PP / P1 |
| `just lint` | Versions des outils, tests des outils, formatage, liens, secrets, workflows, Terraform | disponible |
| `just fmt` / `just fmt-check` | Formater / vérifier le formatage (Markdown exclu) | disponible |
| `just versions` / `just tools-test` / `just docs-links` / `just actionlint` / `just secrets-scan` | Contrôles individuels (appelés par `just lint`) | disponible |
| `just setup` / `just hooks-install` | Installer les outils (mise), activer les hooks Git : action locale, une fois par clone | disponible |
| `just verify-pp <format\|versions\|secrets>` | Vérifications automatiques des critères du jalon PP | disponible |
| `just inspect --seed N --tick T --agent ID` | État, perception, décisions d'un agent | P2 (à venir) |
| `just eval --seeds 50` | Lot de parties, `report.md` comparé à `reports/baseline.json` | P2 (à venir) |
| `just tf-init` / `just tf-check` / `just tf-plan` | Infrastructure GitHub (Terraform) : initialiser, valider, prévisualiser | disponible |
| `just tf-apply` | Appliquer les changements d'infrastructure | **réservé à l'utilisateur** |

## Infrastructure et CI/CD

Détails : [`docs/technique/ci-cd.md`](docs/technique/ci-cd.md).

- **Terraform configure GitHub** (`infra/terraform/`) : dépôt, ruleset de la branche principale, permissions des actions, variables, environnement `production` et ses secrets, labels. Toute modification de la configuration GitHub passe par Terraform, jamais par l'interface web.
- **Les agents ne lancent jamais `terraform apply`, `destroy`, `import` ni `state`** (bloqué dans `.claude/settings.json`). Ils peuvent modifier les fichiers `.tf`, lancer `just tf-check` et `just tf-plan`, puis présenter le plan à l'utilisateur. Un changement d'infrastructure est une décision structurante.
- **Aucun secret dans le dépôt** : le jeton GitHub est dans `GITHUB_TOKEN`, les autres valeurs dans `terraform.tfvars` (ignoré par Git), l'état Terraform hors du dépôt.
- **Dépôt public** : le workflow GPU (`gpu-eval.yml`) ne doit jamais être déclenché par `pull_request`. Toute modification de ses déclencheurs passe par `architecte` et l'utilisateur.
- **Le job `ci-cpu` est le check obligatoire** de la branche principale. Le renommer impose de mettre à jour `required_ci_check` dans Terraform dans le même changement.
- Chaque nouvelle partie du projet (premier `Cargo.toml`, `pyproject.toml`, `package.json`) active automatiquement les étapes correspondantes de la CI : vérifier qu'elles passent dans la même pull request.

## Routine de travail

0. Début de session : dernières entrées de `docs/journal/`, puis `feedback/`.
1. Pour une tâche non triviale : plan d'abord (mode plan, ou `architecte`). Si le plan contient une décision structurante, la poser à l'utilisateur avant d'implémenter.
2. Implémenter (`developpeur`), par petites étapes.
3. `just check`. Si la simulation ou les IA sont touchées : `just eval` et comparaison avec la référence (`synthetiseur` pour résumer le rapport).
4. Relecture (`relecteur`) ; escalade si nécessaire.
5. Ne valider que si rien ne régresse, ou si la régression est voulue et expliquée (mise à jour de `reports/baseline.json` dans le même commit).
6. Chaque bug corrigé ajoute un test dans `tests/regressions/` (seed, tick, agent, condition attendue).
7. `feedback/` contient les retours de l'utilisateur sur des moments précis (seed, tick, capture, commentaire) : les traiter ou les reporter explicitement dans le journal.
8. Mettre à jour `docs/technique/` si le code a changé de forme ou de comportement.
9. Fin de session : entrée de journal par `documentaliste`.

Détails : [`docs/conception/22-boucle-de-retour.md`](docs/conception/22-boucle-de-retour.md).

## Circuit Git

Détails : [`docs/technique/circuit-git.md`](docs/technique/circuit-git.md).

- Une branche et une pull request par changement : `git switch -c <sujet>` depuis `main` à jour, commits en français, `git push -u origin HEAD`, `gh pr create` avec la liste de contrôle remplie, `gh pr checks --watch --required`, puis prévenir l'utilisateur.
- **L'utilisateur seul fusionne.** Les agents n'utilisent jamais `gh pr merge`, ne poussent pas vers `main`, ne forcent jamais un push et ne contournent jamais les hooks (`--no-verify`, `-n`, désactivation de `core.hooksPath`). Un garde-fou (`tools/hooks/guard_bash.py`) bloque ces commandes ; en cas de blocage, corriger la cause plutôt que contourner.

## Règles techniques non négociables

- **Déterminisme** ([03](docs/conception/03-architecture-technique.md)) : tick fixe à 20 Hz, RNG seedé, pas de `relaxed-simd`, fonctions transcendantes via la crate `libm`, ordre fixe des réductions parallèles, aucun calcul GPU qui influence le gameplay. Les décisions IA sont journalisées et rejouées depuis le journal.
- **Pare-feu d'information** ([05](docs/conception/05-ia-survivants-llm.md)) : les prompts des LLM ne sont construits qu'à partir du `BeliefStore` du personnage, jamais à partir de la vérité de la simulation. Un test le vérifie.
- **Laya** ([04](docs/conception/04-ia-laya.md)) : questions `choice` de 3 à 8 options, pas de `noul` sur le checkpoint anglais, décider sur `confidence` (pas `act_probability`), perception textuelle quantifiée et < 512 tokens. `laya-serve` n'est jamais exposé directement.
- **LLM des survivants** : TabbyAPI, sortie JSON contrainte, mode « thinking » désactivé.

## Organisation du dépôt

```
crates/core      Rust : simulation (ECS, déplacements, combat, infection…)
crates/fields    Rust : champs physiques (plus tard : son, odeur, radio)
crates/wasm      Bindings WebAssembly (Node + navigateur)
services/brain   Python : broker, Laya, client TabbyAPI
services/radio   Python : TTS, DSP, ASR (plus tard)
services/recorder Rendu offline des clips (plus tard)
web/viewer       Viewer Three.js (prototype de rendu dans web/viewer/prototype/)
bake             Python : pipeline carto
tests/regressions Tests de non-régression (un fichier par bug)
runs/ shots/ feedback/ reports/  Sorties des outils de retour
docs/            Base documentaire (conception, décisions, journal, technique, plans, recherches)
infra/terraform  Configuration GitHub (Terraform)
.github/workflows CI (ci.yml), évaluation GPU (gpu-eval.yml), déploiement (deploy-viewer.yml)
tools/           Petits utilitaires (vérification des liens de la documentation…)
```

## Langue

Code, identifiants et commentaires en anglais. Documentation, messages de commit et échanges avec l'utilisateur en français.
