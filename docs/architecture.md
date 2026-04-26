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

Per il MVP il focus e' solo `Mode A`: trasformare una immagine "fake pixel art"
in un raster indicizzato coerente con una griglia e una palette. La parte AI non
entra ancora nel codice di produzione; resta una direzione futura per valutare o
proporre interventi, mai come sorgente trusted dell'output finale.

Pipeline MVP aggiornata:

```text
ingest RGBA
  -> alpha/background resolver
  -> grid spec manuale o detect
  -> palette solve/load
  -> hard color snap to palette
  -> constrained rasterizer con majority voting
  -> cleanup conservativo
  -> validation report
  -> export
```

Decisione importante: la pipeline deve fare palette snapping prima del downscale
su griglia. Il rasterizer lavora quindi preferibilmente su una matrice gia'
mappata a indici palette, non su RGB grezzo. Questo riduce artefatti e impedisce
al downscale di creare colori intermedi.

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

### 2. Alpha / Background Resolver

Responsabilita':

- preservare alpha nativo quando l'immagine lo contiene
- applicare `alpha_threshold` quando l'alpha e' presente ma sporco
- supportare chroma key manuale, per esempio `--transparent-color "#ff00ff"`
- in futuro stimare lo sfondo dai bordi con una euristica conservativa
- produrre o aggiornare il `transparent_index` nella palette

Questo passaggio deve avvenire prima della quantizzazione principale. Molti
output AI non hanno alpha pulito: spesso hanno un fondo bianco, verde, magenta o
quasi uniforme con artefatti. Se lo sfondo entra nella quantizzazione come colore
normale, inquina palette, rasterizer e cleanup.

Per il MVP sono sufficienti due modalita' esplicite:

- `alpha_threshold`: pixel con alpha sotto soglia diventano trasparenti
- `transparent_color`: pixel uguali al colore indicato diventano trasparenti
- `auto_background`: stima opt-in del colore di sfondo dai bordi immagine

L'auto-detection dello sfondo dai bordi deve restare conservativa e opt-in:
funziona bene su sprite centrati con sfondo uniforme o quasi uniforme, ma puo'
sbagliare se il soggetto tocca molto i bordi.

### 3. Grid Solver

Responsabilita':

- stimare `pixel_size`
- costruire una mesh coerente
- permettere override manuale

Nel progetto "grid" significa la griglia finale del raster indicizzato. In Mode
A, `rows` e `cols` sono quindi il numero di pixel/celle dell'output finale, non
necessariamente le dimensioni dell'immagine sorgente.

Esempio:

- input fake pixel art: `512x512`
- celle sorgente: `8x8`
- output finale: `64x64`
- `GridSpec.cell_width = 8`
- `GridSpec.cell_height = 8`
- `GridSpec.rows = 64`
- `GridSpec.cols = 64`
- ogni cella `8x8` dell'input diventa un singolo indice palette nell'output

Il rettangolo sorgente usato dalla griglia e':

- `x = origin_x`
- `y = origin_y`
- `width = cols * cell_width`
- `height = rows * cell_height`

Se `rows` e `cols` sono forniti manualmente, questo rettangolo deve rimanere
dentro l'immagine sorgente. Se non ci sta, il comando deve fallire o richiedere
una strategia esplicita di padding/crop.

Se `rows` e `cols` non sono forniti, il MVP puo' derivarli con:

- `cols = floor((image_width - origin_x) / cell_width)`
- `rows = floor((image_height - origin_y) / cell_height)`

In questo caso eventuali pixel residui su bordo destro/basso vengono ignorati
con un warning di validazione. Non bisogna fare stretch implicito: lo stretch
altera la griglia e introduce ambiguita'.

Strategie:

- manual override: `cell_width`, `cell_height`, opzionalmente `rows`, `cols`,
  `origin_x`, `origin_y`
- auto-detect euristico: stimare la dimensione della cella sorgente quando
  l'utente non la conosce

Per "grid detect" si intende stimare automaticamente la scala della fake pixel
art: capire, per esempio, che un'immagine `512x512` e' composta da blocchi
visivi `8x8`, quindi il raster finale dovrebbe essere `64x64`. Non significa
riconoscere tiles semantici, oggetti o animazioni. Nel MVP il manual override
deve essere il percorso affidabile; l'auto-detect puo' restare semplice e
fallibile.

