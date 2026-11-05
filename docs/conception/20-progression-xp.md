# 20 — Progression : XP et compétences

[← Sommaire](README.md)

## Principe [Décidé]

- Les survivants **débutent novices** : en combat, en recherche de ressources, en gestion du stress.
- **Chaque entité a une XP** qui augmente.
- **À chaque palier**, on débloque **un niveau dans une compétence**.

## Compétences des survivants

Les trois premières sont demandées ; les autres sont [Proposé].

| Compétence | Effets par niveau |
|---|---|
| **Tir** | Dispersion réduite, rechargement plus rapide, **meilleure discipline des lignes de tir** (moins de tirs amis) |
| **Corps à corps** | Moins de griffures et de morsures par échange, moins d'endurance consommée |
| **Recherche** | Fouille plus rapide, crochetage plus silencieux, chance de trouver davantage |
| **Sang-froid** | Gain de stress réduit, seuil de rupture relevé, effet tunnel retardé, meilleure compréhension radio sous stress |
| Endurance | Endurance maximale, récupération plus rapide |
| Soins | Inspection plus fiable, fenêtre de traitement d'une griffure allongée |
| Discrétion | Moins de bruit et d'odeur émis |
| Piratage | Durée de piratage réduite |
| Leadership | Poids au conseil, petit effet positif sur le moral du groupe |

Chaque compétence a 3 à 5 niveaux. Les effets sont des **modificateurs de paramètres** déjà existants dans la simulation : pas de nouvelle mécanique à coder par compétence.

## Gain d'XP

- **Sources** : zombies éliminés, fouilles réussies, objectifs atteints (antenne tenue, piratage), coéquipiers sauvés, temps de survie.
- **Apprendre de ses erreurs** : un peu d'XP aussi pour une griffure survécue ou une panique surmontée.
- **Rendements décroissants par type d'action**, pour éviter qu'un agent « farme » la même action.
- **Courbe de paliers croissante** (par exemple `100 × n^1,5`).

## Qui choisit la compétence débloquée

