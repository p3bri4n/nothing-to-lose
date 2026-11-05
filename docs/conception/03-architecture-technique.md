# 03 — Architecture technique

[← Sommaire](README.md)

## Principes

1. **Séparer le mouvement de la décision** : le steering et les flow fields tournent à chaque tick ; l'IA choisit des intentions, sur événement.
2. **Une simulation déterministe et autoritaire**, tick fixe à 20 Hz, RNG seedé.
3. **Tout est journalisé** (event sourcing) : décisions IA, transcriptions radio, entrées du commandant, jets aléatoires.
4. **Un seul cœur Rust compilé en WASM**, exécuté dans Node et dans le navigateur. [Décidé]
5. **Pare-feu d'information** : la vérité de la simulation ne fuit jamais vers les prompts, ni vers le client du commandant.

## Organisation du dépôt

```
crates/
  core/      ECS, steering, flow fields, combat, infection, loot, stress, social
  fields/    FDTD acoustique, odeur + vent, propagation radio
  wasm/      bindings wasm-bindgen (Node + navigateur)
services/
  brain/     Python : broker, Laya, client TabbyAPI (LLM)
  radio/     Python : TTS, DSP radio, ASR (faster-whisper)
  recorder/  rendu offline des clips 9:16
web/
  viewer/    Three.js + Vite : replay interactif, overlays, audio, mode commandant
bake/        Python : pipeline carto
```

## Flux principal

```
Simulation (Rust/WASM, 20 Hz)
   ├─ perception → requêtes de décision → Broker (Python)
   │                                        ├─ Laya (zombies, réflexes, jugements)
   │                                        └─ LLM via TabbyAPI (survivants)
   ├─ messages radio → service radio (TTS → DSP → ASR → `***`)
   ├─ snapshots → viewer (Three.js)
   └─ journal → replay / rendu des clips
```

## Contrat de décision

Requête : `{agent_id, tick, brain, schema_id, state_text, deadline}`
Réponse : `{intent, probs, confidence, latency}`

Une réponse en retard est ignorée : la simulation applique un comportement de repli (utility AI). Tout est journalisé.

## Déterminisme (règles)

- WASM : sémantique flottante strictement définie. **Pas de `relaxed-simd`**, SIMD128 standard uniquement.
- Fonctions transcendantes via la crate `libm` (identiques en natif et en WASM).
- Ordre fixe pour les réductions parallèles ; découpage du multithread en bandes fixes.
- **Aucun calcul GPU n'influence le gameplay** : le GPU ne sert qu'au rendu.
- Les décisions IA, transcriptions et entrées humaines sont rejouées depuis le journal.
- **Keyframes de positions** toutes les quelques secondes pour recaler un replay qui dériverait.

## Navigateur

- Multithread WASM : `SharedArrayBuffer`, donc en-têtes COOP/COEP (Cloudflare Pages, décidé ; GitHub Pages ne le permet pas).
- Mode dégradé monothread : grille acoustique à 2 m (environ 8 fois moins coûteuse), utile aussi sur mobile.
- Zéro copie : Three.js lit directement les `Float32Array` exposés depuis la mémoire WASM.

## Effectifs de départ [Décidé]

~2 000 à 3 000 zombies, ~100 civils, 6 à 10 héros LLM en mode clips, 4 à 6 en live. Valeurs à corriger après les benchmarks.

## Matériel et VRAM

Machine : RTX 4070 Ti Super 16 Go + RTX 5060 Ti 16 Go (32 Go au total).

| Composant | VRAM approx. (à mesurer) |
|---|---|
| LLM Qwen3.6-27B en EXL3 + cache KV (~10 héros) | 18–22 Go |
| Laya (421M) | ~1 Go |
| faster-whisper (turbo, int8) | 1–2 Go, ou CPU |
| Voxtral TTS 4B | 8–10 Go ou plus |
| Voxtral Mini 3B (expérience « LLM qui écoute ») | ~7 Go |

**Tout ne tient pas en même temps. D'où le rendu en deux phases [Décidé] :**

1. **Partie jouée** : LLM + Laya + Whisper sur GPU, **Piper (CPU)** pour l'audio radio que les personnages écoutent.
2. **Rendu du clip, offline** : on décharge le LLM, on charge **Voxtral TTS** et on re-synthétise toutes les répliques du journal avec le même DSP et la même seed de bruit. Le déroulé ne change pas, puisqu'il vient du journal.

Le **mode live** (commandant humain) impose un profil allégé : 4 à 6 héros, Piper en live, Whisper plus petit, éventuellement un LLM plus petit.

## Déploiement

**CI/CD [Décidé]** : GitHub configuré par Terraform (état local hors dépôt), dépôt public dès le départ, CI sans GPU sur les runners GitHub, évaluation avec les modèles sur un runner GPU auto-hébergé (jamais déclenchée par une pull request), viewer de replays déployé sur Cloudflare Pages. Détails dans `docs/technique/ci-cd.md` et les décisions 0001 à 0004 du dépôt.


`docker compose` local : `sim`, `brain`, `tabbyapi`, `radio`, `client`, `chat-bridge`, `recorder`.
Diffusion live : rendu local + OBS ; aucun serveur public exposé, sauf pour un commandant invité (voir [14](14-commandant-humain.md)).
`laya-serve` ne s'expose jamais directement (aucune authentification par défaut sans `LAYA_API_KEY`).
