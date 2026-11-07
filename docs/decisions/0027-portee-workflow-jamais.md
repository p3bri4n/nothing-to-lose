# 0027 — Portée `workflow` : jamais pour les agents

- **Date** : 2026-11-07
- **Statut** : décidée
- **Contexte** : le jeton du compte machine est un jeton classique à portée `repo` ([0024](0024-jeton-compte-machine-classique.md)). Avec la portée `workflow`, un agent pourrait modifier un fichier de `.github/workflows/` pour viser le runner GPU, puisque la garde de `gpu-eval.yml` (`github.repository_owner == github.actor`) est dans un fichier que l'agent peut modifier.
- **Options présentées** :
  1. Jamais : l'agent prépare le changement de workflow, et l'utilisateur le pousse. Avantage : aucune modification de la CI ni du runner GPU par un agent. Inconvénient : l'utilisateur pousse lui-même les changements de `.github/workflows/`.
  2. L'autoriser pour l'instant, à retirer avant P2. Avantage : pas de friction pendant PP. Inconvénient : un agent peut modifier un workflow pour viser le runner GPU ; le retrait peut être oublié.
- **Recommandation des agents** : option 1 (jamais), recommandée par la session principale.
- **Décision de l'utilisateur** : **jamais**.
- **Conséquences** :
  - l'agent prépare le changement de workflow, et l'utilisateur le pousse ;
  - le jeton des agents n'a que la portée `repo` ; la portée `workflow` n'est jamais accordée. Précise [0024](0024-jeton-compte-machine-classique.md) ;
  - la recherche du 2026-11-07 ([§5, question 2](../recherches/2026-11-07-garde-fous-git-gh.md)) signale une exception de GitHub : un fichier de workflow identique (même chemin, même contenu) déjà présent sur une autre branche du dépôt peut être poussé sans la portée `workflow`. Cette exception n'a pas été testée ; elle ne change pas la décision ;
  - la règle est à reprendre dans la procédure du jeton (`docs/technique/compte-machine-agents.md`) et dans le plan PP (U5, R6).
- **Documents mis à jour** : `docs/decisions/README.md` (index), `docs/decisions/0027-portee-workflow-jamais.md` (création), `docs/decisions/0024-jeton-compte-machine-classique.md` (note de précision), `docs/conception/README.md`, `docs/conception/17-questions-ouvertes.md`, `docs/plans/PP.md` (U5, R6).
