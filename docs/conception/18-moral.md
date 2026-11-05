# 18 — Moral

[← Sommaire](README.md)

## Moral, stress, confiance : trois jauges distinctes

| Jauge | Échelle de temps | Nature |
|---|---|---|
| Stress ([11](11-stress-fatigue-rupture.md)) | Secondes à minutes | Réaction aiguë au danger |
| Confiance ([12](12-dynamique-sociale.md)) | Toute la partie | Réputation d'un survivant aux yeux du groupe |
| **Moral** | Toute la partie | Envie de continuer, espoir, cohésion |

Le moral fixe le **niveau de base** du stress et sa vitesse de récupération : un groupe démoralisé stresse plus vite et se calme plus lentement.

## Structure

- **Moral du groupe** `M_g` et **moral individuel** `M_i`.
- `M_i` est attiré vers `M_g` en proportion de la **cohésion** du groupe (moyenne des affinités et des confiances).
- Les traits individuels (résilience) modulent les variations.

## Érosion avec le temps [Décidé]

- **Le moral baisse de lui-même, et de plus en plus vite** à mesure que la partie dure (`dM/dt = −λ(t)`, avec `λ` croissant lentement).
- Conséquence voulue : **chaque partie a un arc naturel vers l'effondrement**. Les épisodes ont une fin, et le rythme narratif s'installe sans script.

## Événements négatifs [Décidé]

- **Mort d'un membre du groupe** : chute du moral de chaque survivant, **pondérée par son affinité avec le défunt**.
- [Décidé] Dans un **groupe uni** (cohésion élevée), chaque mort pèse plus lourd, parce que l'attachement est plus fort ; en contrepartie, il se remet plus vite après les événements positifs.
- Transformation d'un coéquipier, abandon, exclusion (culpabilité), dispute, objectif raté, faim prolongée.

## Événements positifs [Décidé]

- **Éliminer des zombies en masse** (par exemple 10 ou plus en peu de temps).
- **Trouver des ressources** (les médicaments comptent davantage).
- **Se reposer** dans un bâtiment de repos.
- Piratage réussi, réintégration d'un exclu, sauvetage d'un coéquipier.
- **Élimination d'un zombie alpha** : gain nettement plus fort que les autres événements positifs.

Apercevoir un alpha, à l'inverse, fait monter le stress.

Les gains sont **faibles et à rendement décroissant** : le cinquième massacre de la journée réconforte moins que le premier. La pente générale reste descendante.

## Effets

Le moral abaisse ou relève des seuils déjà définis ailleurs :
- probabilité de désobéissance et de panique ;
- probabilité de disputes et vitesse d'escalade ;
- seuil du point de rupture ;
- légère baisse de l'efficacité au combat et de la récupération de la fatigue ;
- ton des répliques LLM (le moral est décrit dans le prompt).

## Visualisation

- Jauge de moral du groupe dans l'overlay et dans l'interface du commandant.
- Courbe du moral sur la durée de l'épisode, utilisable dans les clips (« le moment où tout a basculé »).

## Système

`MoraleSystem` dans `core`, déterministe ; événements journalisés. Équilibrage headless pour régler `λ(t)` et l'amplitude des événements (durée de vie typique d'un groupe).
