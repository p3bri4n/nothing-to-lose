# 08 — Radio et communications

[← Sommaire](README.md)

## Propagation

Contrairement au son du jeu, **les ondes radio traversent les bâtiments** (avec atténuation). Modèle empirique :
- perte en distance, exposant urbain ~3 ;
- **perte par mur traversé** (modèle multi-wall de Motley-Keenan) : raycast sur le masque des bâtiments, ~10–15 dB par mur (brique épaisse) ;
- **fading** variable dans le temps (multi-trajets, passage derrière un îlot) ;
- **SNR** final par paire émetteur/récepteur.

Calcul négligeable, dans la crate `fields` (`RadioPropagation`).

## Comportements réels

- **Half-duplex** : on n'entend rien pendant qu'on émet.
- **Squelch** : sous le seuil, silence total.
- **Effet de capture FM** : en cas d'émissions simultanées, la plus forte couvre l'autre, ou les deux sont brouillées.
- **Le haut-parleur fait du bruit** : un message reçu est une source dans le solveur acoustique. Choix entre oreillette et volume coupé.
- Antenne du QG (mode commandant) : sa position crée des zones d'ombre.

## Chaîne audio

**TTS** → **DSP radio** (passe-bande 300–3 400 Hz, compression, saturation, bruit selon le SNR, coupures de fading, clics de seuil FM, souffle de fin de squelch) → **audio dégradé propre à chaque récepteur**.

## Comment le LLM « entend »

| Niveau | Fonctionnement | Usage |
|---|---|---|
| A. Texte seul | Canal à rafales (Gilbert-Elliott) piloté par le SNR → `***` | Parties d'équilibrage headless |
| **B. Audio → ASR → texte** | faster-whisper ; **mots à faible confiance → `***`** | **Base [Proposé]** |
| C. LLM audio natif | Voxtral Mini 3B écoute l'audio dégradé | Vitrine : un seul héros, clip comparatif |

Niveau B : les malentendus viennent de la physique (« Saint-Sernin » devient « cinq sur ** »). Garde-fous contre les hallucinations de Whisper sur du bruit : squelch, VAD, seuil sur `no_speech_prob`.

**Le stress augmente le seuil de confiance** : un survivant paniqué comprend moins bien, même avec un signal parfait (voir [11](11-stress-fatigue-rupture.md)).

Niveau C : ExLlamaV3 ne semble supporter que des modèles multimodaux image ; Voxtral Mini se sert via vLLM, dans une session dédiée.

## Choix des modèles (projet non monétisé)

| Usage | Modèle |
|---|---|
| Audio écouté par les personnages (partie jouée) | Piper, CPU, voix françaises |
| Voix des clips (rendu offline) | **Voxtral TTS** (CC BY-NC 4.0, autorisé en non commercial), avec prosodie selon le stress |
| ASR | faster-whisper (confiance par mot) |
| LLM audio (option) | Voxtral Mini 3B (Apache 2.0) |

Vigilance : la notion de « non commercial » a des zones grises (pas de sponsoring ni de promotion directe de prestations). Clonage de voix : uniquement des personnes consentantes.

## Messages de données (texte)

Canal distinct de la voix : messages courts, plus robustes, mais avec un délai, perdus sous un seuil de signal, **lus seulement hors combat**.

## Journal

On stocke **ce que chaque personnage a compris**, pas seulement le message émis. Au rendu, les sous-titres affichent la version comprise.

## Sources

- Voxtral (article) : https://huggingface.co/papers/2507.13264.md
- Voxtral en local : https://localaimaster.com/blog/voxtral-local-guide
- Voxtral TTS : https://insiderllm.com/guides/mistral-voxtral-tts-local-voice-ai/
- ExLlamaV3 : https://raw.githubusercontent.com/turboderp-org/exllamav3/master/README.md
