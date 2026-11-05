# Hook SessionStart de Claude Code : affichage utilisateur, format JSON, configuration

Date de la recherche : 2026-11-05. Version locale : Claude Code 2.1.318. La dernière entrée du changelog officiel consultée est la 2.1.318 (4 novembre 2026), donc la doc et la version locale concordent.

## Réponse courte

Un hook `SessionStart` ne peut pas afficher du texte à l'utilisateur à coup sûr : son stdout brut va au contexte du modèle, et seul le champ JSON de premier niveau `systemMessage` est destiné à l'utilisateur. Dans la pratique, plusieurs issues GitHub ouvertes (septembre et octobre 2026) signalent que ce `systemMessage` est parfois absent du TUI par défaut, et absent des clients VS Code et application de bureau. Pour le projet, la configuration la plus sûre est un hook `command` en forme exec (`args: []`), matcher `startup`, `timeout` court, `systemMessage` pour le message, et `additionalContext` pour le contexte modèle.

## Détails utiles

### 1. Qui voit quoi

| Sortie du hook | Voit l'utilisateur | Voit le modèle |
|---|---|---|
| Stdout brut, sortie 0 (texte non JSON) | Non (uniquement le log de debug) | Oui, ajouté au contexte |
| `systemMessage` (JSON, premier niveau) | Oui, « Warning message shown to the user » | Non (documenté comme affichage utilisateur) |
| `hookSpecificOutput.additionalContext` (JSON) | Non, pas de message de chat | Oui, inséré au début de la conversation avant le premier prompt |
| Stderr, sortie 2 | Oui, sous forme de notice « `<hook name>` hook error » | Non, le session continue |
| Stderr, sortie 0 | Jamais | Jamais |

Point d'attention : la doc générale (tableau « Common JSON output fields ») dit que `suppressOutput` n'a aucun effet et que le stdout d'un hook réussi n'apparaît jamais dans la transcription. Le stdout brut d'un SessionStart est donc uniquement du contexte modèle, pas un message utilisateur.

### 2. Format JSON, codes de sortie, matcher

Sortie minimale utile (sur stdout, code 0) :

```json
{
  "systemMessage": "Say Again : session ouverte",
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "Contexte destiné au modèle, 10 000 caractères maximum."
  }
}
```

