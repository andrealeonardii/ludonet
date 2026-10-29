# Rete Forza 4 — prima versione

Policy locale `84 → 128 → 64 → 7`, con ReLU nei due strati intermedi e
**19.591 parametri**. I pesi sono in `pesi.txt`, formato testuale leggibile dal
modulo C++. Non è un LLM e non richiede accesso alla rete o al proxy.

## Come è stata allenata

- 750.000 posizioni generate da partite simulate, seed 42.
- Insegnante offline: negamax con alpha-beta, profondità quattro semimosse;
  etichette esatte per vittorie e blocchi immediati. Non è un solver perfetto.
- 362.248 posizioni distinte per il training, raddoppiate con riflessione.
- 39.948 posizioni di validazione, senza sovrapposizioni o specchi nel training.
- 160 epoche; esportato il checkpoint dell'epoca 155, scelto sulla validazione.
- Nessun dato degli utenti. Addestramento da pesi casuali, nessun modello preallenato.

Codice e comandi riproducibili: [allenamento](../../allenamento/README.md).
Versioni, seed e hash del dataset: [allenamento.json](allenamento.json).

## Valutazione indipendente

Dopo aver fissato i pesi sono state generate altre 30.000 posizioni con seed
2026. Eliminati duplicati e sovrapposizioni con tutti i dati precedenti, anche
riflessi, ne restano **14.804**.

| Misura | Risultato |
|---|---:|
| Vittorie immediate colte (2.347 posizioni) | 96,34% |
| Minacce immediate bloccate (2.326 posizioni) | 95,61% |
| Accordo con una scelta dell'insegnante | 71,62% |
| Contro mosse casuali, colori alternati | 199 vittorie / 200 |
| Contro avversario tattico elementare, colori alternati | 190 vittorie / 200 |

L'avversario tattico cerca una vittoria, poi un blocco immediato, altrimenti gioca
a caso. Non è un solver né un avversario esperto. Sono confronti riproducibili
con seed fisso, non garanzie di risultato contro persone. I dettagli e l'hash
dei pesi valutati sono in [valutazione.json](valutazione.json).

La scelta durante il gioco appartiene interamente alla rete. Il solo filtro
esterno esclude le colonne piene. Non c'è ricerca o correzione tattica dopo
l'inferenza: la rete può ancora perdere e sbagliare anche mosse semplici.

## Formato dei pesi

Prima riga: `NICKGAME_FORZA4_V1`. Per ciascuno dei tre strati seguono:
numero di ingressi e uscite, pesi ordinati per neurone d'uscita, poi bias.
La griglia è ordinata dall'alto verso il basso e da sinistra a destra.
Primi 42 ingressi: pedine proprie; successivi 42: pedine avversarie.
Le sette uscite corrispondono alle colonne 0–6. Il file viene controllato prima
di usarlo; se è assente o non valido il turno fallisce, senza mosse di riserva.
