# Journal de développement

Une entrée par session de travail, nommée `AAAA-MM-JJ-sujet.md` (plusieurs sessions le même jour : suffixe `-2`, `-3`). Écrite en fin de session par `documentaliste`, à partir du compte rendu de la session principale.

**Lire les deux ou trois dernières entrées en début de session** : c'est le moyen de reprendre le fil.

**Titres de sections obligatoires** : le hook `SessionStart` (`tools/hooks/session_start.py`, voir [`../technique/hook-session-start.md`](../technique/hook-session-start.md)) lit la dernière entrée et affiche sa section `## Prochaines étapes` au démarrage de Claude Code, et `## Problèmes et points ouverts` dans le contexte du modèle. Ces deux titres doivent rester exactement tels quels (niveau 2, même graphie). Une section absente est simplement omise.

## Index

| Date | Sujet | Jalon |
|---|---|---|
| 2026-11-05 | [Conception initiale et squelette du dépôt](2026-11-05-conception.md) | avant P0 |
| 2026-11-05 | [Préparation de l'environnement (après-midi)](2026-11-05-pp-preparation.md) | PP |
| 2026-11-07 | [Amorçage Terraform et installation locale](2026-11-07-amorcage-terraform.md) | PP |

## Modèle d'entrée

```markdown
# AAAA-MM-JJ — Sujet

- **Jalon** : P0, P1…
- **Objectif de la session** : une phrase.

## Fait
- …

## Résultats
- `just check` : OK / en échec (détail)
- `just eval` : écarts par rapport à la référence, s'il y a lieu

## Décisions
- Décisions structurantes posées à l'utilisateur : liens vers `docs/decisions/NNNN-…`
- Choix techniques mineurs pris en autonomie, avec leur raison

## Problèmes et points ouverts
- …

## Prochaines étapes
- …
```
