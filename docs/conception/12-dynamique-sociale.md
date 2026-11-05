# 12 — Dynamique sociale

[← Sommaire](README.md)

## Vérité et croyances

- `InfectionSystem` et la simulation détiennent la vérité.
- Chaque survivant a un `BeliefStore` : ce qu'il a vu, ce qu'on lui a dit, ses soupçons, ses relations.
- Voir le pare-feu d'information dans [05](05-ia-survivants-llm.md).

## Relations

Matrice par survivant (confiance, affinité), qui évolue avec les événements : « il m'a sauvé la vie » (+), « il a abandonné un coéquipier » (−), « il m'a caché sa griffure » (−−). Confiance envers le commandant incluse.

## Indice de confiance du groupe [Décidé]

**Principe** : l'indice augmente avec le temps tant qu'aucune action n'est jugée négative par la majorité.

**Jugement** :
- chaque **témoin** juge l'action (positive / neutre / négative) via un schéma **Laya « jugement social »**, depuis son point de vue ;
- **majorité** parmi les membres vivants au courant ; égalité = neutre ;
- **bouche-à-oreille** : un témoin peut rapporter l'action (son LLM décide) ; le rapport est pondéré par l'indice du rapporteur.

**Dynamique** :
- perte rapide, reconstruction lente ;
- action négative majoritaire : chute proportionnelle à la gravité, et **remise à zéro de la période probatoire** ;
- remontée progressive vers un plafond ;
- bonus ponctuels pour les actes positifs majoritaires ;
- [Décidé] après une rupture : **plafond définitivement abaissé** (ex. 0,85).

**Effets** : poids du vote, crédibilité de la parole, rôles confiés (arme à feu, terminal, éclaireur, garde), fréquence des inspections. Affiché dans l'interface du commandant.

**Garde-fou** : le cercle vicieux (confiance basse → isolement → stress → rupture) doit avoir une sortie (réconciliation). L'équilibrage vérifie que la rédemption reste possible.

## Déduction sociale

- Symptômes ambigus, inspections imparfaites, griffures possiblement cachées.
- **Laya juge d'infection** : probabilité affichée au public pendant le débat, vérifiée quand la vérité éclate.
- Public : jeu de pronostics « qui est infecté ? ».

## Abandon et exclusion [Décidé]

| | Abandon | Exclusion |
|---|---|---|
| Situation | Camarade qui ne peut plus suivre | Camarade mobile jugé dangereux |
| Rythme | En combat, en quelques secondes | Au conseil |
| Décideur | Survivant à l'indice le plus élevé, ou le commandant | Vote du groupe |
| Jugement | Après coup, par la majorité (réputation du décideur) | Le vote lui-même |

**Procédure d'exclusion** :
1. Proposition (`proposer_exclusion`).
2. **Évaluation de menace par Laya** (donnée objective, pas un verdict).
3. Débat borné.
4. Vote pondéré par la confiance. [Décidé] : majorité qualifiée (2/3) pour un membre sain, simple pour un membre soupçonné d'infection.
5. Partage des ressources laissées à l'exclu.

**L'exclu** continue en agent autonome (son slot LLM est conservé) : il peut survivre, suivre, revenir, rejoindre une autre escouade, ou mourir seul. Le groupe peut changer de canal radio pour le couper.

**Réintégration [Décidé]** : un exclu peut être réintégré après une **bonne action pour le groupe**.
- L'action doit être jugée positive par la majorité (même mécanisme de jugement social par témoins).
- Si personne ne l'a vue, l'exclu peut la raconter lui-même, mais avec la crédibilité de son indice (très bas).
- Un jugement positif déclenche une proposition de réintégration, puis un vote au conseil.
- En cas de réintégration : indice de confiance de départ très bas, période probatoire, petit gain de moral pour le groupe.
- En cas de refus : hausse du stress de l'exclu ; il peut retenter plus tard.

**Scène émergente** : un blessé abandonné appelle son groupe ; plus le groupe s'éloigne, plus ses messages se dégradent en `***`, jusqu'au silence du squelch.

**Conséquences** : culpabilité (stress et moral, voir [18](18-moral.md)), fractures (perte de confiance des opposants, scission possible), **jugement rétroactif** si l'exclu soupçonné s'avère sain, veto ou imposition possible par le commandant.

## Systèmes

`RelationSystem`, `ReputationSystem`, `GroupSystem` (appartenance, scissions, fusions, partage des ressources) ; schémas Laya « jugement social » et « évaluation de menace » ; extension du conseil. Tout est journalisé.
