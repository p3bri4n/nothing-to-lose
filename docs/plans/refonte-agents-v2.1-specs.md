# Spécifications — Organisation multi-agents Claude Code (v2.1)

> **Statut dans ce dépôt : proposition de l'utilisateur, non décidée.** Texte fourni par l'utilisateur le 2026-11-07 et enregistré tel quel (reproduction fidèle ; seul cet encadré est ajouté).
>
> Réponses déjà données par l'utilisateur : le `developpeur` est **conservé pour les étapes isolées** ; une **file `docs/blockers.md`** est retenue ; la refonte ne commence **qu'après E10** (la fin d'E10 et d'E10b est atteinte, E11 et E12 restent). Un **plan de migration** reste à écrire et à soumettre à l'utilisateur avant toute modification des agents ou de `CLAUDE.md`.
>
> Écarts connus avec l'existant du dépôt (à traiter dans le plan de migration) : les dossiers s'appellent `docs/decisions`, `docs/technique` et `docs/journal` (et non `adr`, `tech`) ; les hooks du projet sont en Python (`guard_bash.py`, `format_on_edit.py`) ; le cœur de la simulation est en Rust (les règles de déterminisme du §8 passent par `clippy` et le test de rejeu, non par des motifs Python) ; `CLAUDE.md` porte aussi les règles d'infrastructure et de CI, qui doivent rester toujours chargées. Voir l'entrée de journal [2026-11-07-circuit-ci-agents.md](../journal/2026-11-07-circuit-ci-agents.md).

---

> Statut : proposition · Date : 7 novembre 2026
> Objet : réorganiser les sous-agents du projet, fiabiliser les passations, imposer les périmètres par hooks, rendre l'activité visible et mesurable.

**Changements v2.1 (relecture)** : responsable de la doc technique désigné ; tests d'acceptation écrits avant l'implémentation (TDD) et protégés ; Bash en liste blanche pour tous les agents sauf le debogueur ; passations archivées au lieu d'être supprimées ; revue du challenger au niveau du jalon ; corrections de bugs dans les scripts (chemins, ligne de statut, rapport).

---

## 1. Objectifs et principes

