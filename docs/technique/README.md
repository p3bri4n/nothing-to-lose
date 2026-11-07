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
- [`outillage.md`](outillage.md) — source unique des versions (`mise.toml`, `rust-toolchain.toml`), `just versions`, `just tools-test`, `tools/verify_pp.sh`, procédure de mise à jour (disponible)

Chaque page indique en tête la date de sa dernière mise à jour.
