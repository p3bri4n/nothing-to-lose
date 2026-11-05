# 0010 — Liste de contrôle des pull requests : vérifiée et bloquante

- **Date** : 2026-11-05
- **Statut** : décidée
- **Contexte** : le critère de PP impose qu'une pull request de test passe la CI avec la liste de contrôle remplie. Une liste non vérifiée reste une convention que l'on oublie.
- **Options présentées** : non consignées dans le compte rendu de la session (décision prise directement par l'utilisateur).
- **Recommandation des agents** : non consignée dans le compte rendu de la session.
- **Décision de l'utilisateur** :
  - la liste de contrôle est vérifiée automatiquement et elle est bloquante, dans le job `ci-cpu` (déclencheur `edited`) ;
  - « sans objet » est autorisé pour un point de la liste ;
  - les pull requests de Dependabot sont exemptées.
- **Conséquences** :
  - le job `ci-cpu` est le check obligatoire de la branche principale (voir [CI/CD](../technique/ci-cd.md)) : toute modification de sa logique passe par le même circuit ;
  - le déclencheur `edited` fait repasser la vérification quand le corps de la pull request est modifié.
- **Documents mis à jour** : `docs/decisions/README.md`, `docs/conception/16-jalons.md`, `docs/conception/17-questions-ouvertes.md`.
