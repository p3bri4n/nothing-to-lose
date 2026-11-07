# 0023 — Périmètre du garde-fou Bash : règles ajoutées au-delà du plan conservées

- **Date** : 2026-11-07
- **Statut** : décidée
- **Contexte** : le plan PP (§E10) prévoyait des règles précises pour `guard_bash.py`. Pendant l'étape E10, le développeur a ajouté des règles qui n'y figuraient pas : `--no-verify` pour `git push`, `git merge` et `git rebase` ; `--prune` et `--all` sur `git push` ; `gh secret`, `gh variable` et `gh alias` ; les mutations GraphQL de la liste `GRAPHQL_FORBIDDEN` ; le refus de modifier `core.hooksPath`. Le garde-fou sur `Edit` et `Write` pour `.git/`, `.githooks/` et `.claude/settings.json` n'est pas dans E10.
- **Options présentées** : le compte rendu de la session ne détaille pas les options ; la question posée portait sur la conservation des règles ajoutées.
  1. (a) Garder les règles ajoutées au-delà du plan.
  2. Autres options : non consignées dans le compte rendu de la session.
- **Recommandation des agents** : non consignée dans le compte rendu de la session.
- **Décision de l'utilisateur** : **option (a)**, garder les règles ajoutées au-delà du plan. Le garde-fou sur `Edit` et `Write` pour `.git/`, `.githooks/` et `.claude/settings.json` est **reporté** à la refonte des agents (guard-paths), et n'entre pas dans E10.
- **Conséquences** :
  - les règles listées ci-dessus restent, avec leurs tests, et sont décrites dans [`docs/technique/garde-fous-bash.md`](../technique/garde-fous-bash.md) ;
  - le garde-fou sur `Edit` et `Write` est un élément de la refonte des agents, à suivre hors d'E10 ;
  - `git reset --hard origin…` et `git clean -fdx` restent hors périmètre. C'est une décision explicite de l'utilisateur du 2026-11-07, et non un choix de session : le garde-fou ne les refuse pas. Tout refus de ces commandes serait une décision nouvelle, à poser à l'utilisateur.
- **Documents mis à jour** : `docs/decisions/README.md` (index), `docs/decisions/0023-perimetre-garde-bash.md` (création), `docs/conception/17-questions-ouvertes.md`.
