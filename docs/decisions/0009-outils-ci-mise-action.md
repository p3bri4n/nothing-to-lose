# 0009 — Outils en CI : `jdx/mise-action` épinglée par SHA

- **Date** : 2026-11-05
- **Statut** : décidée
- **Contexte** : la CI doit utiliser les mêmes versions d'outils que le poste local. Ces versions sont déclarées dans `mise.toml` ; il faut un moyen de les installer dans les workflows.
- **Options présentées** :
  1. `jdx/mise-action` épinglée par SHA, qui lit `mise.toml` — retenue.
  2. mise installé à la main dans chaque workflow — écarté.
  3. Actions `setup-*` par langage — écarté.
  4. CI dans l'image du sandbox — écarté.
- **Recommandation des agents** : non consignée dans le compte rendu de la session.
- **Décision de l'utilisateur** : `jdx/mise-action` épinglée par SHA, qui lit `mise.toml`. Ajout de `jdx/mise-action@*` dans `infra/terraform/actions.tf`.
- **Conséquences** :
  - une seule source de versions (`mise.toml`) pour le poste local et la CI ;
  - l'action est épinglée par SHA dans les workflows ; l'autorisation de l'action est gérée par Terraform (`infra/terraform/actions.tf`), donc soumise à `tf-apply` par l'utilisateur ;
  - la CI n'utilise pas l'image du sandbox (voir [0015](0015-sandbox-reporte-apres-pp.md)).
- **Documents mis à jour** : `docs/decisions/README.md`, `docs/conception/16-jalons.md`, `docs/conception/17-questions-ouvertes.md`.
