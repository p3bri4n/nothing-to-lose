# 14 — Commandant humain

[← Sommaire](README.md)

## Principe [Décidé]

Un humain réel, à distance, commande le groupe par **ordres vocaux ou textuels**. Il voit ce que voient les survivants (bodycams) et entend leurs communications. **Il est soumis à la même physique que tout le monde.**

## Ordres vocaux

- **Push-to-talk** dans le navigateur.
- Même chaîne que la radio : DSP → SNR propre à chaque survivant → faster-whisper → `***`. Un ordre peut arriver déformé.
- **Position de l'antenne du QG** : zones d'ombre radio dans le centre.

## Ordres textuels

Messages de données : plus robustes, mais différés, perdus sous un seuil, lus seulement hors combat. Compromis voix (immédiate, fragile) / texte (fiable, différé).

## Réaction des survivants

- **Réponse immédiate par Laya** : classification de l'ordre dès la transcription, ajustement de posture, accusé (« reçu » / « répétez »). Le LLM élabore ensuite le plan.
- **Les ordres sont interprétés, pas exécutés** : confiance envers le commandant, peur, épuisement ou désaccord peuvent conduire à un refus, dit à la radio.
- Le commandant peut opposer un veto ou imposer une exclusion, et en porte le poids moral.

## Ce que voit le commandant

- **Bodycams** : rendu à hauteur d'yeux, 320×180 à 15 fps, shader « bodycam » (fisheye léger, bruit, horodatage, compression). Flux dégradé par le lien radio (pixellisation, gels, coupures). Déformées en cas de rupture du porteur.
- **Carte tactique** : positions GPS transmises (si le signal passe), observations des caméras qui s'estompent.
- **Flux CCTV** après piratage (voir [13](13-objectif-cameras.md)).
- **Indices de confiance** des survivants.
- Possibilité de **repérer une griffure** dans le champ d'une caméra, même cachée aux coéquipiers.

## Contraintes techniques

- **Temps réel obligatoire** : profil live allégé (4 à 6 héros, Piper, Whisper plus petit).
- Option : simulation à 0,7× en mode commandant pour laisser de la marge au LLM.
- **Client** : le viewer WASM alimenté par un flux d'état en direct, qui rend lui-même les bodycams (pas de flux vidéo).
- **Brouillard de guerre côté serveur** : le serveur n'envoie que ce que les caméras et les GPS ont capté.
- **Audio** : micro en Opus via WebRTC ou WebSocket vers le service `radio` ; retour des échanges radio dégradés.
- Les entrées du commandant sont des événements du journal : le replay et le rendu Voxtral restent possibles.

## Commandant local ou invités [Décidé : local d'abord]

Le commandant est d'abord joué en local. L'ouverture à des invités à distance viendra plus tard ; l'architecture la permet.

- Local : tout reste sur la machine.
- Invités à distance (streamers) : serveur exposé, authentification, brouillard de guerre appliqué strictement.