### 1.1 Objectifs
1. **Fiabilité** : aucune règle critique (périmètre d'écriture, déterminisme) ne repose uniquement sur le prompt.
2. **Continuité** : aucun agent ne repart à froid ; tout passage de relais ou blocage est écrit dans un fichier.
3. **Lisibilité** : l'utilisateur voit en un coup d'œil qui travaille, à quel coût, avec quel verdict.
4. **Mesurabilité** : chaque agent doit pouvoir justifier son existence par des données d'usage.

### 1.2 Principes directeurs
- **Peu d'agents, une tâche claire chacun** (cible : 8, puis élagage après mesure).
- **Contexte isolé là où il apporte quelque chose** : exploration bruyante, revue indépendante, tests écrits sans voir l'implémentation.
- **La session principale garde le fil** : elle planifie, implémente, rédige les ADR et pose les questions structurantes.
- **Des preuves, pas des affirmations** : tout verdict s'accompagne de la sortie qui le justifie.
- **Les règles vérifiables sont vérifiées par l'outillage** (lint, tests de rejeu), pas par un LLM.

---

## 2. Changements par rapport à la v1

| v1 | v2 | Raison |
|---|---|---|
| explorateur + synthetiseur | **lecteur** (fusion) | Deux agents Haiku en lecture seule qui se recoupent |
| relecteur (Haiku) | **relecteur (Sonnet)** + garde-fous outillés | Violations de déterminisme trop subtiles pour Haiku |
| documentaliste rédige les ADR | documentaliste : journal, index, liens, mise en forme | Un ADR porte des nuances de décision |
| architecte planifie | **challenger** : critique plans et changements risqués | Doublon avec opusplan ; la valeur est dans la revue indépendante |
| developpeur | supprimé (option : parallélisme en worktree) | Doublon avec l'exécution Sonnet d'opusplan |
| Règles de délégation dans CLAUDE.md | Skill `/implement` + champs `description` | CLAUDE.md allégé, routage plus fiable |
| Périmètres d'écriture dans le prompt | Hooks `PreToolUse` par agent | Seule façon d'imposer un chemin |
| Escalade sans contexte | Fichier de passation obligatoire | Supprime la taxe de coordination |

---

## 3. Rôles

### 3.1 Session principale (opusplan)
- Mode plan (Opus) : plans de jalons découpés en étapes testables, écrits dans `docs/plans/`.
- Exécution (Sonnet) : implémentation des étapes, lancement de `just check`.
- **Mise à jour de la documentation technique** (`docs/tech/`) dans le même commit que le code qu'elle décrit.
- Rédaction des ADR (`docs/adr/`) après validation utilisateur.
- **Seule à écrire dans `docs/blockers.md`** : elle y inscrit les questions structurantes (les siennes ou celles remontées par le challenger et le debogueur) et les pose à l'utilisateur.
- Ne modifie jamais un test d'acceptation existant (`tests/acceptance/`) sans accord de l'utilisateur ; le relecteur le vérifie sur chaque diff.
- Vérifie les conclusions des agents en lecture seule avant d'agir dessus.
- Orchestration via le skill `/implement` (§6).

### 3.2 Catalogue des agents

| Agent | Modèle (effort) | Couleur | Outils | Écriture autorisée (Write/Edit) | Bash |
|---|---|---|---|---|---|
| lecteur | haiku (medium) | cyan | Read, Grep, Glob | aucune | non |
| chercheur-web | haiku (medium) | green | WebSearch, WebFetch, Write | `docs/recherches/` | non |
| documentaliste | haiku (medium) | green | Read, Grep, Glob, Write, Edit | `docs/journal/`, `docs/index.md`, `README.md` | non |
| executant | haiku (medium) | blue | Read, Grep, Glob, Write, Edit, Bash | tout sauf zones protégées et `tests/acceptance/` | liste blanche |
| relecteur | sonnet (high) | yellow | Read, Grep, Glob, Bash | aucune | liste blanche (git en lecture, `just lint`, `just check`) |
| testeur | sonnet (high) | yellow | Read, Grep, Glob, Write, Edit, Bash | `tests/`, `docs/eval/` | liste blanche (`just *`, lanceur de tests) |
| challenger | opus (high) | purple | Read, Grep, Glob, Write | `docs/revues/` | non |
| debogueur | opus (xhigh) | red | tous | tout sauf `tests/acceptance/` | libre |

**Zones protégées** (interdites à l'executant, à adapter aux chemins réels) : simulation, déterminisme, contrat de décision, journal d'événements, broker, prompts.

> **Limite connue** : les hooks sur Write/Edit ne contrôlent pas ce qu'une commande Bash écrit. C'est pourquoi Bash est absent ou en liste blanche pour tous les agents sauf le debogueur, dont le périmètre reste une consigne vérifiée par le relecteur.
>
> **À vérifier** : la prise en compte du champ `effort` pour Haiku selon la version ; s'il est ignoré, le retirer des en-têtes Haiku.

### 3.3 Fiches détaillées

#### lecteur
- **Quand l'utiliser** : localiser fichiers, définitions, usages ; résumer une sortie longue **présente sur disque** (logs, rapports d'éval, sorties de tests, retours utilisateur).
- **Ne pas l'utiliser** : pour analyser un non-déterminisme (le debogueur lit les logs bruts) ; quand la sortie est déjà dans le contexte principal.
- **Sortie** : chemins et numéros de ligne ; pour une synthèse : verdict, écarts à la baseline, commande de reproduction. Aucun avis ni proposition.

#### chercheur-web
- **Quand** : documentation, versions, API, licences, messages d'erreur.
- **Sortie** : faits sourcés, datés, avec niveau de confiance (élevé / moyen / faible) ; fiche écrite dans `docs/recherches/AAAA-MM-JJ-sujet.md`.
- **Interdit** : prendre ou recommander une décision.

#### documentaliste
- **Quand** : fin de session (journal), mise à jour de l'index et des liens.
- **Contrôle de cohérence** : en fin de session, compare les modules modifiés (`git diff --stat` fourni par la session principale) à `docs/tech/` et liste dans le journal les docs qui n'ont pas suivi.
- **Interdit** : écrire dans `docs/adr/` ou `docs/tech/` (rédigés par la session principale).

#### executant
- **Quand** : renommages, formatage, code passe-partout, déplacements, configuration, petits scripts.
- **Interdit** : toute écriture en zone protégée (bloquée par hook) ; toute commande Bash hors liste blanche (bloquée par hook).
- **Fin de tâche** : lance `just check` et joint la sortie.

#### relecteur
- **Quand** : première relecture de tout diff avant commit.
- **Contrôles** : règles non négociables (déterminisme, pare-feu d'information), tests manquants, oublis évidents.
- **Préalable obligatoire** : `just lint` (inclut les règles de déterminisme outillées, §8) puis `just check` ; leurs sorties sont jointes au verdict.
- **Contrôle spécifique** : toute modification d'un fichier existant de `tests/acceptance/` ⇒ verdict `Escalade challenger`.
- **Verdicts** : `OK` · `À corriger` · `Escalade challenger`. Un `OK` n'est valide que si `just lint` et `just check` sont verts dans la même relecture.

#### testeur
- **Quand** : dès qu'une étape de plan est validée, **avant** l'implémentation (TDD).
- **Entrée** : l'étape du plan et ses critères d'acceptation, pas le code en cours.
- **Responsabilités** : tests d'acceptation de l'étape dans `tests/acceptance/<etape>/`, tests unitaires, non-régression (seed, tick, agent), invariants, `just eval` et comparaison à la baseline.
- **État attendu à la livraison** : les nouveaux tests d'acceptation **échouent** (rouge) pour la bonne raison ; les tests existants restent verts.
- **Sortie** : tests écrits + sortie d'exécution montrant le rouge attendu + écart à la baseline.

#### challenger
- **Quand** : (1) tout **plan de jalon** avant exécution (une fois par jalon, pas par étape) ; (2) tout diff escaladé par le relecteur ; (3) toute cause racine « de conception » remontée par le debogueur.
- **Posture** : « Staff Engineer » : trous, cas limites, hypothèses implicites, conflits avec les ADR existants.
- **Sortie** : revue dans `docs/revues/` + questions structurantes proposées, que la session principale reporte dans `docs/blockers.md`.
- **Interdit** : écrire le plan à la place de la session principale.
- **Note** : même famille de modèle que le planificateur ; la valeur vient du contexte isolé. Si les revues apportent peu, tester un autre modèle (via `/advisor` ou un outil externe).

#### debogueur
- **Quand** : déclenché uniquement par une escalade (§5) ou à la demande explicite.
- **Entrée obligatoire** : fichier de passation (§5.2). Sans passation, il commence par la demander.
- **Démarche** : reproduction → réduction → cause racine **prouvée** → correctif minimal → test de non-régression dans `tests/regression/`.
- **Interdit** : modifier `tests/acceptance/` (bloqué par hook) ; un test d'acceptation jugé faux est signalé, pas corrigé.
- **Renvoi** : si la cause relève de la conception → challenger, sans corriger.

---

## 4. Format de retour commun

Chaque agent commence sa réponse par **une ligne d'en-tête** au format exact :

```
[<agent>] VERDICT: <OK|À corriger|Escalade <cible>|Fait|Bloqué> — <résumé en 10 mots max>
```

Puis, dans cet ordre :
1. **Preuves** : commandes lancées et extrait de sortie (code de retour, lignes pertinentes).
2. **Détail** : constats, avec `chemin:ligne`.
3. **Suite proposée** (sauf lecteur et chercheur-web).

Un verdict sans section Preuves est considéré comme invalide par la session principale.

---

## 5. Escalade et passations

### 5.1 Règles d'escalade
| Déclencheur | Action |
|---|---|
| 2 échecs consécutifs de `just check` sur la même étape, **comptés à partir de la première tentative d'implémentation** (le rouge initial des tests d'acceptation ne compte pas) | Passation → debogueur |
| Non-déterminisme constaté (rejeu seed ≠) | Passation → debogueur, sans tentative préalable |
| Relecteur : `Escalade challenger` | Diff + verdict → challenger |
| Debogueur : cause de conception | Passation → challenger → question utilisateur |
| Décision structurante (architecture, contrat, dépendance, format de données) | Entrée dans `docs/blockers.md` + question utilisateur → ADR |

**Expérimentation parallèle (2 semaines)** : sur un blocage sur deux, essayer Sonnet + `/advisor` au lieu du debogueur ; consigner le résultat dans le journal (§9).

### 5.2 Fichier de passation
Emplacement : `docs/handoffs/AAAA-MM-JJ-<sujet>.md` (gitignoré). À la clôture : `statut: clos` et déplacement dans `docs/handoffs/archive/` (conservé pour les métriques du §9.4).

```markdown
---
de: session-principale
vers: debogueur
statut: ouvert            # ouvert | en-cours | clos
etape: <lien vers l'étape du plan>
branche: <nom>
---
## Objectif
<ce qui doit fonctionner>

## Échec observé
- Commande : `just check`
- Sortie (extrait) :
  ```
  <sortie exacte>
  ```

## Hypothèses testées
| Hypothèse | Test | Résultat |
|---|---|---|

## Fichiers modifiés depuis le dernier vert
- <chemin>

## Ne pas toucher
- <ADR / zones / contrats concernés>

## Prochaine action attendue
<une phrase>
```

**Règle** : aucun agent ne s'arrête au milieu d'une tâche sans avoir mis à jour la passation.

### 5.3 Fichier des points bloquants
Emplacement : `docs/blockers.md` (versionné).

```markdown
## B-007 — <titre court>
- Ouvert le : 2026-11-07 · source : challenger (écrit par la session principale)
- Contexte : <2-3 lignes, liens>
- Question à l'utilisateur : <formulée pour une réponse courte>
- Options : A) … B) … (conséquences en une ligne chacune)
- Statut : en attente | tranché → ADR-0012
```
Une entrée tranchée renvoie vers son ADR puis est déplacée en bas du fichier (section « Résolus »).

### 5.4 ADR
Emplacement : `docs/adr/NNNN-titre.md`, rédigé par la session principale (le documentaliste ne fait que l'indexer).
Sections : Contexte · Décision · Options écartées · Conséquences · Lien vers le blocker d'origine.

---

## 6. Orchestration : skill `/implement`

Emplacement : `.claude/skills/implement/SKILL.md`. Il remplace les règles de délégation de CLAUDE.md.

```markdown
---
name: implement
description: Exécuter une étape d'un plan validé de docs/plans/ avec tests, relecture et escalades. Utiliser quand l'utilisateur demande d'implémenter une étape ou un jalon.
---
# Procédure

1. Lire l'étape dans docs/plans/ et les ADR qu'elle cite. Si le plan du jalon n'a pas de revue du challenger dans docs/revues/, s'arrêter et la demander.
2. Testeur : tests d'acceptation de l'étape dans tests/acceptance/<etape>/. Attendre son verdict : nouveaux tests rouges pour la bonne raison, anciens tests verts.
3. Implémenter dans la session principale (code + docs/tech/ concernée). Tâches mécaniques → executant.
4. `just check`. Deux échecs consécutifs depuis le début de l'implémentation → créer la passation (docs/handoffs/) et escalader au debogueur.
5. Relecteur sur le diff. `À corriger` → retour en 3. `Escalade challenger` → challenger.
6. Décision structurante rencontrée → docs/blockers.md + question à l'utilisateur. Ne pas trancher.
7. Clôture : commit (code + tests + docs/tech/), documentaliste (journal, index, écarts de doc), passations closes archivées.

# Règles
- Exiger la ligne VERDICT et la section Preuves de chaque agent.
- Ne jamais transmettre une sortie longue dans un prompt d'agent : donner le chemin du log (build/logs/, §7.1).
- Ne jamais modifier un fichier existant de tests/acceptance/ sans accord de l'utilisateur.
```

Autres skills possibles : `/escalade` (crée la passation à partir de l'état courant), `/fin-session` (journal + rapport métriques).

---

## 7. Configuration technique

### 7.1 Arborescence
```
.claude/
  agents/            # 8 fichiers d'agents
  skills/implement/SKILL.md
  hooks/
    guard-paths.sh
    guard-bash.sh
    log-agent.sh
  statusline.sh
  logs/agents.jsonl  # gitignoré
  settings.json
docs/
  plans/ adr/ revues/ recherches/ journal/ eval/ tech/
  handoffs/          # gitignoré
    archive/
  blockers.md
  index.md
tests/
  acceptance/<etape>/  # protégé
  regression/
build/logs/          # gitignoré : sortie complète de chaque recette just
scripts/
  agent-report.sh
```

`.gitignore` :
```
.claude/logs/
docs/handoffs/
build/logs/
```

**Sorties longues** : chaque recette `just` (check, lint, eval) écrit elle-même sa sortie complète dans `build/logs/<recette>.log` et n'affiche qu'un résumé. Les agents se transmettent le chemin du log, jamais son contenu ; cela évite aussi les redirections, incompatibles avec les listes blanches Bash.

**Chemins dans les hooks** : toujours préfixer par `$CLAUDE_PROJECT_DIR` pour ne pas dépendre du répertoire courant.

### 7.2 Exemple de fichier d'agent
`.claude/agents/executant.md`
```markdown
---
name: executant
description: Tâches mécaniques sans décision — renommages, formatage, code passe-partout, déplacements, configuration, rédaction de petits scripts. Ne pas utiliser pour la simulation, le déterminisme, le contrat de décision, le journal, le broker ou les prompts.
model: haiku
effort: medium
color: blue
tools: Read, Grep, Glob, Write, Edit, Bash
hooks:
  PreToolUse:
    - matcher: "Write|Edit|MultiEdit|NotebookEdit"
      hooks:
        - type: command
          command: "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/guard-paths.sh deny src/simulation/ src/determinism/ src/decision/ src/journal/ src/broker/ prompts/ tests/acceptance/"
    - matcher: "Bash"
      hooks:
        - type: command
          command: "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/guard-bash.sh --allow 'just fmt' 'just check' 'just lint' 'git status' 'git diff*' 'git mv *' --protect src/simulation/ src/determinism/ src/decision/ src/journal/ src/broker/ prompts/ tests/acceptance/"
---
Tu exécutes des tâches mécaniques sans prendre de décision.
Commence ta réponse par : [executant] VERDICT: <Fait|Bloqué> — <résumé>
Termine toujours par `just check` et joins la sortie dans une section Preuves.
Si la tâche exige un choix de conception, réponds VERDICT: Bloqué et explique pourquoi.
```

Agents en écriture limitée (chercheur-web, documentaliste, testeur, challenger) : même hook en mode `allow`, par ex.
`"$CLAUDE_PROJECT_DIR"/.claude/hooks/guard-paths.sh allow docs/recherches/`

Debogueur : `guard-paths.sh deny tests/acceptance/`.
Relecteur : `guard-bash.sh --allow 'git diff*' 'git log*' 'git show*' 'git status' 'just lint' 'just check'`.
Testeur : `guard-bash.sh --allow 'just *' '<lanceur de tests> *'`.

> ⚠️ Les chemins `src/...` sont des exemples : à remplacer par ceux du dépôt. Vérifier la prise en charge du champ `hooks` dans l'en-tête d'agent selon la version de Claude Code ; à défaut, utiliser des hooks globaux dans `settings.json`.

### 7.3 `guard-paths.sh`
```bash
#!/usr/bin/env bash
# Usage : guard-paths.sh allow|deny <prefixe>...
# Lit le JSON du hook PreToolUse sur stdin. Code 2 = blocage (stderr renvoyé à Claude).
mode="$1"; shift
input=$(cat)
path=$(jq -r '.tool_input.file_path // .tool_input.notebook_path // empty' <<<"$input")
[ -z "$path" ] && exit 0
root="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"
rel=$(realpath -m --relative-to="$root" "$path")

# Toute écriture hors du dépôt est refusée, quel que soit le mode
case "$rel" in ../*|..) echo "Écriture hors du dépôt refusée : $path" >&2; exit 2 ;; esac

match=0
for p in "$@"; do
  case "$rel" in "$p"*) match=1 ;; esac
done

if { [ "$mode" = allow ] && [ $match -eq 0 ]; } || { [ "$mode" = deny ] && [ $match -eq 1 ]; }; then
  echo "Écriture refusée ($mode : $*) : $rel" >&2
  exit 2
fi
exit 0
```

### 7.4 `guard-bash.sh` (liste blanche paramétrable)
```bash
#!/usr/bin/env bash
# Usage : guard-bash.sh --allow <motif>... [--protect <chemin>...]
# Motifs au format glob shell. Refuse aussi les enchaînements et redirections.
allow=(); protect=(); mode=""
for a in "$@"; do
  case "$a" in
    --allow) mode=allow ;; --protect) mode=protect ;;
    *) [ "$mode" = allow ] && allow+=("$a") || protect+=("$a") ;;
  esac
done
cmd=$(jq -r '.tool_input.command // empty')

# Pas d'enchaînement ni de redirection : une commande = une action contrôlable
case "$cmd" in *";"*|*"&&"*|*"||"*|*"|"*|*">"*|*"<"*|*'$('*|*'`'*)
  echo "Commande composée refusée : $cmd" >&2; exit 2 ;; esac

# Aucune mention d'un chemin protégé (ex. git mv vers la simulation)
for p in "${protect[@]}"; do
  p="${p%/}"   # « src/simulation » sans slash final doit aussi être détecté
  case "$cmd" in *"$p"*) echo "Chemin protégé dans la commande : $p" >&2; exit 2 ;; esac
done

for pat in "${allow[@]}"; do
  # shellcheck disable=SC2053
  [[ "$cmd" == $pat ]] && exit 0
done
echo "Commande hors liste blanche : $cmd" >&2
exit 2
```

### 7.5 `settings.json` (extraits)
```json
{
  "permissions": {
    "allow": [
      "Bash(just check)", "Bash(just lint)", "Bash(just eval)", "Bash(just fmt)",
      "Bash(git diff:*)", "Bash(git log:*)", "Bash(git status)"
    ]
  },
  "hooks": {
    "PreToolUse": [
      { "matcher": "Task|Agent",
        "hooks": [{ "type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/log-agent.sh start" }] }
    ],
    "PostToolUse": [
      { "matcher": "Task|Agent",
        "hooks": [{ "type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/log-agent.sh end" }] }
    ],
    "Notification": [
      { "hooks": [{ "type": "command",
        "command": "notify-send 'Claude Code' 'Une réponse est attendue'" }] }
    ]
  },
  "statusLine": { "type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/statusline.sh" }
}
```

### 7.6 `log-agent.sh`
```bash
#!/usr/bin/env bash
# Usage : log-agent.sh start|end — une ligne JSON par événement de délégation
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
mkdir -p .claude/logs
jq -c --arg ev "$1" '{
  t: (now | todate),
  ev: $ev,
  s: .session_id,
  a: .tool_input.subagent_type,
  d: .tool_input.description,
  r: (if $ev == "end" then (.tool_response | tostring | .[0:400]) else null end)
}' >> .claude/logs/agents.jsonl
exit 0
```
Le champ `r` conserve le début de la réponse, donc la ligne VERDICT (§4).

---

## 8. Garde-fous outillés du déterminisme

À intégrer dans `just lint` (le relecteur le lance systématiquement) :

| Règle | Mise en œuvre |
|---|---|
| Aléatoire sans seed explicite | Recherche de motifs interdits (`random.` hors module RNG central, `uuid4`, etc.) |
| Horloge système dans la simulation | Interdiction de `time.time`, `datetime.now` hors couche d'E/S |
| Itération sur ensembles non ordonnés | Règle de lint (`set`/`dict` itérés dans le cœur de simulation → tri explicite) |
| Pare-feu d'information | Test d'import : les modules agents n'importent pas l'état global |
| Rejeu | `just check` inclut un test : même seed + mêmes entrées ⇒ trace identique (hash) |

Chaque violation de déterminisme trouvée en revue ou en débogage donne lieu à une nouvelle règle dans ce tableau.

---

## 9. Retour visuel et métriques

### 9.1 Couleurs (par famille)
| Couleur | Famille | Agents |
|---|---|---|
| cyan | Lecture | lecteur |
| green | Recherche / doc | chercheur-web, documentaliste |
| blue | Production | executant |
| yellow | Contrôle | relecteur, testeur |
| purple | Critique | challenger |
| red | Escalade | debogueur |

### 9.2 Ligne de statut — `.claude/statusline.sh`
```bash
#!/bin/bash
in=$(cat)
cd "${CLAUDE_PROJECT_DIR:-$(jq -r '.workspace.project_dir // .cwd' <<<"$in")}" || exit 0
sid=$(jq -r '.session_id' <<<"$in")
m=$(jq -r '.model.display_name' <<<"$in")
ctx=$(jq -r '.context_window.used_percentage // 0 | floor' <<<"$in")
cost=$(jq -r '.cost.total_cost_usd // 0' <<<"$in")
log=.claude/logs/agents.jsonl

n=0; esc=0
if [ -f "$log" ]; then
  n=$(jq -c "select(.s==\"$sid\" and .ev==\"start\")" "$log" | wc -l)
  esc=$(jq -c "select(.s==\"$sid\" and .ev==\"start\" and .a==\"debogueur\")" "$log" | wc -l)
fi
open=$(grep -c 'Statut : en attente' docs/blockers.md 2>/dev/null); open=${open:-0}

c=$'\e[32m'; [ "$ctx" -ge 50 ] && c=$'\e[33m'; [ "$ctx" -ge 70 ] && c=$'\e[31m'
printf "%s │ ${c}ctx %s%%\e[0m │ \$%.2f │ délég. %s │ \e[31mesc. %s\e[0m │ ⏸ %s" \
  "$m" "$ctx" "$cost" "$n" "$esc" "$open"
```
Affichage : `Sonnet │ ctx 42% │ $1.37 │ délég. 7 │ esc. 1 │ ⏸ 2`
(⏸ = décisions en attente dans `docs/blockers.md`.)

### 9.3 Rapport hebdomadaire — `scripts/agent-report.sh`
```bash
#!/usr/bin/env bash
log=.claude/logs/agents.jsonl
echo "Appels par agent :"
jq -r 'select(.ev=="start") | .a' "$log" | sort | uniq -c | sort -rn
echo; echo "Verdicts :"
jq -r 'select(.ev=="end")
  | [.a, (((.r // "") | capture("VERDICT: (?<v>OK|À corriger|Escalade [a-z-]+|Fait|Bloqué)")? | .v) // "sans verdict")]
  | @tsv' "$log" \
  | sort | uniq -c | sort -rn
echo; echo "Escalades avec passation :"
ls docs/handoffs/archive/ 2>/dev/null | wc -l
```

### 9.4 Indicateurs suivis
| Indicateur | Source | Seuil d'alerte |
|---|---|---|
| Appels par agent / semaine | agents.jsonl | < 1 → candidat à suppression |
| Réponses sans VERDICT | agents.jsonl | > 10 % → revoir le prompt de l'agent |
| Travail repris par la session principale | journal de session (noté à la main) | > 30 % des appels → agent inutile |
| Escalades / étape | agents.jsonl | tendance à la hausse → plans trop gros |
| Coût par session | ligne de statut / journal | à comparer à la baseline (§10) |
| Blockers ouverts > 3 jours | blockers.md | relancer l'utilisateur |

---

## 10. Protocole d'évaluation

**Phase 1 — Observation (2 semaines)** : configuration v2 + hooks de journalisation ; aucune autre modification.

**Phase 2 — Comparaison** : rejouer 5 à 10 tâches réelles déjà terminées (même commit de départ, même énoncé) dans trois configurations :
1. v2 complète ;
2. Sonnet seul + `/advisor` (Opus) ;
3. Opus seul.

Mesurer pour chaque tâche : réussite (`just check` + `just eval` vs baseline), coût, durée, nombre d'interventions manuelles.

**Phase 3 — Décision** : supprimer ou fusionner les agents sous les seuils du §9.4 ; consigner la décision dans un ADR.

---

## 11. CLAUDE.md allégé (squelette)

```markdown
# Projet
<2-3 lignes : but, stack, commandes just>

# Règles non négociables
- Déterminisme : <résumé> — vérifié par `just lint` et le test de rejeu.
- Pare-feu d'information : <résumé>.
- Décision structurante → docs/blockers.md + question à l'utilisateur → ADR. Ne jamais trancher seul.

# Travail
- Implémentation d'une étape : skill /implement.
- Tout verdict d'agent sans section Preuves est invalide.
- Sorties longues : écrire sur disque, transmettre le chemin.

# Erreurs déjà commises (à ne pas répéter)
- <ajouté après chaque correction>
```

---

## 12. Plan de migration

| Étape | Contenu | Critère de fin |
|---|---|---|
| 0 | Recettes `just` écrivant leurs logs dans `build/logs/` | Un `just check` produit `build/logs/check.log` |
| 1 | Hooks `guard-paths`, `guard-bash`, `log-agent` + `.gitignore` | Écriture hors périmètre, commande hors liste et commande composée bloquées lors d'un test manuel |
| 2 | Réécriture des 8 fichiers d'agents (en-têtes, couleurs, format VERDICT) | Chaque agent répond avec la ligne VERDICT |
| 3 | Skill `/implement`, allègement de CLAUDE.md | Une étape complète exécutée via `/implement` |
| 4 | Gabarits passation / blockers / ADR | Une escalade réelle passe par un fichier de passation |
| 5 | Règles de déterminisme dans `just lint` + test de rejeu | Une violation volontaire est détectée |
| 6 | Ligne de statut, notifications, rapport hebdo | Affichage conforme au §9.2 |
| 7 | Phases d'observation et d'évaluation (§10) | ADR de décision sur la configuration finale |

---

## 13. Critères d'acceptation globaux
- [ ] Aucun agent ne peut écrire hors de son périmètre via Write/Edit (testé pour chacun).
- [ ] Aucun agent sauf le debogueur ne peut lancer une commande Bash hors liste blanche.
- [ ] Aucun fichier existant de `tests/acceptance/` n'est modifié sans accord explicite (vérifié par le relecteur).
- [ ] Chaque étape démarre avec des tests d'acceptation rouges et se termine au vert.
- [ ] 100 % des escalades vers le debogueur ont un fichier de passation (archivé).
- [ ] Toute décision structurante a un blocker puis un ADR.
- [ ] ≥ 90 % des réponses d'agents ont une ligne VERDICT et une section Preuves.
- [ ] CLAUDE.md fait moins de 80 lignes.
- [ ] Le rapport hebdomadaire tourne sans erreur.
- [ ] La comparaison du §10 est faite et sa conclusion consignée.
