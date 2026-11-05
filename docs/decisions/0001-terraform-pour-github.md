# 0001 — Terraform pour configurer GitHub et la CI/CD

- **Date** : 2026-11-05
- **Statut** : décidée
- **Contexte** : la configuration de GitHub (dépôt, protections, secrets, variables des workflows) doit être reproductible, versionnée et modifiable par les agents sous contrôle de l'utilisateur.
- **Options présentées** : décision prise directement par l'utilisateur.
- **Décision de l'utilisateur** : « on va se baser sur Terraform pour configurer GitHub Actions / GitHub pour la CI/CD ».
- **Conséquences** : `infra/terraform/` (provider `integrations/github` ~> 6.0) ; toute modification de la configuration GitHub passe par Terraform ; les agents ne lancent jamais `apply`.
- **Documents mis à jour** : `CLAUDE.md`, `docs/technique/ci-cd.md`, `docs/conception/03-architecture-technique.md`.