Output:

- `GridSpec`
  - `cell_width`
  - `cell_height`
  - `rows`
  - `cols`
  - `origin_x`
  - `origin_y`

### 4. Palette Solver

Responsabilita':

- estrarre palette
- quantizzare a `N` colori
- forzare una palette esistente
- gestire trasparenza come canale speciale
- mappare ogni colore sorgente al colore palette piu' vicino

Il solver deve supportare entrambe le modalita':

- palette automatica: estrazione/quantizzazione a `N` colori
- palette esplicita: lista di colori fornita dall'utente o da file

La trasparenza non deve essere trattata come un colore RGB qualunque. Va
preservata come canale speciale, con `transparent_index` opzionale. L'ordine
della palette deve essere stabile per rendere ripetibili asset, report e futuri
passaggi di Mode B.

La distanza colore deve stare dietro una funzione piccola, per esempio
`nearest_palette_color` o equivalente vettoriale. Nel MVP puo' partire semplice,
ma l'interfaccia deve permettere di sostituire la distanza RGB con una distanza
percettiva come CIELAB/OKLAB senza cambiare il resto della pipeline.

Dithering: default `none`. Il dithering automatico tende a introdurre rumore
che sembra sporco nella pixel art. In futuro puo' esistere una opzione esplicita
come `none|bayer`, ma il MVP deve evitare dithering implicito.

Output:

- `PaletteSpec`
  - lista colori
  - indice trasparente opzionale
  - mappa indice->colore

### 5. Constrained Rasterizer

Responsabilita':

- convertire il raster in una matrice di celle
- assegnare un colore per cella
- garantire che il risultato finale sia solo `grid + palette`

Questo modulo e' il confine duro del sistema: nessun output esce senza passare da qui.

La rappresentazione interna dopo questo step deve essere una matrice `rows x
cols` di indici palette. Cleanup, validation ed export devono preferire questa
matrice indicizzata rispetto a RGB diretto.

Il downscale da cella sorgente a pixel finale deve usare majority voting sugli
indici palette:

```text
blocco sorgente cell_height x cell_width
  -> conta gli indici palette presenti
  -> scegli l'indice piu' frequente
  -> scrivi un solo indice nella matrice output
```

Questo e' piu' adatto della media RGB o del nearest-neighbor puro per fake pixel
art, perche' assorbe anti-aliasing e variazioni leggere dentro il blocco. In
caso di pareggio, la scelta deve essere deterministica. La trasparenza va
trattata come un indice normale, ma il validator deve segnalare celle con mix
ambiguo tra trasparenza e colore.

Nel MVP l'export PNG puo' essere un PNG RGBA ricostruito dalla matrice
indicizzata e dalla palette. Un PNG realmente palettizzato puo' arrivare dopo:
e' utile, ma non deve bloccare la pipeline iniziale.

### 6. Cleanup / Refiner

Responsabilita':

- rimuovere pixel isolati
- correggere anti-aliasing sporco
- ridurre banding brutto
- sistemare cluster troppo rumorosi
- consolidare outline

Approccio consigliato:

- stile micro-funzionale: funzioni piccole, pure quando possibile, applicate
  alla matrice indicizzata
- prima regole locali deterministiche
- poi, in una milestone futura, eventuale giudizio LLM/AI sui risultati
  intermedi o sulle regioni problematiche

Per il MVP il cleanup deve restare conservativo. Regole iniziali sensate:

- segnalare pixel isolati senza cancellarli di default
- rimuovere pixel isolati solo in modalita' opt-in e con maggioranza locale
  chiara
- applicare/enforzare la palette
- normalizzare alpha/trasparenza

La parte difficile e' decidere quando una correzione migliora davvero lo sprite.
Questa decisione non va codificata troppo presto con euristiche aggressive:
meglio produrre report e rendere i passaggi osservabili, cosi' in futuro un LLM
puo' giudicare output intermedi senza sostituire il rasterizer deterministico.

Un pixel isolato puo' essere rumore, ma anche un occhio, un bottone o un
highlight. Le correzioni automatiche devono quindi restare opt-in e non devono
toccare casi ambigui; piu' avanti potranno considerare contrasto e luminosita'
rispetto ai vicini.

### 7. Validator

