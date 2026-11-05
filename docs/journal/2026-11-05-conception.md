# 2026-11-05 — Conception initiale et squelette du dépôt

- **Jalon** : avant P0
- **Objectif de la session** : définir le concept, l'architecture et les mécaniques du démonstrateur, puis préparer l'environnement de travail pour Claude Code.

## Fait
- Dossier de conception complet dans `docs/conception/` (README + 22 documents), avec revue des 21 décisions ouvertes.
- Prototype de rendu Three.js (`web/viewer/prototype/index.html`) : ville de démonstration générée, chargement d'un export OSM, entités en capsules sur le réseau de rues.
- Squelette du dépôt : `CLAUDE.md`, réglage `opusplan`, dix sous-agents (Haiku, Sonnet, Opus), `justfile` avec les commandes prévues, base documentaire `docs/`.
- Infrastructure : configuration GitHub en Terraform (`infra/terraform/`), workflows `ci.yml`, `gpu-eval.yml`, `deploy-viewer.yml`, vérification des liens de la documentation (`tools/check_links.py`). Validé localement : syntaxe HCL, `actionlint`, liens. `terraform validate` non lancé (Terraform indisponible dans l'environnement de conception).

## Décisions
Toutes prises par l'utilisateur ; voir le journal des décisions de `docs/conception/17-questions-ouvertes.md`. Principales :
- Laya = modèle de décision de Convai Innovations ; survivants pilotés par un LLM local (TabbyAPI).
- Centre de Toulouse, 5 quartiers, vue 3D de dessus ; cœur Rust compilé en WASM ; rendu Three.js.
- Phase 0 (prototype P0–P5) avant le MVP ; MVP = J0 à J4c (intérieurs et sièges compris).
- Antennes : une par quartier, à découvrir puis à tenir pendant toute une vague pour révéler les bâtiments d'intérêt ; sinon, tester les bâtiments un par un.
- Cinq types de bâtiments d'intérêt (vivres, soins, matériaux, munitions, repos) ; les autres sont inexplorables.
- Mécanique du « dernier recours » supprimée.
- Nom du projet : **Say Again**, avec une variante par ville (« Say Again : Toulouse ») — décision [0005](../decisions/0005-nom-say-again.md). Dépôt renommé `say-again`. Accroche : « Lead or Fade: Your Command » — décision [0006](../decisions/0006-accroche-lead-or-fade.md).
- CI/CD : décisions [0001](../decisions/0001-terraform-pour-github.md) à [0004](../decisions/0004-cloudflare-pages.md) (Terraform, état local, dépôt public, Cloudflare Pages).
- Boucle de retour outillée dès P0 ; décisions structurantes toujours posées à l'utilisateur ; journal de développement.

## Problèmes et points ouverts
- Données OSM de Toulouse non récupérables depuis l'environnement de conception : à extraire en P0 (pipeline de bake) ou via un export Overpass.
- Capacités réelles de la machine (CPU, débit du LLM en parallèle, latence de Laya) non mesurées : trois benchmarks à écrire.
- Questions ouvertes restantes : Q21, Q30 à Q33 (`17-questions-ouvertes.md`).

## Prochaines étapes
- Jalon PP (préparation de l'environnement) ajouté au plan avant P0 ; doublures des modèles et benchmarks intégrés à P2 ; traçabilité des versions à P0–P1.
- Planifier PP puis P0 avec `architecte`.
- Lancer `just tf-init`, `just tf-check` et `just tf-plan`, vérifier les points signalés dans `docs/technique/ci-cd.md`, puis `just tf-apply` (utilisateur) et premier push.
