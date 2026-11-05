# 21 — Intérieurs et sièges

[← Sommaire](README.md)

## Ce qui change [Décidé]

- **Un alpha peut forcer l'entrée d'un bâtiment stratégique** : planque (repos), ressources, informations.
- Il faut donc **gérer le combat en intérieur**.
- Les survivants peuvent **renforcer le bâtiment**, au prix d'effort physique et de temps.
- Pendant une attaque, il faut renforcer pour éviter l'invasion.
- **Sortie de secours parfois présente, parfois non** : plus un bâtiment est stratégique, moins il a d'issues.

Les zombies ordinaires, sans alpha, continuent seulement d'attendre dehors.

## Quels intérieurs sont modélisés

- **Seuls les bâtiments stratégiques** (ceux tirés au hasard par quartier, voir [19](19-quartiers-batiments.md)) ont un intérieur. Les autres bâtiments restent des volumes pleins.
- **Un seul niveau** : la simulation reste en 2D.
- **Génération procédurale** à partir de l'emprise du bâtiment (subdivision BSP) : 3 à 8 pièces, couloirs, portes intérieures, parfois une cour intérieure. Plan tiré avec la seed de la partie, donc différent à chaque partie.
- Grille de navigation locale, raccordée à la grille de la ville par les portes.

## Issues et valeur stratégique

| Niveau stratégique | Issues | Exemple |
|---|---|---|
| Faible | Entrée + 1 ou 2 sorties de secours | Bâtiment de vivres ordinaire |
| Moyen | Entrée + 1 sortie de secours | Planque standard |
| Élevé | **Entrée unique** | Bâtiment de munitions ou de soins important |

C'est le dilemme central : les meilleurs bâtiments sont aussi des pièges potentiels. [Décidé] Une sortie de secours est **inconnue tant qu'on n'a pas exploré l'intérieur**.

## Renforcement

- Chaque ouverture (porte, fenêtre) a une **intégrité**.
- **Renforcer** : action longue qui consomme de l'endurance, augmente la fatigue et utilise des **matériaux** (mobilier, planches). [Décidé] **Stock de matériaux limité par bâtiment, mais on peut en apporter**, notamment depuis les **bâtiments « matériaux »** (transport : charge, lenteur, exposition).
- **Renforcer fait du bruit** (coups de marteau, meubles déplacés) : événements sonores qui fuient par les ouvertures. Se barricader peut attirer l'attention.
- La compétence **Endurance** accélère le renforcement ; [Proposé] une future spécialisation « technicien » pourrait le rendre plus efficace.

## L'assaut

- **Seule une horde menée par un alpha peut forcer une entrée.** L'alpha choisit le point d'attaque ; les zombies de sa horde ajoutent leur poussée.
- L'intégrité baisse en fonction du nombre d'attaquants au contact de l'ouverture.
- **Course entre deux vitesses** : dégâts de la horde contre vitesse de renforcement des survivants. Chaque survivant affecté au renforcement ne tire pas.
- **Ruses de l'alpha** (options Laya) : attaquer l'ouverture la plus faible, feinter sur une porte pour attirer les défenseurs puis frapper ailleurs, attendre que les survivants s'épuisent.
- La priorité de ruche peut amener un autre alpha à envoyer sa horde (voir [20](20-progression-xp.md)).

## Défense en intérieur

- **Les goulets changent le combat.** Dans un couloir ou une porte, peu de zombies sont au contact en même temps : le corps à corps redevient viable, alors qu'il est mortel quand on est encerclé dehors.
- **Positions de tir** à travers les fenêtres et les brèches.
- **Tir ami plus probable** : espaces étroits, coéquipiers proches dans les lignes de tir.
- **Repli pièce par pièce** : chaque porte intérieure peut aussi être renforcée. On obtient une défense en couches.
- **Évacuation** par la sortie de secours, si elle existe, avant d'être submergés. Les zombies qui attendent à la sortie (voir [19](19-quartiers-batiments.md)) peuvent aussi la couvrir.

## Décisions des IA

- **LLM (stratégie)** : tenir ou évacuer tôt, répartition des rôles (renfort, tir, garde de la sortie de secours), sacrifice éventuel pour couvrir une évacuation.
- **Laya, survivant (réflexes)** : `renforcer`, `tenir la brèche`, `tirer par la fenêtre`, `se replier dans la pièce suivante`, `fuir par la sortie de secours`.
- **Laya, alpha** : choix du point d'assaut, feinte, encerclement des issues, attente.

## Son, odeur et visibilité

- L'intérieur des bâtiments stratégiques est ouvert dans les grilles acoustique et olfactive, avec les murs intérieurs comme réflecteurs. **Un tir à l'intérieur résonne**, et le son fuit par les ouvertures et les brèches.
- L'odeur des survivants s'accumule à l'intérieur et fuit par les ouvertures.
- La vision passe par les portes ouvertes, les fenêtres et les brèches.

## Rendu

- **Coupe du toit** quand le focus est sur un bâtiment stratégique occupé (même technique que pour les rues étroites) : on voit l'intérieur en plan.
- Murs intérieurs extrudés bas, état des barricades visible, brèches.
- Bodycams à l'intérieur pour le commandant.

## Technique

- **Bake** : liste des bâtiments éligibles et emprises.
- **`core`** :
  - `InteriorGen` : génération BSP des pièces, portes et issues selon le niveau stratégique ;
  - `FortificationSystem` : intégrité des ouvertures, matériaux, renforcement, dégâts ;
  - navigation intérieure raccordée à la ville.
- **`fields`** : ouverture des cellules intérieures dans les masques son et odeur.

## Périmètre

[Décidé] **Intérieurs et sièges font partie du MVP** (jalon J4c). C'est l'ajout le plus coûteux (génération d'intérieurs, navigation, rendu en coupe) : il allonge le délai avant le premier épisode jouable, mais les jalons J0 à J2 restent publiables entre-temps. Les sièges supposent les alphas : J4b fait donc aussi partie du MVP.