Responsabilita':

- misurare se lo sprite e' usabile
- produrre score e warning

Il validator non deve essere solo booleano. Deve produrre un report leggibile,
con metriche e warning. Anche quando l'export riesce, il report deve dire se
l'output e' sospetto.

Controlli minimi:

- numero colori effettivi
- pixel isolati
- cluster troppo piccoli
- rapporto silhouette/originale
- bounding box
- coerenza alpha

### 8. Pose Generator (AI)

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

### 9. Identity Validator

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

Per il MVP `SpriteAsset` deve restare minimale. La forma utile e':

- `grid`: `GridSpec`
- `palette`: `PaletteSpec`
- `pixels`: matrice indicizzata
- `metadata`/`tags`: opzionali, pensati per compatibilita' futura con pose,
  direzione, azione e frame

Non serve ancora modellare tutto il sistema di pose generation. Basta non
bloccare la strada: i dati devono poter descrivere frame e tag in modo esplicito.

## Suggested Stack

Stack MVP minimo:

- `Python`
- `Pillow`
- `numpy`
- `argparse` dalla standard library per la CLI
- `dataclasses` dalla standard library per i modelli dati
- `json` dalla standard library per serializzazione/report

Dipendenze esterne MVP:

- `Pillow`: necessaria per leggere/scrivere PNG/WebP e gestire RGBA
- `numpy`: necessaria per snapping colore, majority voting e analisi su matrici

Dipendenze da evitare nella Milestone 1:

- `opencv-python`: troppo pesante per il core; da aggiungere solo se una futura
  grid detection lo richiede davvero
- `scipy`: utile per morfologia, ma non necessaria per il primo cleanup
- `scikit-image`: rimandata a metriche piu' avanzate
- `pydantic`: non necessario per modelli interni semplici; `dataclasses` basta
- `typer`/`click`: non necessari per una CLI iniziale; `argparse` basta

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
2. resolve alpha/background
3. detect grid oppure manual override
4. solve/load palette
5. hard snap colori alla palette
6. rasterize indexed con majority voting
7. cleanup conservativo
8. validate
9. export

MVP Mode A deve essere installabile e usabile da CLI. Percorso affidabile:

```text
pixel clean input.png output.png --cell-width 8 --cell-height 8 --colors 16
```

Percorso con detection:

```text
pixel clean input.png output.png --auto-grid --colors 16
```

La detection non deve essere requisito per avere una pipeline funzionante.

Il comando iniziale puo' usare `argparse`; non serve introdurre un framework CLI
finche' la superficie resta piccola.

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
- sfondo AI non trasparente che entra nella palette e rovina lo sprite
- AI pose generation che rompe identita' del personaggio
- validator troppo debole per distinguere output "quasi giusto" da output usabile
- cleanup troppo aggressivo che elimina dettagli validi, soprattutto su sprite
  piccoli
- export apparentemente corretto ma non riproducibile per palette non stabile
- dithering involontario che trasforma gradienti in rumore visivo

## MVP Decision

La scelta giusta e':

- costruire prima `Mode A`
- progettare i dati gia' pensando a `Mode B`
- integrare AI solo quando il refiner deterministic gia' funziona bene
- mantenere il codice micro-funzionale: funzioni piccole, moduli chiari, niente
  framework astratto di pipeline finche' non serve

Se il cleanup non funziona bene, l'AI a monte peggiora solo il problema.

Decisioni MVP attuali:

- `rows` e `cols` rappresentano la griglia finale/output indicizzato
- manual override della griglia e' supportato fin da subito
- auto grid detection e' utile ma non obbligatoria
- palette automatica e palette esplicita devono essere entrambe previste
- background/alpha resolver e' uno step esplicito
- auto-background da bordi immagine e' disponibile come opzione opt-in
- palette snapping avviene prima del downscale su griglia
- constrained rasterizer usa majority voting sugli indici palette
- dithering default `none`
- cleanup conservativo, osservabile tramite validation report
- output iniziale PNG RGBA ricostruito da palette e indici; PNG palettizzato
  rimandabile
- export `.aseprite` e' target prioritario post-MVP per integrarsi bene con il
  workflow reale di rifinitura manuale
- stack MVP esterno limitato a `Pillow` e `numpy`; CLI e modelli dati usano
  standard library
