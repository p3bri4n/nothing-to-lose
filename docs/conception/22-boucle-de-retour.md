# 22 — Boucle de retour (observabilité)

[← Sommaire](README.md)

## Pourquoi ce document

Le développement se fera en grande partie avec Claude dans Claude Code. Claude y **lit des fichiers, lance des commandes et regarde des images**. Pour savoir quoi corriger ou améliorer, le jeu doit produire ses retours sous ces trois formes, sans qu'un humain soit devant l'écran. Ces outils font partie du projet dès le premier jalon.

## 1. Exécution headless en une commande

```bash
just sim --seed 42 --minutes 10 --out runs/42/
```

Produit :
- `journal.jsonl` : événements et décisions, tick par tick ;
- `summary.json` : indicateurs de la partie ;
- `violations.txt` : anomalies détectées.

## 2. Reproductibilité

- Seed + journal = partie rejouable à l'identique (voir le déterminisme dans [03](03-architecture-technique.md)).
- **Chaque bug corrigé devient un test de non-régression** (seed, tick, agent, condition attendue), stocké dans `tests/regressions/`.

## 3. Invariants

Vérifiés en continu par la simulation, écrits dans `violations.txt` :
- agent dans un mur, dans un bâtiment plein, ou position `NaN` ;
- **agent bloqué** : aucun progrès depuis N secondes ;
- compte d'entités incohérent (zombie apparu sans infection, survivant disparu sans mort) ;
- décision IA hors délai ; JSON du LLM invalide ;
- fuite d'information : un champ de vérité présent dans un prompt (pare-feu, voir [05](05-ia-survivants-llm.md)).

## 4. Indicateurs et cibles

- `targets.toml` fixe des fourchettes attendues. Exemples : durée de survie médiane 15–40 min ; tirs amis < 5 % des tirs ; latence Laya p95 < 80 ms ; plan LLM < 5 s.
- `just eval --seeds 50` lance un lot de parties et produit `report.md`, comparé à la **référence** versionnée (`reports/baseline.json`).
- Indicateurs suivis : courbe d'infection, consommation de ressources, durée de survie, tirs amis, **temps sans événement** (mesure de l'ennui), nombre de moments forts, débit et latence des modèles, taux de repli sur l'IA simple.

## 5. Évaluation des IA

- **Laya** : jeu d'états de test annotés ; précision et calibration (ECE) après chaque fine-tuning ; comparaison avec l'IA simple.
- **Survivants LLM** :
  - taux de JSON valides ;
  - **cohérence parole / action** : la destination et l'intention correspondent à ce que le personnage annonce à la radio (vérifié automatiquement) ;
  - revue d'un échantillon de dialogues par Claude.

## 6. Captures d'écran automatisées

- Script Playwright : ouvre le viewer dans Chromium (GPU de la machine pour le WebGL), rejoue une partie, capture à des ticks et angles de caméra définis : `shots/seed42_t5320_capitole.png`.
- Claude lit ces images directement.
- Comparaison avec des images de référence pour détecter les régressions visuelles.

## 7. Inspection d'un agent

```bash
just inspect --seed 42 --tick 5320 --agent z123
```

Affiche l'état, la perception textuelle, les probabilités de Laya et l'historique des décisions. Répond à « pourquoi cet agent a-t-il fait ça ? ».

## 8. Retour humain

Ce que les outils ne mesurent pas : **est-ce amusant à regarder**, et une animation « sonne-t-elle juste ».
- Dans le viewer local, une touche pour **marquer un moment** : « bug », « bizarre », « génial », avec un commentaire.
- Enregistré dans `feedback/` : seed, tick, position de caméra, capture, commentaire (le serveur de développement local écrit le fichier).
- Claude lit `feedback/`, rejoue le moment exact et traite le retour.
- Rythme recommandé : de courtes sessions de visionnage annoté après chaque jalon.

## 9. Doublures des modèles et traçabilité

- **Doublures** (jalon P2) : `--brain=fake` (règles simples, instantané), `--brain=replay` (réponses enregistrées dans `tests/cassettes/`), `--brain=real` (Laya et LLM). La CI et le développement courant n'ont pas besoin des GPU ; seul `gpu-eval` utilise les vrais modèles.
- **Traçabilité** (jalons P0–P1) : chaque `summary.json` enregistre le commit, l'extrait OSM, le checkpoint Laya, le modèle LLM et le mode de cerveau. Une évaluation qui change d'un jour à l'autre doit pouvoir s'expliquer par une de ces versions.

## 10. Règle de travail (`CLAUDE.md`)

À la racine du dépôt, `CLAUDE.md` décrit les commandes et la routine :
1. modifier ;
2. `just check` : tests unitaires, tests de non-régression, invariants, mini-partie ;
3. `just eval` si la simulation ou les IA sont touchées ;
4. comparer avec la référence ;
5. ne valider que si rien ne régresse, ou si la régression est voulue et expliquée (mise à jour de la référence).

Chaque jalon a ses **critères d'acceptation sous forme de tests automatiques**.

## Limites

- Claude détecte les bugs, régressions et dérives de chiffres, et peut juger une image fixe.
- Il ne juge pas de façon fiable le plaisir de visionnage ni la fluidité d'une animation : c'est le rôle du retour humain (section 8).