- Le champ `hookEventName` est requis dans `hookSpecificOutput` (il figure dans l'exemple officiel de sortie SessionStart).
- Codes de sortie (doc officielle, « Exit code output ») : 0 = succès, le JSON est appliqué ; 2 = erreur bloquante, mais SessionStart ne peut pas bloquer (stderr affiché à l'utilisateur, session continue) ; autre code = erreur non bloquante (notice, session continue).
- JSON invalide sur sortie 0 : erreur non bloquante avec le message de validation.
- Matchers SessionStart (doc officielle) : `startup` (nouvelle session), `resume` (`--resume`, `--continue`, `/resume`), `clear` (`/clear`), `compact` (compaction automatique ou manuelle), `fork` (session forkée).
- Limiter à `startup` : `"matcher": "startup"`. Pour `startup` et `resume`, la doc ne documente pas la syntaxe « `startup|resume` » pour SessionStart (non vérifié : la doc décrit une matcher « regex » pour d'autres événements seulement). Solution sûre : deux entrées distinctes dans le tableau, ou pas de matcher et filtrage dans le script à partir du champ `source` de l'entrée JSON (valeurs `startup`, `resume`, `clear`, `compact`, `fork`). Le champ `model` peut être absent.

### 3. Configuration `.claude/settings.json`

Exemple recommandé (forme exec : pas de shell, le chemin n'a pas besoin de guillemets) :

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/session-start.sh",
            "args": [],
            "timeout": 10
          }
        ]
      },
      {
        "matcher": "resume",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/session-start.sh",
            "args": [],
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

- Forme exec : si `args` est présent, `command` est résolu comme exécutable et lancé directement, sans shell ; les placeholders comme `${CLAUDE_PROJECT_DIR}` sont substitués comme chaînes simples. La doc recommande explicitement la forme exec pour tout hook qui référence un chemin placeholder.
- Forme shell (`args` absent) : la doc donne comme exemple `"\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/..."` ; en forme shell, il faut mettre les placeholders entre guillemets doubles. Cette forme est un second choix.
- `$CLAUDE_PROJECT_DIR` et `${CLAUDE_PROJECT_DIR}` apparaissent tous deux dans les exemples officiels ; la doc définit `${CLAUDE_PROJECT_DIR}` comme « the project root where the session started ».
- Chemin avec espaces et « : » : la forme exec n'utilise pas de shell, donc pas de découpage sur les espaces. **Non vérifié** dans la doc : le comportement exact avec ce chemin. À tester localement avec `just`/une commande de test avant adoption.
- Le script doit être exécutable (`chmod +x`) et avoir un shebang : **non vérifié** dans la doc consultée, mais cohérent avec les exemples officiels (`check-style.sh` appelé directement).
- `timeout` : en secondes. Défaut 600 s pour `command`. SessionStart n'est pas listé parmi les événements au délai réduit (30 s, pour `UserPromptSubmit`, `PreModelSwitch`, `PostModelSwitch` ; 10 s pour `MessageDisplay`).
- Confiance hors doc : la doc ne dit pas si un hook de `.claude/settings.json` demande une validation de confiance du dossier (seules les `permissions.allow`, `env`, etc. sont listées comme attendant la confiance). **Non vérifié** pour les hooks.

Où le mettre : `.claude/settings.json` (partagé, versionné) ou `.claude/settings.local.json` (personnel, hors git). Précédence : managed > ligne de commande > local projet > projet partagé > utilisateur. Les listes se fusionnent.

### 4. Limites

- Taille : `additionalContext`, `systemMessage`, `initialUserMessage` et le stdout brut sont plafonnés à 10 000 caractères. Au-delà, la sortie est écrite dans un fichier de session et le modèle reçoit le chemin et un aperçu de 2 000 caractères. Changelog 2.1.316 (31 octobre 2026) : même plafond de 10 000 caractères pour les hooks.
- Rendu Markdown et sauts de ligne : **non vérifié**. La doc ne dit rien sur le rendu de `systemMessage` (Markdown ou texte brut). Les sauts de ligne `\n` dans la chaîne JSON sont probablement affichés, mais ce n'est pas documenté : tester.
- Mode plein écran : le réglage est `"tui": "fullscreen"` (scope : tout fichier de réglages, y compris `~/.claude/settings.json`). La doc fullscreen indique que `/tui fullscreen` sauvegarde ce réglage et `/tui default` revient au rendu classique. La doc ne dit pas que le plein écran change l'affichage de `systemMessage`. En revanche, les issues GitHub ci-dessous rapportent que `systemMessage` s'affiche en plein écran là où il n'apparaît pas en rendu par défaut (observation d'utilisateurs, non confirmée par Anthropic).

### 5. Problèmes ouverts (issues GitHub, observations de tiers)

- [#98162](https://github.com/anthropics/claude-code/issues/98162), ouverte le 29 septembre 2026, état ouvert : `systemMessage` de SessionStart:startup « appears on screen only intermittently » en TUI (11 affichages sur 15 démarrages chez le rapporteur, versions 2.1.278 et 2.1.284). En `claude -p --output-format stream-json`, le message est toujours présent. Un commentaire rapporte que `"tui": "fullscreen"` le faisait apparaître (2.1.288) : observation, non officiel.
- [#96699](https://github.com/anthropics/claude-code/issues/96699), ouverte le 24 septembre 2026, état ouvert : après `/clear`, `systemMessage` n'apparaît pas en rendu par défaut (0 sur 17), mais apparaît en plein écran (2 sur 2) et dans la vue transcription (ctrl+o). Version 2.1.281 ; reproduit en 2.1.283 (Linux).
- [#80882](https://github.com/anthropics/claude-code/issues/80882), ouverte le 24 juillet 2026, marquée « stale » le 25 octobre 2026 : `systemMessage` de SessionStart n'apparaît pas dans l'extension VS Code ni dans l'application de bureau, alors qu'il fonctionne dans le CLI terminal. Un hook Stop affiche bien son `systemMessage` dans l'application de bureau. Les auteurs de l'issue citent la doc qui dit que le message est « displayed in the transcript as a system message » sans restriction par surface : citation de l'issue, non relue dans la doc.
- Conséquence : sur un client non terminal, un SessionStart ne peut pas parler à l'utilisateur de façon fiable. Le contournement décrit est de faire relayer `additionalContext` par le modèle (non fiable, dépend du modèle).
- Historique : des issues de mars et avril 2026 signalaient déjà une disparition de `systemMessage` en TUI (version 2.1.88 puis 2.1.119), marquées fermées en juin et avril 2026. Le retour de ces problèmes en septembre 2026 n'est pas expliqué par la doc.
- Pas de note de changelog trouvée qui corrige l'affichage de `systemMessage` de SessionStart jusqu'à 2.1.318 (recherche par mot-clé, changelog tronqué : vérification partielle).

## Niveau de confiance

- Routage stdout / `systemMessage` / `additionalContext` / stderr : **élevé** (documentation officielle code.claude.com, version 2.1.318 au changelog du 4 novembre 2026).
- Format JSON, codes de sortie, matchers : **élevé** (doc officielle).
- Limite de 10 000 caractères : **élevé** (doc officielle + changelog 2.1.316).
- Affichage réel de `systemMessage` au démarrage en TUI : **moyen à faible** : la doc dit oui, mais trois issues ouvertes de septembre-octobre 2026 signalent des absences. À vérifier sur la version locale 2.1.318 avant de compter dessus.
- Forme exec avec chemin contenant espaces et « : » : **non vérifié**, à tester.
- Rendu Markdown et sauts de ligne dans `systemMessage` : **non vérifié**.
- Sémantique du `tui` en plein écran pour les hooks : **faible** (observations d'issues seulement).

## Sources

- [Hooks reference, Claude Code docs](https://code.claude.com/docs/en/hooks.md) : consultée le 2026-11-05 ; matchers SessionStart, champs `source`/`model`, `hookSpecificOutput`, tableaux de sorties, timeout, plafond de 10 000 caractères, forme exec. Extraction partielle (la page fait 286 000 caractères et a été lue par morceaux).
- [Automate actions with hooks (guide), Claude Code docs](https://code.claude.com/docs/en/hooks-guide.md) : consultée le 2026-11-05 ; exemples `$CLAUDE_PROJECT_DIR`, matcher `compact`.
- [Settings files and precedence, Claude Code docs](https://code.claude.com/docs/en/settings.md) : consultée le 2026-11-05 ; fichiers et précédence ; hooks non listés parmi les clés attendant la confiance du dossier.
- [Settings reference, Claude Code docs](https://code.claude.com/docs/en/settings-reference.md) : consultée le 2026-11-05 ; index : `tui` (scope tout fichier), `hooks`, `disableAllHooks`. Détail de `tui` non lu (tronqué).
- [Fullscreen rendering, Claude Code docs](https://code.claude.com/docs/en/fullscreen.md) : consultée le 2026-11-05 ; `/tui fullscreen` et `/tui default`, réglage `tui` sauvegardé. Pas de mention de `systemMessage`.
- [Claude Code changelog, docs](https://code.claude.com/docs/en/changelog) : consultée le 2026-11-05 ; dernière entrée 2.1.318 (4 novembre 2026) ; 2.1.316 (31 octobre 2026) plafond 10 000 caractères ; 2.1.305 (20 octobre 2026) statut « Running start-up hooks » pour SessionStart en VS Code.
- [Issue #98162, anthropics/claude-code](https://github.com/anthropics/claude-code/issues/98162) : ouverte le 29 septembre 2026, ouverte à la date de consultation. Observation d'utilisateurs (source secondaire).
- [Issue #96699, anthropics/claude-code](https://github.com/anthropics/claude-code/issues/96699) : ouverte le 24 septembre 2026, ouverte à la date de consultation. Observation d'utilisateurs.
- [Issue #80882, anthropics/claude-code](https://github.com/anthropics/claude-code/issues/80882) : ouverte le 24 juillet 2026, marquée stale le 25 octobre 2026. Observation d'utilisateurs.
- Recherche web générale (sources secondaires, à titre de recoupement seulement) : [claudefa.st, session lifecycle hooks](https://claudefa.st/blog/tools/hooks/session-lifecycle-hooks) (exemples de matchers, non officiel).
