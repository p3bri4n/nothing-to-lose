# 2026-11-07 — Circuit Git, CI et garde-fous des agents (après-midi et soirée)

- **Jalon** : PP (préparation de l'environnement), étapes E3 à E10b. E11 et E12 restent à faire.
- **Objectif de la session** : mettre en place le circuit de travail des agents (une pull request par étape, fusion réservée à l'utilisateur, garde-fous Bash, formatage, secrets, CI alignée sur mise) avant toute écriture de code de simulation.

## Fait
Chaque étape a été livrée par pull request, fusionnée par l'utilisateur :
- **#1 E3** : `bypass_mode = "pull_request"` ; plus de push direct sur la branche principale. `tf-apply` fait par l'utilisateur.
- **#2 E4** : `tools/check_tool_versions.py`, recettes `just versions` et `just tools-test`. Correction de `run_version` (erreur `OSError`) pendant l'étape.
- **#3 E5** : `tools/fmt.py`, fichiers de configuration des formateurs, recettes `just fmt`, `just fmt-check`, `just lint` et `just check`. Commit « formatage initial » du prototype `index.html`.
- **#4 E6** : hook PostToolUse `format_on_edit.py` avec garde de configuration (décision 0020). Essai de bout en bout : un Write est formaté ; un Edit suivant est accepté sans relecture préalable (règle R8 non observée) ; le hook se déclenche pour un sous-agent.
- **#5 E7** : hook Git `pre-commit`, fermé par défaut ; gitleaks ; recettes `secrets-scan`, `pre-commit`, `hooks-install` et `verify-pp secrets`. Historique vérifié : aucun secret. Test en conditions réelles : un lien cassé est refusé, un commit propre est accepté.
- **#6 E8** : modèles de pull request et de ticket GitHub ; contrôle de la liste de contrôle (`check_pr_checklist.py`) ; recette `just actionlint`.
- **#7 E9** : CI alignée sur mise ; actions épinglées par SHA ; contrôle bloquant de la liste de contrôle. Premier run : 37 s. Contre-épreuve C3 réussie : case décochée, job `ci-cpu` en échec ; case recochée, succès.
- **#8 E10** : garde-fous Bash `guard_bash.py` (hook PreToolUse, analyseur de shell maison), circuit Git des agents, page `docs/technique/circuit-git.md`, section circuit dans `CLAUDE.md`. Essai réel : `--no-verify`, `git commit -an`, `gh pr merge --auto` et push forcé vers la branche principale sont refusés.
- **#9 E10b** : Terraform : variable `agents_account`, collaborateur à droit Write, ruleset à une approbation, CODEOWNERS et `require_last_push_approval`. Recette `just verify-pp merge-barrier`. Garde étendu aux identifiants GitHub, avertissement de session, procédure `docs/technique/compte-machine-agents.md`. Phrase de `CLAUDE.md` reformulée pour `GITHUB_TOKEN` et `GH_TOKEN`.
- Décisions rédigées : [0020](../decisions/0020-securite-hook-formatage.md) à [0028](../decisions/0028-garde-bash-identifiants-github.md).

## Résultats
- `just lint` : vert à chaque pull request. Dernière exécution : 367 tests des outils.
- `just eval` : sans objet (aucun code de simulation touché).
- `python3 tools/check_links.py` : 0 lien cassé.
- Essais réels consignés plus haut (hook de formatage, hook Git, garde Bash, contre-épreuve de la liste de contrôle).
- Non exécuté : `tf-plan` réel d'E10b (les agents n'ont pas de jeton d'administration). Il reste à faire par l'utilisateur.

## Décisions
Décisions posées à l'utilisateur et tranchées :
- [0020](../decisions/0020-securite-hook-formatage.md) : garde de configuration du hook de formatage (option c).
- [0021](../decisions/0021-fusion-compte-machine-agents.md) : compte machine pour les agents, une approbation requise, fusion par l'utilisateur seul (option 2, plus stricte que la recommandation).
- [0022](../decisions/0022-panne-garde-bash.md) : en cas de panne du garde, refus seulement pour `git` et `gh`.
- [0023](../decisions/0023-perimetre-garde-bash.md) : règles ajoutées au-delà du plan conservées ; garde sur Edit et Write reporté à la refonte des agents.
- [0024](../decisions/0024-jeton-compte-machine-classique.md) : jeton classique à portée `repo`. GitHub ne permet pas de jeton à granularité fine pour un collaborateur d'un dépôt personnel.
- [0025](../decisions/0025-barriere-serveur-codeowners.md) : CODEOWNERS et revue du propriétaire.
- [0026](../decisions/0026-isolement-identifiants-claudeus.md) : agents dans Claudeus comme cible ; mesures intérimaires sur l'hôte.
- [0027](../decisions/0027-portee-workflow-jamais.md) : portée `workflow` jamais accordée aux agents.
- [0028](../decisions/0028-garde-bash-identifiants-github.md) : garde étendu à `gh auth` et à `GH_TOKEN`. `git reset --hard` et `git clean -fdx` restent volontairement hors du périmètre du garde.

Choix mineurs pris en autonomie, avec leur raison :
- Options `shfmt` explicites et `target-version` de ruff à py314 (étape E5).
- `.yml` ajouté à la table des formateurs.
- Analyseur de shell maison pour le garde : `shlex`, `bashlex` et `tree-sitter` écartés. Raisons dans [`garde-fous-bash.md`](../technique/garde-fous-bash.md) (`shlex` gère mal les heredocs et les `$(…)`, `bashlex` est sous GPL-3 et peu maintenu, `tree-sitter` serait une dépendance lourde donc une décision structurante).
- Fail-closed pour `git` et `gh` seulement (précise 0022).
- Injection corrigée dans `gpu-eval.yml` (règle R10). Déclencheurs et garde inchangés.
- `wrangler-action` passé de v3 à v4.1.3 (déploiement désactivé).
- Version de mise 2026.11.0 en CI : exception à la règle des deux semaines de délai.
- `%(push)` à la place de `%(push:remoteref)` dans le garde.

Discussion sans décision d'implémentation : spécifications de l'utilisateur sur une organisation multi-agents de Claude Code v2.1 (lecteur, relecteur en Sonnet, challenger, hooks de périmètre par agent, format VERDICT et Preuves, fichiers de passation, ADR, skill `/implement`, TDD avec tests protégés, règles de déterminisme dans `just lint`, ligne de statut, métriques, protocole d'évaluation).
- Avis de la session : adopter le format VERDICT et Preuves, la passation pour le `debogueur`, la fusion de `explorateur` et `synthetiseur` en « lecteur », le `relecteur` en Sonnet, un garde unique en Python avec profils par agent (lisant `agent_type`), la ligne de statut. Reporter à P1 les règles de déterminisme (clippy `disallowed-*`, test de rejeu) et le TDD à tests protégés. Mesurer avant de décider du reste. Ne pas renommer les dossiers de `docs/`.
- Réponses de l'utilisateur : (1) garder le `developpeur` pour les étapes isolées ; (2) une file `blockers.md` ; (3) attendre la fin d'E10 avant de toucher aux agents.
- Le texte des spécifications est enregistré tel quel dans [`docs/plans/refonte-agents-v2.1-specs.md`](../plans/refonte-agents-v2.1-specs.md) (statut : proposition, non décidée). Un plan de migration reste à écrire et à soumettre à l'utilisateur avant toute modification des agents ou de `CLAUDE.md`.

## Problèmes et points ouverts
- **Barrière de fusion intérimaire** : sur l'hôte, les identifiants du propriétaire restent à portée des agents tant que Claudeus n'est pas adapté (0026). La barrière n'est pas réelle avant cela.
- **Contournement administrateur** en mode `pull_request` sur un dépôt personnel : non testé.
- **Mention « compte machine » dans les conditions de GitHub** : aucune déclaration formelle trouvée. La session a cité les conditions de mémoire ; la vérification par `chercheur-web` a été proposée et n'est pas faite.
- **Hook PreToolUse sous `--dangerously-skip-permissions`** : exécution non confirmée (règle R7). À vérifier à E11.
- `MultiEdit` non testé. Seuls Write et Edit sont couverts par l'essai du hook de formatage.
- Garde sur Edit et Write vers `.git/`, `.githooks/` et `.claude/settings.json` : reporté à la refonte des agents (0023).
- Affichage du nombre d'erreurs du garde à l'ouverture de session : non codé (0022).
- 16 avertissements `ruff check` préexistants, hors des fichiers d'E4 à E10.
- Fixtures de format `bad.*` exclues de `fmt-check`.
- Rust passe par mise (rustup). Le cache de la CI et l'installation seront mesurés au premier `Cargo.toml`. `rustfmt.toml` (max_width 100) à reconfirmer en P1.
- Les actions `dtolnay/rust-toolchain`, `extractions/setup-just` et `astral-sh/setup-uv` restent dans `actions.tf` : leur retrait est à prévoir.
- `docs/decisions/0015` : sandbox reporté (voir 0026).
- Restes de l'entrée du matin : `infra/terraform/terraform.tfvars.example` supprimé localement, à trancher ; provenance de `key-art.png` (Gemini, droits non vérifiés) à documenter dans 0018 ; topic public `toulouse` non tranché ; réglage d'approbation des workflows de forks à poser avant le runner GPU (P2).

## Prochaines étapes
1. Utilisateur : renseigner `agents_account` dans `terraform.tfvars`, puis `just tf-plan` depuis la branche principale à jour. Attendu : ruleset modifié en place (`~`, pas de `-/+`), `bypass_actors` inchangés, invitation du collaborateur créée. Puis `just tf-apply`.
2. Utilisateur : accepter l'invitation depuis le compte machine ; créer son jeton classique (`repo` seule, 30 jours) ; le ranger dans `~/.config/nothing-to-lose/agents.env` (droits 600) ; révoquer l'ancien jeton U5 ; lancer Claude Code avec l'environnement nettoyé.
3. `just verify-pp merge-barrier`, puis essai négatif de fusion et essai du contournement administrateur sur une pull request triviale. Voie de secours : repasser le ruleset à 0 approbation par Terraform.
4. E11 (vérification finale : C1 à C4, R7 sous `--dangerously-skip-permissions`), à faire par l'utilisateur. Puis E12 (documentation et clôture de PP).
5. Écrire le plan de migration de l'organisation des agents et le soumettre à l'utilisateur, avant toute modification des agents ou de `CLAUDE.md`. Inclure la file `blockers.md`.
6. Fixer la date d'adaptation de Claudeus, prérequis d'une barrière réelle (0026).
7. Trancher les restes listés plus haut (`terraform.tfvars.example`, provenance de `key-art.png`, topic `toulouse`, approbation des workflows de forks).
