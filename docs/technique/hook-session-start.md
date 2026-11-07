# Hook SessionStart : résumé de « où on en est »

*Mise à jour : 2026-11-07 (avertissement sur l'identité GitHub de la session, revue d'E10b : [0028](../decisions/0028-garde-bash-identifiants-github.md) ; avertissement sur les erreurs du garde-fou Bash, décision [0022](../decisions/0022-panne-garde-bash.md) ; création : 2026-11-05, ajout du hook à la demande de l'utilisateur, hors périmètre initial de PP, voir [`../plans/PP.md`](../plans/PP.md) §8)*

Recherche sur le format du hook et ses limites : [`../recherches/2026-11-05-hook-sessionstart.md`](../recherches/2026-11-05-hook-sessionstart.md).

## Rôle

À l'ouverture de Claude Code, le hook résume l'état du projet à partir de la dernière entrée de `docs/journal/` et de l'état Git. Il ne bloque jamais le démarrage de la session.

## Fichiers et configuration

| Élément | Où | Détail |
|---|---|---|
| Script | `tools/hooks/session_start.py` | Python standard, aucune dépendance. Code de sortie toujours 0. |
| Configuration | `.claude/settings.json`, section `hooks.SessionStart` | Deux entrées, matchers `startup` et `resume`. |
| Commande | `python3 "$CLAUDE_PROJECT_DIR/tools/hooks/session_start.py"` | Guillemets obligatoires : le chemin du dépôt contient des espaces et un « : ». |
| Délai | `timeout` de 10 s | Git est interrogé avec un délai de 5 s par appel. |

Les matchers `clear`, `compact` et `fork` ne sont pas configurés : le résumé n'est pas réaffiché après `/clear`, une compaction ou un fork.

## Sortie

Le script écrit un unique objet JSON sur stdout :

```json
{
  "systemMessage": "…",
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "…"
  }
}
```

- `systemMessage` est destiné à l'utilisateur. Il contient le titre (« Nothing To Lose — où on en est »), le nom et le titre du dernier journal, la section « Prochaines étapes », puis l'état Git.
- `hookSpecificOutput.additionalContext` est injecté dans le contexte du modèle. Il contient le même contenu, plus la section « Problèmes et points ouverts ».
- Chaque champ est tronqué à 9 000 caractères (la limite de Claude Code est de 10 000).

L'état Git comprend : la branche courante, le dernier commit (`git log -1`, format `%h %s`), le nombre de lignes de `git status --short` (fichiers modifiés et non suivis), et un avertissement si aucun remote n'est configuré. Une commande Git en échec ou absente affiche « ? ».

**Identité GitHub.** Une ligne « Identité GitHub : … » s'ajoute aux deux champs si `GITHUB_TOKEN` est présent et non vide (jeton d'administration du propriétaire qui ne doit pas être dans l'environnement des agents) ou si `GH_TOKEN` est absent ou vide (`gh` et `git` n'utilisent pas le compte machine). Elle renvoie à [`compte-machine-agents.md`](compte-machine-agents.md), étape (f). **Aucune valeur n'est jamais affichée**, seulement la présence ou l'absence. Le test est `TokenWarningTest` de `tools/tests/test_session_start.py`.

### Avertissement sur le garde-fou Bash

Le script compte les lignes qui contiennent `hook error` dans `.cache/hooks/guard.log` (le journal du hook `PreToolUse` [`guard_bash.py`](garde-fous-bash.md)). Quand le nombre est supérieur à 0, une ligne est ajoutée à la fin des **deux** sorties (`systemMessage` et `additionalContext`) :

```
Garde-fou Bash : 3 ligne(s) « hook error » dans .cache/hooks/guard.log (le garde-fou a échoué ; les commandes git/gh sont refusées dans ce cas). Voir docs/technique/garde-fous-bash.md ; prévenir l'utilisateur.
```

Raison (décision [0022](../decisions/0022-panne-garde-bash.md)) : quand le garde-fou est en panne, il refuse les commandes `git` et `gh` ; l'utilisateur doit en être informé dès l'ouverture de la session. Le journal n'est jamais effacé par ce hook (il est borné par rotation vers `guard.log.1`, qui n'est pas lu) : le compteur ne retombe à 0 que si l'utilisateur supprime ou vide `guard.log` après avoir traité la cause. Journal absent, illisible ou sans ligne `hook error` : rien n'est affiché.

## Dernier journal

- Fichiers pris : `docs/journal/AAAA-MM-JJ-*.md`, dont le nom commence par une date (`README.md` est exclu).
- Tri : préfixe de date décroissant, puis date de modification du fichier. Deux sessions le même jour (suffixes `-2`, `-3`) sont départagées par leur date de modification.
- Le titre est la première ligne du fichier, sans `#`.

## Dépendance au format du journal

Le script extrait les sections par leur titre exact, de niveau 2 :

- `## Prochaines étapes` (affichée dans les deux sorties) ;
- `## Problèmes et points ouverts` (affichée seulement dans `additionalContext`).

Une section absente ou vide est simplement omise. Les entrées de journal doivent donc garder ces titres, tels que définis dans [`../journal/README.md`](../journal/README.md). Le modèle d'entrée et l'instruction du sous-agent `documentaliste` doivent suivre la même règle.

En cas d'erreur inattendue, le script renvoie « Résumé de session indisponible (…) » dans les deux champs.

## Limites connues

- **Affichage non vérifié** : trois issues GitHub (#98162, #96699, #80882) signalent que `systemMessage` d'un hook SessionStart peut ne pas apparaître selon l'interface (TUI par défaut, VS Code, application de bureau, après `/clear`). Le comportement n'a pas été vérifié avec Claude Code 2.1.318. **À tester à la prochaine ouverture.** Si le message n'apparaît pas, le contexte injecté permet tout de même de demander « où en est-on ? ».
- **Forme de commande** : la recherche recommandait la forme exec (champ `args`, sans shell). La configuration actuelle utilise la forme shell avec guillemets doubles, plus simple à lire ; elle a le même effet sur le chemin du dépôt.
- Tests : `tools/tests/test_session_start.py` couvre le compte des lignes `hook error` et la présence de l'avertissement dans les deux sorties (JSON produit par le vrai script, dossier de projet jetable). Le reste du résumé (journal, état Git) n'a pas de test automatisé.
