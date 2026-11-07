# 0025 — Barrière serveur : CODEOWNERS et revue du propriétaire

- **Date** : 2026-11-07
- **Statut** : décidée
- **Contexte** : une pull request approuvée est fusionnable par tout compte *Write*. Le compte machine des agents ([0021](0021-fusion-compte-machine-agents.md), rôle *Write*) peut donc approuver une pull request du propriétaire ou de Dependabot, puis la fusionner. Point relevé par la revue d'`architecte` d'E10b. Le ruleset de `main` n'exige pour l'instant qu'une approbation, quelle que soit la personne qui l'a donnée.
- **Options présentées** :
  1. CODEOWNERS et `require_code_owner_review` : seule l'approbation d'un propriétaire du code (`.github/CODEOWNERS`) compte. Les approbations du compte machine ne comptent plus. Avantage : ferme l'approbation croisée par un compte *Write* sans changer de compte. Inconvénient : dépend d'un fichier CODEOWNERS valide ; les pull requests du propriétaire ne se fusionnent que par contournement administrateur.
  2. Option 1, plus une règle `update` (*Restrict updates*) réservée à l'administrateur. Avantage : restreint aussi les mises à jour de la branche protégée. Inconvénient : apport limité tant que la règle `pull_request` bloque déjà le push direct (inférence, non testée) ; règle supplémentaire à maintenir et à tester.
  3. Rien de plus : une approbation d'un compte *Write* reste suffisante ; la fusion ne resterait sûre que parce que l'utilisateur fusionne toujours par contournement, sans approbation. Inconvénient : la barrière repose sur la seule discipline du propriétaire.
- **Recommandation des agents** : option 1, recommandée par l'`architecte` et par la session principale.
- **Décision de l'utilisateur** : **option 1** (CODEOWNERS et `require_code_owner_review`). La règle `update` reste une option future.
- **Conséquences** :
  - un fichier `.github/CODEOWNERS` désigne le propriétaire du dépôt comme responsable de tout le dépôt ; l'attribut `require_code_owner_review = true` figure dans `infra/terraform/ruleset.tf` (écrit dans le code à la date de la décision, non appliqué) ;
  - les approbations du compte machine ne comptent plus : une pull request d'agent n'est mergeable qu'après approbation de l'utilisateur, ou par son contournement ;
  - les pull requests du propriétaire ne se fusionnent que par contournement administrateur (un auteur ne peut pas approuver sa propre pull request). Ce comportement est **à vérifier sur une pull request triviale** ; voie de secours si le contournement ne suffit pas : repasser temporairement le ruleset par Terraform ;
  - **conséquence sur la règle « seul l'utilisateur fusionne »** ([0013](0013-identite-agents-fusion.md)) : côté serveur, une fois la pull request approuvée, le compte machine peut la fusionner (rôle *Write*). Le contrôle de la fusion par les agents reste donc local (`guard_bash.py`). L'approbation de l'utilisateur vaut autorisation de fusion : il n'approuve une pull request d'agent qu'au moment de la fusionner, ou il la fusionne lui-même par contournement (cf. [0024](0024-jeton-compte-machine-classique.md)) ;
  - **à vérifier avant `just tf-plan`** : la liste des attributs de la règle `pull_request` du provider `github_repository_ruleset` relevée par la [recherche du 2026-11-07](../recherches/2026-11-07-garde-fous-git-gh.md) (§4) ne contient pas `require_code_owner_review`. Le schéma installé (`terraform providers schema -json`) doit confirmer le nom de l'attribut ;
  - la règle `update` n'est pas mise en œuvre ; elle reste une option future ;
  - E10b : le fichier CODEOWNERS doit être sur `main` avant `tf-apply` (voir [`PP.md`](../plans/PP.md), étape E10b).
- **Documents mis à jour** : `docs/decisions/README.md` (index), `docs/decisions/0025-barriere-serveur-codeowners.md` (création), `docs/conception/README.md`, `docs/conception/17-questions-ouvertes.md`, `docs/plans/PP.md` (R6, E10b, interface de `verify_pp.sh`, périmètre hors PP).
