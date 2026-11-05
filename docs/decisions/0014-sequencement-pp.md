# 0014 — Séquencement de la préparation de l'environnement (PP)

- **Date** : 2026-11-05
- **Statut** : décidée
- **Contexte** : PP modifie la configuration GitHub (Terraform) et le circuit de pull requests. Les modifications Terraform ne peuvent être appliquées que par l'utilisateur, et le premier push conditionne la suite du circuit.
- **Options présentées** : non consignées dans le compte rendu de la session (décision prise directement par l'utilisateur).
- **Recommandation des agents** : non consignée dans le compte rendu de la session.
- **Décision de l'utilisateur** :
  1. modifications Terraform de PP d'abord (étape E2) ;
  2. `tf-apply` et premier push par l'utilisateur ;
  3. le reste de PP, en une pull request par étape.
- **Conséquences** :
  - aucune étape de PP après l'étape E2 ne démarre avant l'application Terraform par l'utilisateur ;
  - le premier push déclenche l'état où `bypass_mode` peut être ajouté au ruleset (voir [0013](0013-identite-agents-fusion.md)) ;
  - chaque étape restante fait l'objet de sa propre pull request.
- **Documents mis à jour** : `docs/decisions/README.md`, `docs/conception/16-jalons.md`, `docs/conception/17-questions-ouvertes.md`.
