# 10 — Combat et infection

[← Sommaire](README.md)

## Le triangle de combat

| | Distance (arme à feu) | Corps à corps |
|---|---|---|
| Coût | 1 munition par tir | Endurance |
| Bruit | Très fort, propagé dans les rues | Faible |
| Exposition | Quasi nulle tant que la distance est tenue | Jet de contact à chaque échange |
| Limite | Précision qui baisse avec le stress, la fatigue et la distance | Catastrophique quand on est encerclé |

## Tir ami et lignes de tir [Décidé]

**Balistique** : chaque tir est un rayon tracé depuis le tireur, avec une dispersion qui dépend de la compétence **Tir**, du stress, de la fatigue et de la distance (tirage seedé). Le projectile touche **la première entité ou le premier mur** sur sa trajectoire, ami compris.

**Discipline de tir** :
- le réflexe Laya du survivant reçoit en entrée « allié dans le cône de tir » ;
- options : `tirer quand même`, `se repositionner`, `attendre`, `crier « baisse-toi »` ;
- un tireur novice ou très stressé (effet tunnel) vérifie mal sa ligne de tir ; la compétence **Tir** améliore cette discipline (voir [20](20-progression-xp.md)).

**Conséquences d'un tir ami** :
- blessure ou mort du coéquipier touché ;
- jugement des témoins (Laya « jugement social ») : un accident en situation critique est jugé moins sévèrement qu'une imprudence ;
- impact sur les relations, la confiance et le moral ([12](12-dynamique-sociale.md), [18](18-moral.md)).

À ne pas confondre avec le tir pendant un point de rupture, qui vient d'une perception corrompue ([11](11-stress-fatigue-rupture.md)).

**Visuel** : traçantes à l'écran ; ligne de tir affichable sur la carte du commandant.

## Contact au corps à corps

En intérieur, les goulets (portes, couloirs) limitent le nombre de zombies au contact : le corps à corps redevient viable. Voir [21](21-interieurs-sieges.md).

**Jet de contact** : à chaque échange, chaque zombie au contact a une chance de griffer, et une chance plus faible de mordre. Ces probabilités augmentent avec le nombre de zombies au contact et quand l'endurance baisse.

## Morsure [Décidé]

- **Transformation certaine.** Les médicaments n'y peuvent rien.
- **Durée d'incubation variable selon la santé** : `T = T_min + (T_max − T_min) × santé^γ` (santé = blessures, faim, endurance).
- La morsure est visible. Issues possibles pour le groupe : isoler, abandonner, sacrifice volontaire (le mordu couvre la retraite).
- Pas de scène d'exécution d'un coéquipier (modération des plateformes).
- À la transformation : bascule du LLM vers Laya ; dégradation progressive des répliques pendant l'incubation.

## Griffure [Décidé]

- **Probabilité d'infection** (ex. 30 %), **réduite par un médicament** (ex. 10 %). [Décidé] : à prendre dans une **fenêtre de temps juste après** la griffure.
- **Résultat caché** : tiré avec le RNG seedé au moment de la griffure, inconnu des personnages **et du public** [Décidé] (le public fait ses pronostics ; la vérité tombe à la transformation ou à la guérison).
- **Affaiblissement progressif** si infecté : endurance maximale, vitesse et précision en baisse, indices visuels (titube, tousse).
- **Symptômes ambigus** : la faim, la fatigue et les blessures produisent les mêmes. L'affaiblissement seul ne prouve rien.
- Le personnage ressent ses symptômes mais ne connaît pas la vérité.

## Inspection [Décidé]

- On peut demander à un personnage de **prouver qu'il n'est pas infecté** par inspection.
- Coût : ~10 s d'arrêt au contact, à découvert (dangereux en rue, sûr dans un bâtiment de repos).
- **Fiabilité croissante avec le temps** depuis la griffure ; petit taux de faux positifs (plaie enflammée). Une inspection précoce négative ne prouve pas grand-chose.
- Le refus est possible, et suspect.

## Témoins

Une griffure n'est connue que des agents qui avaient une ligne de vue, et de la victime. **Un survivant griffé hors de vue peut la cacher et mentir s'il est interrogé** [Décidé]. L'inspection et les bodycams peuvent le démasquer.

## Systèmes

- `CombatSystem` : portée, précision, jets de contact, événements sonores.
- `InfectionSystem` : `sain → griffé (tirage caché) → incubation → transformé`.
- **Équilibrage headless** : centaines de parties accélérées avec l'utility AI pour régler les probabilités et les stocks, en visant un taux de survie qui maintienne la tension.
