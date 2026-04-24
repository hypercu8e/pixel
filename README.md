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
```

## Principi

- AI solo dentro vincoli forti
- output sempre esportabile come vera pixel art
- palette e grid come primitive di sistema, non come post-effect cosmetico
- tutto quello che e' ripetitivo deve essere automatizzabile
