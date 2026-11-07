# Documentation technique

Décrit le code **tel qu'il existe**, pas tel qu'il est prévu (le prévu est dans `../conception/` et `../plans/`).

À créer au fil des jalons, une page par sujet :
- `carte.md` — pipeline de bake, formats des fichiers produits (P0)
- `simulation.md` — organisation du cœur Rust, tick, entités, systèmes (P1)
- `journal-format.md` — format de `journal.jsonl` et de `summary.json` (P1)
- `invariants.md` — liste des invariants vérifiés et leur signification (P1)
- `contrat-decision.md` — requêtes et réponses entre simulation et broker (P2)
- `laya.md` — schémas de questions, dataset, fine-tuning, métriques (P3)
- `survivants-llm.md` — prompts, format JSON, contrôles de cohérence (P4)
- `commandes.md` — toutes les commandes `just`, leurs options et leurs sorties
- [`ci-cd.md`](ci-cd.md) — Terraform, CI, runner GPU, déploiement (disponible)
- [`hook-session-start.md`](hook-session-start.md) — hook SessionStart : résumé de l'état du projet à l'ouverture de Claude Code (disponible)
- [`hook-format-on-edit.md`](hook-format-on-edit.md) — hook PostToolUse : formatage automatique du fichier que Claude vient d'écrire ou de modifier (`tools/hooks/format_on_edit.py`) (disponible)
- [`hooks-git.md`](hooks-git.md) — hook Git `pre-commit` (gitleaks sur les changements indexés, liens de la documentation), recettes `hooks-install`, `pre-commit`, `secrets-scan`, contournement `--no-verify`, faux positifs (disponible)
- [`garde-fous-bash.md`](garde-fous-bash.md) — hook `PreToolUse` `tools/hooks/guard_bash.py` et règles `deny` : refus de `--no-verify`, des push forcés ou vers `main`, des clés de configuration Git dangereuses, de `gh pr merge` et des modifications de la configuration GitHub ; comportement en cas de panne, règles, limites, journal `guard.log`, point à confirmer sous `--dangerously-skip-permissions` (disponible)
- [`outillage.md`](outillage.md) — source unique des versions (`mise.toml`, `rust-toolchain.toml`), formatage (`tools/fmt.py`, `just fmt`, `just fmt-check`, configurations), `just lint`, `just versions`, `just tools-test`, `tools/verify_pp.sh`, procédure de mise à jour (disponible)
- [`modeles-github.md`](modeles-github.md) — modèle de PR, formulaires de tickets, `tools/check_pr_checklist.py` (contrôle de la liste de contrôle, variables `PR_BODY` et `PR_AUTHOR`), `just actionlint` (disponible ; branché dans `ci.yml` en E9)
- [`circuit-git.md`](circuit-git.md) — circuit Git des agents : branche, commits, pull request, contrôles requis, rôle de l'utilisateur qui fusionne ; interdits et leurs raisons, identité des agents (U5 puis compte machine, E10b), essai manuel du garde-fou (disponible)

Chaque page indique en tête la date de sa dernière mise à jour.
