# Architecture

## Product Shape

Il software e' una pipeline a moduli. L'AI non scrive direttamente il file finale senza controllo: propone un output che passa sempre dentro moduli deterministici.

Pipeline completa:

```text
input image/reference
  -> ingest
  -> grid solver
  -> palette solver
  -> cleanup/refiner
  -> validator
  -> export

base sprite + pose request
  -> pose generator (AI)
  -> constrained rasterizer
  -> cleanup/refiner
  -> identity validator
  -> export
```

## Core Modules

### 1. Ingest

Responsabilita':

- caricare immagini PNG/WebP
- leggere alpha
- normalizzare dimensioni e background
- opzionalmente ritagliare margini inutili

Input:

- immagine sorgente
- metadata opzionali: `pixel_size`, `palette`, `sprite_bbox`

Output:

- raster normalizzato
- config di lavoro

### 2. Grid Solver

Responsabilita':

- stimare `pixel_size`
- costruire una mesh coerente
- permettere override manuale

Strategie:

- auto-detect stile `proper-pixel-art`
- fallback manuale con width/height fissi

Output:

- `GridSpec`
  - `cell_width`
  - `cell_height`
  - `rows`
  - `cols`
  - `origin_x`
  - `origin_y`

### 3. Palette Solver

Responsabilita':

- estrarre palette
- quantizzare a `N` colori
- forzare una palette esistente
- gestire trasparenza come canale speciale

Output:

- `PaletteSpec`
  - lista colori
  - indice trasparente opzionale
  - mappa indice->colore

### 4. Constrained Rasterizer

Responsabilita':

- convertire il raster in una matrice di celle
- assegnare un colore per cella
- garantire che il risultato finale sia solo `grid + palette`

Questo modulo e' il confine duro del sistema: nessun output esce senza passare da qui.

### 5. Cleanup / Refiner

Responsabilita':

- rimuovere pixel isolati
- correggere anti-aliasing sporco
- ridurre banding brutto
- sistemare cluster troppo rumorosi
- consolidare outline

Approccio consigliato:

- prima regole locali deterministiche
- poi eventuale pass AI solo su regioni problematiche

### 6. Validator

Responsabilita':

- misurare se lo sprite e' usabile
- produrre score e warning

Controlli minimi:

- numero colori effettivi
- pixel isolati
- cluster troppo piccoli
- rapporto silhouette/originale
- bounding box
- coerenza alpha

### 7. Pose Generator (AI)

Questo entra dalla milestone 2.

Input:

- sprite base pulito
- posa target
- direzione target
- eventuali attributi: arma, stato, frame index

Output desiderato:

- bozza della nuova posa

Non deve essere trusted output. Va sempre rimandato a:

1. `grid solver` o `grid reuse`
2. `palette enforcement`
3. `cleanup`
4. `identity validation`

### 8. Identity Validator

Serve per non perdere il personaggio originale dopo una nuova posa.

Controlli:

- silhouette similarity
- colori chiave presenti
- elementi distintivi ancora visibili
- proporzioni personaggio
- coerenza di equipaggiamento e dettagli

Se lo score scende sotto soglia:

- retry AI con prompt/conditioning piu' stretto
- oppure edit locale solo sulle regioni incoerenti

## Data Model

Il progetto dovrebbe ragionare su formati espliciti, non solo immagini.

### SpriteAsset

```json
{
  "id": "knight_base",
  "grid": {
    "cell_width": 1,
    "cell_height": 1,
    "rows": 64,
    "cols": 64
  },
  "palette": ["#00000000", "#1a1c2c", "#5d275d", "#b13e53"],
  "frames": [
    {
      "name": "idle_south_0",
      "pixels": "indexed-matrix"
    }
  ],
  "tags": {
    "character": "knight",
    "direction": "south",
    "action": "idle"
  }
}
```

Per internals conviene usare:

- matrice `H x W` di indici palette
- non RGB diretto

## Suggested Stack

Per partire veloce:

- `Python`
- `Pillow`
- `numpy`
- `opencv-python` per detection e morfologia
- `scikit-image` opzionale per metriche
- `pydantic` per config e asset metadata
- CLI con `typer`

Per la UI, piu' avanti:

- web app leggera `FastAPI + simple frontend`
- oppure desktop wrapper se serve

## Execution Modes

### Mode A: Cleanup

Use case:

- input AI fake pixel art
- output sprite pulito

Flow:

1. ingest
2. detect grid
3. quantize palette
4. rasterize indexed
5. cleanup
6. validate
7. export

### Mode B: Pose Transfer

Use case:

- input sprite base
- output nuova posa

Flow:

1. load base sprite asset
2. ask AI for target pose draft
3. snap su grid
4. enforce palette
5. cleanup
6. identity validate
7. export

### Mode C: Batch Production

Use case:

- generare piu' direzioni o animazioni da un personaggio base

Flow:

1. lista pose target
2. batch generate drafts
3. score ogni output
4. accetta solo sopra soglia
5. salva report errori per retry

## Suggested Milestones

### Milestone 1

Goal:

- fake pixel art -> true pixel art pulita

Deliverables:

- CLI
- import/export PNG
- grid detection
- palette quantization
- cleanup base
- validator base

### Milestone 2

Goal:

- nuova posa da sprite esistente

Deliverables:

- pose request format
- adapter per modello AI
- identity validator
- retry loop

### Milestone 3

Goal:

- batch generation di spritesheet

Deliverables:

- action presets
- direction presets
- report di quality scoring

## Technical Risks

- grid detection fragile su immagini troppo sporche
- quantizzazione che mangia dettagli chiave
- AI pose generation che rompe identita' del personaggio
- validator troppo debole per distinguere output "quasi giusto" da output usabile

## MVP Decision

La scelta giusta e':

- costruire prima `Mode A`
- progettare i dati gia' pensando a `Mode B`
- integrare AI solo quando il refiner deterministic gia' funziona bene

Se il cleanup non funziona bene, l'AI a monte peggiora solo il problema.
