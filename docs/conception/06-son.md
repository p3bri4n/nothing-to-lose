# 06 — Son

[← Sommaire](README.md)

## Exigences [Décidé]

- Le son **ne traverse pas les bâtiments**.
- Le son se comporte comme **une onde** : réflexions, diffraction, réverbération.

## Solveur

**FDTD 2D** (différences finies dans le domaine temporel) sur une grille décalée : pression `p`, vitesse particulaire `(vx, vy)`.

| Paramètre | Valeur |
|---|---|
| Résolution | **1 m** (certaines ruelles font 3 à 4 m de large) |
| Taille | ~1 500 × 1 500 cellules, ~2,25 M cellules, ~27 Mo en float32 |
| Bâtiments | Murs réfléchissants partiellement absorbants (coefficient par matériau) ; **intérieur ouvert pour les bâtiments stratégiques**, murs intérieurs réfléchissants, fuites par les ouvertures et les brèches ([21](21-interieurs-sieges.md)) |
| Arbres | Légère atténuation |
| Garonne | Transparente au son |
| Bords | Zone absorbante (évite les retours depuis le bord du monde) |
| Implémentation | Crate `fields`, Rust, multithread + SIMD128, compilée en WASM |

Avantage décisif : **la superposition de toutes les sources est gratuite**. Le coût est le même pour 1 ou 50 tirs simultanés.

## Vitesse du son [Décidé : ralentie]

| | Réelle (343 m/s) | Stylisée (~50 m/s) |
|---|---|---|
| Pas de temps (CFL, 1 m) | ~2 ms → ~480 pas/s | ~14 ms → ~70 pas/s |
| Charge | ~1 G mises à jour/s | ~160 M/s |
| Visuel | Invisible (4 s pour traverser le centre) | **Front d'onde visible qui ricoche** |

Choix retenu : vitesse ralentie (~50 m/s). Limite assumée : la grille ne résout que des longueurs d'onde d'une dizaine de mètres minimum, donc la diffraction est plus forte que dans la réalité. C'est une approximation perceptive, pas une simulation acoustique de référence.

## Sources sonores

Injectées dans le champ sous forme d'impulsions (forme d'ondelette, amplitude selon le type) : tir, rideau forcé, alarme d'armoire, course, cri, radio (haut-parleur), grognements de la horde (source continue de faible niveau), leurres, **cris d'alpha** (ordres vocaux à la horde, voir [20](20-progression-xp.md)).

## Perception

- **Niveau** : enveloppe RMS lissée dans la cellule de l'agent.
- **Direction** : **vecteur d'intensité `I = p·v`**, moyenné sur ~0,5 s.
- **Nature** : deux champs séparés au départ (tirs/impacts ; voix/grognements), ou classification de l'enveloppe (impulsif / continu).

## Comportements émergents

- Le son suit les rues : un tir rue du Taur réveille la rue, la rue parallèle n'entend presque rien.
- **Les échos trompent les agents** : dans une rue étroite, le vecteur d'intensité peut pointer vers une façade.
- **Leurres** : pétards ou bouteilles lancés pour attirer une horde dans une impasse.

## Transmission au client

Champ d'énergie sous-échantillonné (4 m, 8 bits, 10–15 Hz), rendu en ondes par shader.
