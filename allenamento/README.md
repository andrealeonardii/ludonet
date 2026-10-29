# Allenamento di NickBot

Il gioco usa soltanto i pesi in `modelli/forza4/pesi.txt` e la libreria standard
C++17. Questa cartella serve a ricreare quei pesi: non viene eseguita da Flask.

## Preparazione

Dalla cartella principale di Nickgame, con Python 3.10 o successivo e g++:

```bash
python3 -m venv allenamento/.venv
allenamento/.venv/bin/pip install -r allenamento/requirements.txt
allenamento/.venv/bin/python allenamento/allena.py
allenamento/.venv/bin/python allenamento/valuta.py
```

L'allenamento usa la CPU con quattro thread e il seed 42. Non richiede GPU o
servizi esterni. Le versioni effettivamente utilizzate sono riportate in
`modelli/forza4/allenamento.json`. I risultati possono variare fra versioni delle
librerie o hardware. `run.sh` non allena la rete a ogni avvio.

Per sperimentare senza sostituire il modello distribuito:

```bash
allenamento/.venv/bin/python allenamento/allena.py --output allenamento/build/candidato
allenamento/.venv/bin/python allenamento/valuta.py --modello allenamento/build/candidato/pesi.txt
```

## Dati e insegnante

`insegnante.cpp` produce posizioni raggiungibili tramite partite: alterna mosse
casuali e mosse scelte con ricerca negamax e potatura alpha-beta, limitata a quattro
semimosse. Non è un solver perfetto. Valuta allineamenti e controllo del centro;
termina la partita appena qualcuno vince. Riconosce esattamente vittorie immediate
e mosse che rimuovono tutte le minacce immediate dell'avversario.

Il file contiene una griglia, sette punteggi e due maschere per vittorie/parate.
Il giocatore di turno è sempre rappresentato da 1, l'avversario da 2. Le mosse
equivalenti hanno tutte valore come esempi corretti. Python elimina duplicati e
riflessi, separa training e validazione tramite hash stabile, poi aggiunge gli
specchi soltanto nel training. Nessuna posizione, o suo riflesso, può apparire
nei due gruppi. Non usiamo dati delle partite degli utenti.

Dataset, eseguibile dell'insegnante e checkpoint PyTorch rimangono in `build/`,
esclusa da Git. I pesi finali e i rapporti sono piccoli e vengono inclusi nel
repository. La generazione viene ripetuta se cambiano seed, quantità o profondità.

## Rete e apprendimento

Gli ingressi sono due piani di 42 valori: mie pedine e pedine avversarie.
Tre trasformazioni lineari producono `84 → 128 → 64 → 7` valori; ReLU viene
applicata solo dopo i primi due strati. In totale ci sono 19.591 pesi e bias.

Durante l'allenamento Adam modifica i parametri per aumentare la probabilità
complessiva delle mosse corrette. Gli esempi di vittoria o parata pesano sei volte
gli altri. Le colonne piene vengono mascherate. Se più mosse sono corrette,
non imponiamo arbitrariamente una sola etichetta. A ogni epoca misuriamo accordo
con l'insegnante, vittorie immediate colte e minacce bloccate nella validazione.
Conserviamo il checkpoint con la somma più alta di queste tre percentuali.

Il file esportato contiene intestazione, dimensioni, pesi per neurone e bias.
C++ esegue le stesse somme e ReLU e sceglie l'uscita più alta tra le colonne
libere. Non contiene l'insegnante, una ricerca, o un controllo delle minacce.

## Valutazione e limiti

`valuta.py` genera altre 30.000 posizioni con un seed distinto, esclude quelle
presenti nel dataset originale (anche riflesse) e valuta il modello senza
modificarne i pesi. Inoltre gioca 200 partite contro un avversario casuale e 200
contro un avversario tattico elementare, alternando i colori.

L'avversario tattico cerca una vittoria, poi un blocco immediato, altrimenti gioca
a caso. Questo controllo è presente **solo nell'avversario del test**, non nel bot.
Un buon risultato contro questi avversari non dimostra gioco perfetto o forza
contro persone esperte. La rete può ancora sbagliare, anche mosse elementari.
`valutazione.json` include l'hash dei pesi a cui si riferiscono i risultati.
