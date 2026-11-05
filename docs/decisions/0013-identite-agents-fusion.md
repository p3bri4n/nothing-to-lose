# 0013 — Identité GitHub des agents et fusion des pull requests

- **Date** : 2026-11-05
- **Statut** : décidée
- **Contexte** : les agents ouvrent des pull requests via `gh`. Il faut limiter les droits de leur jeton GitHub et définir qui fusionne, sans que les agents puissent contourner la revue.
- **Options présentées** : non consignées dans le compte rendu de la session (décision prise directement par l'utilisateur).
- **Recommandation des agents** : non consignée dans le compte rendu de la session.
- **Décision de l'utilisateur** :
  - le jeton des agents est à granularité fine et limité au dépôt nothing-to-lose (nom renommé le 2026-11-05, voir [0016](0016-nom-nothing-to-lose.md)) ;
  - après le premier push, `bypass_mode = "pull_request"` est ajouté au ruleset dans `ruleset.tf` ;
  - seul l'utilisateur fusionne : `gh pr merge` est interdit aux agents.
- **Conséquences** :
  - le jeton est fourni par `GITHUB_TOKEN` (pas de secret dans le dépôt, voir [0001](0001-terraform-pour-github.md)) ;
  - la modification de `ruleset.tf` est une modification de la configuration GitHub : elle passe par Terraform et son application relève de l'utilisateur ;
  - la fusion reste une action de l'utilisateur, les agents s'arrêtent à la pull request ouverte.
- **Documents mis à jour** : `docs/decisions/README.md`, `docs/conception/16-jalons.md`, `docs/conception/17-questions-ouvertes.md`.
