# Pixel

Toolchain per trasformare immagini "fake pixel art" in sprite puliti e, in una seconda fase, generare nuove pose tramite AI dentro un loop vincolato.

## Goal

Ridurre al minimo il passaggio:

1. generazione immagine AI "pixel style"
2. apertura in Aseprite
3. cleanup manuale
4. variazioni di pose a mano

L'idea del progetto e' usare un sistema ibrido:

- regole deterministiche per `grid`, `palette`, `cleanup`, `validation`
- AI solo dove serve davvero: proposta di nuove pose o varianti
- refinement automatico dopo ogni passaggio AI

## MVP

La prima versione non deve "fare pixel art da zero". Deve fare bene queste cose:

1. import di un'immagine fake pixel art
2. stima o definizione manuale della griglia
3. snap su grid
4. quantizzazione palette
5. cleanup di rumore e pixel isolati
6. export sprite pulito

Stato attuale del MVP:

- CLI installabile con comando `pixel`
- import/export PNG
- manual grid override
- auto grid euristico minimale
- alpha/background resolver con `--alpha-threshold` e `--transparent-color`
- auto background opt-in con `--auto-background`
- palette automatica o esplicita
- hard snap alla palette prima del downscale
- rasterizzazione indicizzata con majority voting
- cleanup conservativo
- validation report con metriche e warning

La seconda milestone aggiunge:

1. input di uno sprite base pulito
2. richiesta di nuova posa o direzione
3. generazione AI di una bozza
4. post-processing vincolato
5. scoring di coerenza col personaggio originale

## Architettura

Vedi [docs/architecture.md](/home/gabriele/Desktop/pixel/docs/architecture.md).

## Repo Layout

```text
docs/
  architecture.md
src/
  pixel/
tests/
```

## Setup

```bash
python -m pip install -e .
```

Dipendenze runtime esterne:

- `Pillow`
- `numpy`

La CLI usa `argparse`; i modelli dati usano `dataclasses`.

Per il cleanup assistito da modello vision:

```bash
python -m pip install -e ".[ai]"
export GEMINI_API_KEY="..."
```

L'extra `ai` installa il client Gemini. La pipeline base resta utilizzabile
senza questa dipendenza.

## Usage

Percorso consigliato per il MVP: specificare manualmente la dimensione della
cella sorgente.

```bash
pixel clean input.png output.png --cell-width 8 --cell-height 8 --colors 16
```

Esempio con colore di sfondo da rendere trasparente:

```bash
pixel clean input.png output.png \
  --cell-width 8 \
  --cell-height 8 \
  --colors 16 \
  --transparent-color "#ff00ff" \
  --transparent-tolerance 8 \
  --report report.json
```

Se `--cell-height` non viene passato, usa lo stesso valore di `--cell-width`.
La CLI stampa dimensione sorgente, griglia risultante, palette e warning.

`--transparent-color` usa match esatto di default. Su output AI con sfondo quasi
magenta, usa `--transparent-tolerance` per assorbire variazioni leggere prima
della quantizzazione palette.

Per rimuovere pixel visibili isolati solo quando il vicinato ha una maggioranza
chiara, usa il cleanup opt-in:

```bash
pixel clean input.png output.png \
  --cell-width 8 \
  --cell-height 8 \
  --colors 16 \
  --remove-isolated
```

Se non conosci il colore di sfondo, puoi stimarlo dai bordi dell'immagine:

```bash
pixel clean input.png output.png \
  --cell-width 8 \
  --cell-height 8 \
  --colors 16 \
  --auto-background \
  --transparent-tolerance 12 \
  --report report.json
```

`--auto-background` e' opt-in perche' puo' sbagliare se il soggetto tocca molto
i bordi dell'immagine.

Per chiedere a Gemini di indicare zone sospette su cui applicare cleanup locale:

```bash
pixel clean input.png output.png \
  --cell-width 8 \
  --colors 16 \
  --ai-cleanup gemini \
  --ai-advice-report advice.json \
  --report report.json
```

Questa modalita' non fa generare pixel finali al modello. Gemini guarda
immagine, output provvisorio e report, poi restituisce regioni in coordinate
griglia con azioni consentite. Il programma applica solo cleanup deterministico
su quelle regioni e salva cosa e' stato accettato o ignorato in `advice.json`.

Esiste anche un auto-grid euristico:

```bash
pixel clean input.png output.png --auto-grid --colors 16
```

Per ora il percorso affidabile resta il manual override.

## Cosa e' reale vs stub

Reale:

- pipeline Mode A end-to-end
- matrice interna indicizzata
- auto background da bordi immagine
- palette quantization con Pillow senza dithering
- palette snapping alla palette risolta
- majority voting su blocchi della griglia
- export PNG RGBA ricostruito da palette e indici
- report JSON opzionale
- cleanup mirato da advice Gemini opzionale

Ancora minimale:

- auto grid detection e' solo una euristica semplice
- cleanup dei pixel isolati e' opt-in e corregge solo casi non ambigui
- export `.aseprite` e PNG palettizzato sono rimandati
- l'integrazione AI non genera immagini: suggerisce solo regioni/azioni di cleanup

## Principi

- AI solo dentro vincoli forti
- output sempre esportabile come vera pixel art
- palette e grid come primitive di sistema, non come post-effect cosmetico
- tutto quello che e' ripetitivo deve essere automatizzabile
