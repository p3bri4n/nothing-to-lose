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
- **Précisions ultérieures** : [0021](0021-fusion-compte-machine-agents.md) (compte machine des agents, une approbation requise) et [0024](0024-jeton-compte-machine-classique.md) (le jeton des agents est un jeton classique à portée `repo` du compte machine, et non un jeton à granularité fine : GitHub ne permet pas ce dernier à un collaborateur d'un dépôt de compte personnel). La règle « seul l'utilisateur fusionne » est inchangée.
- **Conséquences** :
  - le jeton est fourni par `GITHUB_TOKEN` (pas de secret dans le dépôt, voir [0001](0001-terraform-pour-github.md)). Précision : les agents utilisent `GH_TOKEN` du compte machine ([0024](0024-jeton-compte-machine-classique.md)) ; le `GITHUB_TOKEN` d'administration (Terraform) ne doit jamais être dans leur environnement ([0026](0026-isolement-identifiants-claudeus.md)), et le garde Bash refuse de le manipuler ([0028](0028-garde-bash-identifiants-github.md)) ;
  - la modification de `ruleset.tf` est une modification de la configuration GitHub : elle passe par Terraform et son application relève de l'utilisateur ;
  - la fusion reste une action de l'utilisateur, les agents s'arrêtent à la pull request ouverte.
- **Documents mis à jour** : `docs/decisions/README.md`, `docs/conception/16-jalons.md`, `docs/conception/17-questions-ouvertes.md`.
