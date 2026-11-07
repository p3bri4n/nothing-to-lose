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
| [0005](0005-nom-say-again.md) | 2026-11-05 | Nom du projet : « Say Again », une variante par ville | remplacée par 0016 |
| [0006](0006-accroche-lead-or-fade.md) | 2026-11-05 | Accroche officielle : « Lead or Fade: Your Command » | remplacée par 0017 |
| [0007](0007-hooks-git-scripts-maison.md) | 2026-11-05 | Hooks Git : scripts maison dans `.githooks/` + `core.hooksPath` | décidée |
| [0008](0008-gitleaks-binaire-fige.md) | 2026-11-05 | Gitleaks : binaire figé via mise, règles par défaut étendues | décidée |
| [0009](0009-outils-ci-mise-action.md) | 2026-11-05 | Outils en CI : `jdx/mise-action` épinglée par SHA | décidée |
| [0010](0010-liste-controle-pr.md) | 2026-11-05 | Liste de contrôle des pull requests vérifiée et bloquante | décidée |
| [0011](0011-politique-versions-exactes.md) | 2026-11-05 | Politique de versions : versions exactes partout | décidée |
| [0012](0012-markdown-hors-formatage.md) | 2026-11-05 | Markdown exclu du formatage automatique | décidée |
| [0013](0013-identite-agents-fusion.md) | 2026-11-05 | Identité GitHub des agents et fusion réservée à l'utilisateur | décidée |
| [0014](0014-sequencement-pp.md) | 2026-11-05 | Séquencement de PP : Terraform, puis premier push, puis une PR par étape | décidée |
| [0015](0015-sandbox-reporte-apres-pp.md) | 2026-11-05 | Sandbox reporté après PP (Claudeus de l'utilisateur) | décidée |
| [0016](0016-nom-nothing-to-lose.md) | 2026-11-05 | Nom du projet : « Nothing To Lose », Toulouse seulement (remplace 0005) | décidée |
| [0017](0017-accroche-le-speech.md) | 2026-11-05 | Accroche : le speech officiel, signature « commandez avec brio ! » (remplace 0006) | décidée |
| [0018](0018-image-principale-key-art.md) | 2026-11-05 | Image principale du jeu : `docs/assets/key-art.png` (style réaliste non décidé comme direction artistique) | décidée |
| [0019](0019-accroche-command-humanity-last-hope.md) | 2026-11-05 | Accroche courte officielle : « Command humanity's last hope » (sous-titre du key art ; complète 0017) | décidée |
| [0020](0020-securite-hook-formatage.md) | 2026-11-07 | Sécurité du hook de formatage : refus si `mise.toml`, `mise.local.toml`, `.prettierrc.json` ou `rust-toolchain.toml` diffèrent de HEAD | décidée |

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