[Décidé] **Le LLM du survivant**, qui justifie son choix à la radio (« après ce qui s'est passé, je travaille mon sang-froid »). En mode commandant, le commandant peut recommander un choix, que le survivant suit selon sa confiance envers lui.

## Arc narratif

Les compétences montent pendant que le moral baisse ([18](18-moral.md)) : **les survivants deviennent meilleurs tout en s'usant**. Les premières minutes sont chaotiques (tirs amis, fouilles bruyantes, paniques), puis le groupe devient efficace, mais de plus en plus fragile psychologiquement. La mort d'un vétéran pèse d'autant plus lourd que les liens avec lui sont anciens.

Plan très partageable : « minute 2 contre minute 40 », le même groupe débutant puis vétéran.

## Zombies [Décidé]

- XP gagnée par les infections et les attaques réussies.
- **Les paliers débloquent de nouvelles options dans le schéma Laya** (tendre une embuscade, imiter un cri humain, contourner par une rue parallèle…), sans réentraînement.
- Les zombies vétérans sont rares et identifiables à l'écran.

## Zombie alpha [Décidé]

### Apparition

- **Spontanée : un alpha pour X zombies**, avec **au plus un alpha par quartier**.
- [Proposé] Quand le nombre de zombies d'un quartier sans alpha franchit le seuil, le zombie le plus expérimenté du quartier mute. L'XP désigne qui mute ; le ratio décide quand.
- [Décidé] Valeur de départ : un alpha pour 300 à 500 zombies, à régler en équilibrage. Avec 2 à 3 000 zombies et 5 quartiers, on atteint le plafond de 5 alphas en fin de partie.
- Si un alpha meurt, son quartier peut en voir apparaître un nouveau quand le ratio le permet à nouveau.

### Caractéristiques

- **Apparence supérieure** : silhouette plus grande, distincte, immédiatement reconnaissable ; overlay dédié.
- **Caractéristiques supérieures** : endurance, résistance.
- **Sens très développés** : rayon de perception visuelle étendu, ouïe plus fine (seuil de détection plus bas dans le champ acoustique), odorat plus fin (gradient d'odeur détecté de plus loin).
- **Rapide** : vitesse nettement supérieure à celle des autres zombies.

### Commandement

- **Il commande sa horde** : les zombies qu'il a ralliés le suivent (leader du steering de groupe) et ses décisions s'imposent à eux.
- **Schéma Laya enrichi** : plus d'options, horizon plus long (encercler un bâtiment, couper une retraite, attirer les survivants dans une impasse).
- **Cri de rassemblement** : événement sonore propagé par le FDTD, qui rallie les zombies sans alpha qui l'entendent.

### Ordres vocaux [Décidé]

L'alpha **crie pour donner des ordres** aux zombies de sa horde. C'est le pendant de la radio des survivants : **un ordre n'arrive qu'à ceux qui l'entendent**.

[Proposé] Fonctionnement :
- **Des ordres simples, puisque ce sont des cris** [Décidé] : quatre cris distincts, sans paramètre. **Rassemblement** (venir vers l'alpha), **charge** (attaquer la cible de l'alpha), **embuscade** (s'immobiliser et attendre), **repli** (s'éloigner de la menace). La direction n'est pas transmise : elle découle de la position de l'alpha ou de sa cible. Encercler reste une décision individuelle des zombies.
- **Propagation** : chaque cri est une source dans le solveur acoustique. Les bâtiments bloquent, les rues portent. Les zombies hors de portée ou derrière un îlot continuent en autonomie. Dans le prototype, un rayon simple suffit.
- **Obéissance** : un zombie de la horde qui entend l'ordre voit son jeu d'options réduit à l'ordre reçu (sauf s'il est déjà au contact d'un survivant).
- **Décision de l'alpha** : une seule question Laya, « quel cri ? » (aucun, rassemblement, charge, embuscade, repli). Un temps de recharge limite la fréquence.
- **Un coût** : crier révèle la position de l'alpha à tous ceux qui l'entendent, survivants compris.

**Côté survivants** :
- les cris s'entendent ; avec l'expérience, les survivants apprennent à les **reconnaître** (« c'est un cri d'encerclement, ils vont nous couper la route ») ;
- c'est une information de plus, transmise ensuite par radio, avec les risques de déformation habituels ;
- [Proposé] plus tard : imiter un cri pour leurrer une horde.

**Visuel** : chaque cri est une onde colorée selon le type d'ordre ; les zombies qui l'entendent réagissent visiblement, ceux qui ne l'entendent pas continuent leur route. On voit littéralement les ordres se propager dans les rues.

### Relations entre alphas

- **Égaux entre eux** : aucun alpha ne commande un autre alpha.
- **Ils peuvent coopérer**, mais **ne peuvent pas commander la horde d'un autre alpha**. Un alpha qui a besoin d'aide le signale ; l'autre alpha décide lui-même s'il engage sa propre horde, et comment.
- **L'intérêt de la ruche l'emporte toujours** : les alphas sont liés par un instinct commun. Quand l'intérêt de la ruche est en jeu, un alpha ne peut pas refuser d'y contribuer.

[Décidé] Les alphas ne partagent pas leurs perceptions : ils ne reçoivent qu'une **priorité de ruche résumée** (un instinct, pas une télépathie).

[Proposé] Mise en œuvre de l'intérêt de la ruche :
- **Ce n'est pas un esprit supplémentaire**, c'est un instinct : une couche `HiveSystem` agrège grossièrement ce que perçoivent les alphas (concentrations de survivants, bâtiments occupés, bruits majeurs) et en tire une **priorité de ruche**.
- La priorité de ruche est une entrée de chaque décision d'alpha.
- **Au-delà d'un seuil** (par exemple un groupe de survivants encerclé dans un bâtiment, ou un siège en cours autour d'une armoire de piratage), la contribution devient obligatoire : l'option « ignorer » disparaît du schéma Laya de l'alpha. Il garde le choix de la manière de contribuer.
- Les zombies sans alpha restent indépendants jusqu'à ce qu'un alpha les rallie.

### Côté survivants

- Apercevoir un alpha fait monter le stress.
- **L'éliminer désorganise sa horde** (les zombies retombent sur leurs comportements individuels) et donne un gain de moral nettement plus fort qu'un massacre ordinaire.
- Deux alphas qui coopèrent forment une super-horde : la menace la plus grave du jeu, que les caméras piratées permettent de voir venir.

### Visuel

- La mutation est un événement marquant du journal (« naissance d'un alpha »).
- [Proposé] Overlay « instinct de ruche » : liens lumineux entre les alphas quand ils coopèrent, plus intenses quand la ruche impose sa priorité.

## Spécialisations [Décidé : évolutif]

La liste des compétences pourra évoluer, et des **spécialisations** seront ajoutées plus tard. [Proposé] À un palier élevé, un survivant choisit une voie : tireur d'élite, médecin, éclaireur, technicien, meneur. Chaque voie donne un bonus durable et une capacité propre.

## Persistance entre épisodes [Reporté]

À décider plus tard. Option envisagée : les survivants qui terminent un épisode gardent leur XP et leurs compétences dans le suivant, pour une **série avec des personnages récurrents**.

## Technique

- **`core`** : `ProgressionSystem` (XP, paliers, modificateurs), déterministe et journalisé.
- **Prompts LLM** : les niveaux de compétence décrits en langage clair (« tu es un tireur novice »).
- **Laya** : les niveaux de compétence font partie de la perception du survivant ; le dataset de fine-tuning doit couvrir toute la gamme, de novice à vétéran.
- **Équilibrage headless** : vitesse de progression, impact de chaque niveau.
