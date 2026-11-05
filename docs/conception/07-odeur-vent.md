# 07 — Odeur et vent

[← Sommaire](README.md)

## Exigence [Décidé]

L'odeur **ne traverse pas les bâtiments**.

## Champ d'odeur

| Paramètre | Valeur |
|---|---|
| Résolution | 2 m (l'odeur diffuse lentement) |
| Mise à jour | 5 Hz |
| Modèle | Advection semi-lagrangienne par le vent + diffusion + décroissance |
| Bâtiments | Flux nul aux murs |
| Implémentation | Crate `fields`, worker dédié |

## Émetteurs

- **Survivants** : trace de base, plus forte s'ils saignent ou transportent de la nourriture.
- **Zombies** : odeur de putréfaction, perceptible par les survivants (alerte).
- Option : la pluie efface les traces.

## Vent canalisé par les rues

Un vent global uniforme traverserait les bâtiments. À la place :
- **précalcul au bake** d'un écoulement potentiel 2D avec les bâtiments comme obstacles (quelques centaines d'itérations de Jacobi), pour 8 à 16 directions ;
- en jeu, interpolation entre les deux directions les plus proches.

Le vent accélère dans les rues alignées, contourne les îlots et reste calme dans les cours.

## Vent d'autan

Épisodes de vent de sud-est : l'odeur porte loin sous le vent, le long des axes orientés sud-est. Les survivants doivent approcher un objectif **contre le vent**. Une touche locale que tous les Toulousains reconnaîtront.

## Perception

Intensité et direction du gradient, quantifiées pour Laya (`odeur: humain blessé, NE, moyenne`).

## Transmission au client

Champ à 4 m, 5 Hz, rendu en brume qui dérive.
