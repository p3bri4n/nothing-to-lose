# 0002 — État Terraform local, hors du dépôt

- **Date** : 2026-11-05
- **Statut** : décidée
- **Contexte** : l'état Terraform mémorise ce qui a été créé sur GitHub et peut contenir des valeurs sensibles ; il ne doit pas être versionné.
- **Options présentées** :
  1. HCP Terraform — état chiffré et verrouillé, rien à héberger (recommandée)
  2. Local, hors dépôt — le plus simple, sauvegarde à la charge de l'utilisateur
  3. Stockage compatible S3 — plus de contrôle, plus de configuration
- **Recommandation des agents** : HCP Terraform.
- **Décision de l'utilisateur** : local, hors dépôt.
- **Conséquences** : backend `local` avec chemin fourni à l'initialisation (`~/.local/share/terraform/nothing-to-lose/` par défaut, surchargeable par `TF_STATE_PATH` ; nom du dossier renommé le 2026-11-05, voir [0016](0016-nom-nothing-to-lose.md)) ; fichiers d'état ignorés par Git et illisibles par les agents ; l'utilisateur sauvegarde l'état dans un endroit chiffré.
- **Documents mis à jour** : `infra/terraform/versions.tf`, `justfile`, `.gitignore`, `.claude/settings.json`, `docs/technique/ci-cd.md`.
