# 0012 — Markdown exclu du formatage automatique

- **Date** : 2026-11-05
- **Statut** : décidée
- **Contexte** : PP prévoit un formatage automatique après modification de fichier (hooks Claude Code). Il faut décider si les fichiers Markdown de la documentation en font partie.
- **Options présentées** : non consignées dans le compte rendu de la session (décision prise directement par l'utilisateur).
- **Recommandation des agents** : non consignée dans le compte rendu de la session.
- **Décision de l'utilisateur** : les fichiers Markdown sont exclus du formatage automatique. Les autres types sont formatés : rustfmt, ruff, taplo, terraform fmt, shfmt, prettier.
- **Conséquences** :
  - la documentation sous `docs/` et les autres fichiers Markdown ne sont pas réécrits par le formatage ;
  - les hooks de formatage doivent exclure `*.md` ;
  - la vérification des liens de la documentation reste assurée par `tools/check_links.py`.
- **Documents mis à jour** : `docs/decisions/README.md`, `docs/conception/16-jalons.md`, `docs/conception/17-questions-ouvertes.md`.
