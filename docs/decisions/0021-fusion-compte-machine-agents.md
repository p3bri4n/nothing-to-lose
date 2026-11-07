# 0021 — Fusion des pull requests : compte machine pour les agents, une approbation requise

- **Date** : 2026-11-07
- **Statut** : décidée
- **Contexte** : le ruleset de `main` (`infra/terraform/ruleset.tf`) exige 0 approbation (`required_approving_review_count = 0`). Le jeton U5 (*Pull requests* en écriture) peut appeler l'API de fusion. Côté serveur, le ruleset bloque déjà le push direct vers `main`, le push forcé et la suppression de `main` ; rien côté serveur n'empêche un agent de fusionner une pull request. Seul le hook local `guard_bash.py` refuse `gh pr merge`. La revue d'`architecte` d'E10 a relevé ce point.
- **Options présentées** :
  1. Accepter le risque et le documenter. Aucun changement de configuration ; la fusion reste protégée par le hook local et par la discipline des agents. Inconvénient : un agent qui contourne le hook peut fusionner sa propre pull request sans relecture.
  2. Compte machine pour les agents (rôle *Write*, pas administrateur) et `required_approving_review_count = 1` ; l'utilisateur fusionne comme administrateur, grâce à `bypass_mode = "pull_request"`. Avantage : un auteur ne peut pas approuver sa propre pull request (doc GitHub, voir [la note du 2026-11-07](../recherches/2026-11-07-garde-fous-git-gh.md)), donc une pull request d'agent exige un autre acteur ; le jeton des agents n'est plus celui du propriétaire. Inconvénient : création d'un compte, d'une invitation et d'un jeton par l'utilisateur, puis `tf-apply` ; protection réelle seulement après E10b.
- **Recommandation des agents** : option 1 (accepter et documenter), recommandation de la session principale.
- **Décision de l'utilisateur** : **option 2**.
  - le compte machine des agents est invité sur le dépôt avec le rôle *Write*, jamais administrateur ;
  - le ruleset exige 1 approbation (`required_approving_review_count = 1`) ;
  - l'utilisateur fusionne comme administrateur, par le contournement `bypass_mode = "pull_request"` ;
  - le jeton U5 est remplacé par un jeton à granularité fine **du compte machine** (*Contents*, *Pull requests* et *Issues* en écriture), jamais rattaché au compte propriétaire.
- **Conséquences** :
  - étape **E10b**, dans une PR séparée d'E10 : Terraform (ruleset à 1 approbation ; variable `agents_account` ; ajout du compte machine comme collaborateur avec le rôle *Write*) ;
  - actions de l'utilisateur : créer le compte machine, accepter l'invitation, créer le jeton, lancer `just tf-apply` (réservé à l'utilisateur) ;
  - **jusqu'à E10b, la fusion n'est protégée que par le hook `guard_bash.py` et par la discipline des agents** ; les agents s'arrêtent à la pull request ouverte ;
  - la règle « seul l'utilisateur fusionne » de [0013](0013-identite-agents-fusion.md) est inchangée ; cette décision précise seulement le compte et le jeton des agents ;
  - les mentions de U5 dans `docs/plans/PP.md` et dans la documentation du circuit valent jusqu'à E10b.
- **Documents mis à jour** : `docs/decisions/README.md` (index), `docs/decisions/0021-fusion-compte-machine-agents.md` (création), `docs/conception/README.md`, `docs/conception/03-architecture-technique.md`, `docs/conception/17-questions-ouvertes.md`, `docs/plans/PP.md` (§E10).
