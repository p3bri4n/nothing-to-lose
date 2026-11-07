# Modèles GitHub et contrôle de la liste de contrôle

*Mise à jour : 2026-11-07 (étapes E8 et E9 du jalon PP : le contrôle est branché dans `ci.yml`)*

Décrit le code **tel qu'il existe** : modèle de pull request, formulaires de tickets, script `tools/check_pr_checklist.py` et ses tests, recette `just actionlint`. Le plan est dans [`docs/plans/PP.md`](../plans/PP.md) (étapes E8 et E9, risque R10, critère C3).

## État

| Élément | État |
|---|---|
| Modèle de pull request (`.github/pull_request_template.md`) et formulaires de tickets (`.github/ISSUE_TEMPLATE/`) | écrits dans la même étape E8 ; voir le dépôt pour leur contenu exact |
| `tools/check_pr_checklist.py` et ses tests | disponibles (`just tools-test`) |
| Recette `just actionlint`, ajoutée à `just lint` | disponible |
| **Branchement dans `ci.yml`** | **fait (E9)** : étape « Liste de contrôle de la pull request » du job `ci-cpu`, bloquante (voir ci-dessous) |

## Contrat du modèle de pull request

Le script ne dépend que de la structure suivante :

- une section dont le titre est **exactement** `## Liste de contrôle` (casse et accent compris ; espaces autour du titre tolérés) ;
- 7 cases `- [ ]` dans cette section ;
- la section se termine au titre `## ` suivant, ou à la fin du corps. Un titre `### ` ne la termine pas.

Les 7 points (plan PP, E8) : `just lint` / `just check` passe ; `just eval` lancé si la simulation ou les IA sont touchées ; `docs/technique/` à jour ; test de non-régression si la PR corrige un bug ; décision structurante posée à l'utilisateur ou « sans objet » ; `reports/baseline.json` inchangé ou changement expliqué ; aucun secret. Un point qui ne s'applique pas est **coché** et suivi de « — sans objet ».

## `tools/check_pr_checklist.py`

Bibliothèque standard uniquement. La logique est pure (`check_body`, `check_pull_request`, `extract_section`, `parse_checkboxes`) ; seule `main()` lit l'environnement.

### Variables d'environnement

| Variable | Rôle |
|---|---|
| `PR_BODY` | Corps de la pull request. Absente ou vide : traitée comme un corps vide (donc section absente, code 1). |
| `PR_AUTHOR` | Login de l'auteur de la PR. `dependabot[bot]` (comparaison exacte) est **exempté** : message, code 0. |

Le corps n'est **jamais** passé en argument ni interpolé dans un `run:` (injection, risque R10). En CI il est transmis par `env:` (étape de `.github/workflows/ci.yml`) :

```yaml
- name: Liste de contrôle de la pull request
  if: ${{ !cancelled() && github.event_name == 'pull_request' }}
  env:
    PR_BODY: ${{ github.event.pull_request.body }}
    PR_AUTHOR: ${{ github.event.pull_request.user.login }}
  run: python3 tools/check_pr_checklist.py
```

Essai local :

```bash
PR_BODY="$(cat .github/pull_request_template.md)" python3 tools/check_pr_checklist.py   # code 1
PR_BODY="$(sed 's/- \[ \]/- [x]/' .github/pull_request_template.md)" python3 tools/check_pr_checklist.py   # code 0
```

### Branchement dans la CI

- L'étape n'existe que dans `ci.yml`, job `ci-cpu` ; elle ne s'exécute que pour `github.event_name == 'pull_request'` (jamais sur un push vers `main`). `!cancelled()` la fait tourner même après l'échec d'une étape précédente.
- Le workflow se déclenche sur `pull_request` avec les types `opened`, `edited`, `synchronize` et `reopened` : modifier la description d'une PR relance `ci-cpu`, qui relit le corps à jour. Cocher une case suffit donc à faire passer le check. Pour relancer le contrôle, **modifier la description de la PR** (cocher la case) : « Re-run jobs » rejoue le job avec l'ancien corps de la PR et échouerait de nouveau.
- Le contrôle est **bloquant** : `ci-cpu` est le check obligatoire du ruleset de `main`. Une case décochée fait échouer le job avec « Liste de contrôle incomplète » et la liste des cases concernées.
- Le corps ne passe **jamais** par une expression `${{ }}` dans un `run:` (R10). Le script est lancé par le `python3` de mise.
- Contre-épreuve de C3 à faire sur une vraie PR (décocher une case, vérifier l'échec, la recocher) : non vérifiable en local.

### Comportement

- Les commentaires HTML (`<!-- … -->`, y compris sur plusieurs lignes) sont retirés avant l'analyse : les consignes ou exemples laissés dans le modèle ne comptent pas comme des cases ni comme un titre.
- Fins de ligne CRLF et espaces (indentation, espaces multiples) tolérés. Puces `-` (de préférence), `*` ou `+` ; case cochée `[x]` ou `[X]`.
- Seule la **première** section « Liste de contrôle » est lue ; les cases hors de la section sont ignorées.
- Sortie sur stdout, en français.

### Codes de retour

| Code | Cas | Message |
|---|---|---|
| `0` | Toutes les cases cochées | `Liste de contrôle complète (N case(s) cochée(s)).` |
| `0` | Auteur exempté | `PR de dependabot[bot] : liste de contrôle non exigée.` |
| `1` | Au moins une case décochée | `Liste de contrôle incomplète : cases non cochées :` puis une ligne `- [ ] …` par case |
| `1` | Section absente | `Section « Liste de contrôle » absente de la description de la PR.` |
| `1` | Section sans aucune case | `Section « Liste de contrôle » vide : aucune case à cocher trouvée.` |

## Tests : `tools/tests/test_check_pr_checklist.py`

Lancés par `just tools-test`. Classes : `CheckBodyTests` (section absente, vide, cochée, `[X]`, une décochée, CRLF, espaces, cases hors section, titre suivant, titre inexact, commentaires HTML), `CheckPullRequestTests` (dependabot), `MainTests` (variables d'environnement, `PR_BODY` absent) et `TemplateTests`, qui lit le vrai `.github/pull_request_template.md` : inchangé il doit échouer avec 7 cases décochées, toutes cochées il doit passer. `TemplateTests` est **ignoré** si le fichier n'existe pas.

## `just actionlint`

```
actionlint -config-file .github/actionlint.yaml
```

Vérifie tous les workflows de `.github/workflows/`. La recette est dans `just lint` (après `secrets-scan`, avant `tf-check`) et appelle `actionlint` du `PATH` (donc `mise exec -- just lint` si mise n'est pas activé dans le shell). [`.github/actionlint.yaml`](../../.github/actionlint.yaml) déclare le label de runner auto-hébergé `gpu` ; sans cette configuration, `gpu-eval.yml` produit l'alerte `label "gpu" is unknown` (vérifié le 2026-11-07). Les workflows actuels passent (y compris après l'épinglage par SHA de l'étape E9). La CI l'exécute aussi (étape « Workflows (actionlint) » de `ci-cpu`).

## Liens

- [`outillage.md`](outillage.md) : recette `lint`, tests des outils
- [`ci-cd.md`](ci-cd.md) : CI et validation locale
- [`docs/plans/PP.md`](../plans/PP.md) : étapes E8 et E9
