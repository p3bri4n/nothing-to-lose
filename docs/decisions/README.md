# Registre des décisions structurantes

Une fiche par décision, nommée `NNNN-titre-court.md` (numérotation continue). Une décision structurante est **toujours prise par l'utilisateur** ; les agents préparent les options et enregistrent la réponse.

Les décisions antérieures à la création du dépôt sont dans le journal des décisions de [`../conception/17-questions-ouvertes.md`](../conception/17-questions-ouvertes.md).

## Index

| # | Date | Décision | Statut |
|---|---|---|---|
| [0001](0001-terraform-pour-github.md) | 2026-11-05 | Terraform pour configurer GitHub et la CI/CD | décidée |
| [0002](0002-etat-terraform-local.md) | 2026-11-05 | État Terraform local, hors du dépôt | décidée |
| [0003](0003-depot-public.md) | 2026-11-05 | Dépôt public dès le départ | décidée |
| [0004](0004-cloudflare-pages.md) | 2026-11-05 | Déploiement du viewer sur Cloudflare Pages | décidée |
| [0005](0005-nom-say-again.md) | 2026-11-05 | Nom du projet : « Say Again », une variante par ville | décidée |
| [0006](0006-accroche-lead-or-fade.md) | 2026-11-05 | Accroche officielle : « Lead or Fade: Your Command » | décidée |

Statuts possibles : `en attente` (question posée, pas encore de réponse), `décidée`, `remplacée par NNNN`.

## Modèle de fiche

```markdown
# NNNN — Titre

- **Date** : AAAA-MM-JJ
- **Statut** : décidée
- **Contexte** : pourquoi la question se pose (2 à 4 phrases).
- **Options présentées** :
  1. Option A — avantages, inconvénients
  2. Option B — avantages, inconvénients
- **Recommandation des agents** : option et raison.
- **Décision de l'utilisateur** : option retenue, avec ses mots s'il a précisé quelque chose.
- **Conséquences** : ce qui change (code, documentation, jalons).
- **Documents mis à jour** : liste des fichiers.
```
