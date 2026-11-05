# 15 — Rendu et viewer

[← Sommaire](README.md)

## Moteur

[Décidé] **Three.js** (davantage de ressources sur les vertex animation textures) ; Babylon.js reste une alternative.

## Style

Diorama low-poly, toits plats, palette brique rose toulousaine. Lisible en vidéo verticale et peu coûteux.

## Agents

Meshes instanciés animés par **vertex animation textures** : des milliers de zombies animés en un seul draw call.

## Caméra et occlusions

- **Arbres et arches** : découpe en **dithering pilotée par la présence des agents**. La simulation écrit une texture de densité d'agents ; le shader des occludeurs devient transparent là où des agents passent dessous. Pas de tri de transparence, coût quasi nul. Passe de silhouette en secours.
- **Bâtiments** : dans les rues étroites, les façades masquent l'action.
  - caméra presque verticale (75–85°) ;
  - **coupe des toits** autour du point d'intérêt (bâtiments proches tronqués à 3–4 m).
- **Intérieurs des bâtiments stratégiques** : toit coupé quand le focus est dessus, murs intérieurs bas, barricades et brèches visibles ([21](21-interieurs-sieges.md)).

## Overlays

- Probabilités Laya au-dessus des agents (pour les agents sélectionnés).
- Jauges de stress, fatigue, confiance des héros.
- Calques **son** (ondes qui parcourent les rues) et **odeur** (brume qui dérive).
- Sous-titres radio : **version comprise** par chaque personnage.
- Probabilité d'infection estimée par Laya (juge).
- Alphas : silhouette distincte, liens « instinct de ruche » entre alphas qui coopèrent.

## Vues spéciales

- **Bodycams** et **flux CCTV** : rendus secondaires basse résolution, à la demande.

## Viewer public (navigateur)

- **Replay interactif** : le cœur WASM re-simule la partie depuis le journal.
- Orbite libre, suivi d'un héros, calques, inspection des agents, audio radio pré-rendu (Voxtral).
- Hébergement statique sur Cloudflare Pages avec en-têtes COOP/COEP, mode dégradé monothread.

## Clips

- Rendu offline dans un Chromium headless, en 9:16, caméra scénarisée.
- **Détection automatique des moments forts** à partir du journal : pics d'infection, mort d'un héros, chute d'une barricade, rupture, exclusion, piratage réussi.
- Crédits : © OpenStreetMap contributors, IGN.
