# Nickgame

Progetto per il corso di Advanced Programming Languages.

## Descrizione

Stanze multiplayer con quattro giochi in Python e aggiornamenti tramite Go: Forza 4, Quiz, Nomi, cose, città e Just One.

## Struttura

- `cpp/`: regole economiche e inferenza della rete neurale di Forza 4.
- `python/`: applicazione Flask, quattro giochi, profili, avatar e persistenza SQLite.
- `go/`: server WebSocket per notificare gli aggiornamenti delle stanze.
- `allenamento/`: generazione dei dati, allenamento e valutazione della rete neurale.
- `modelli/forza4/`: pesi già allenati e rapporti del modello.

Python gestisce le regole e il database, Go distribuisce gli eventi ai browser e C++ esegue i calcoli economici e la rete neurale.

## Prima installazione

Servono Python 3.9 o successivo con supporto `venv`, Go 1.22 o successivo,
Bash e g++ con supporto C++17. Dalla cartella `nickgame`:

```bash
python3 -m venv python/.venv
python/.venv/bin/python -m pip install -r python/requirements.txt
```

La prima installazione richiede una connessione Internet per scaricare Flask
e la dipendenza Go, scaricata automaticamente durante la compilazione.
Per giocare si usano i pesi già inclusi: non occorre allenare il modello.

## Avvio con un solo comando

Dalla cartella `nickgame`:

```bash
./run.sh
```

Avvia Flask sulla porta **50010** e Go sulla **50011**.
Apri http://127.0.0.1:50010. **Ctrl+C ferma entrambi**; se uno dei server si
arresta, lo script chiude anche l'altro. Ferma prima eventuali server già avviati
nei vecchi terminali: lo script non interrompe programmi che occupano le porte.

Servono Python con Flask installato, Go e g++ con supporto C++17. Se esiste `python/.venv`, lo script usa
quel Python; altrimenti usa `python3`. Il binario Go viene compilato in
`go/build/`; i due eseguibili C++ in `cpp/build/`. Entrambe le cartelle sono escluse da Git. Per porte diverse si possono impostare
`NICKGAME_PY_PORT` e `NICKGAME_GO_PORT` prima del comando.

## Accesso temporaneo

In “Gioca senza account” basta uno username libero per creare una stanza o entrare,
anche dalla lista pubblica. Gli ospiti possono giocare e scegliere un avatar gratuito.
Non ricevono un codice personale né accumulano Nickcoin o acquisti. Uscendo dalla
stanza, o quando l'admin la chiude, partecipazione e avatar temporaneo vengono eliminati.
Chiudere soltanto la scheda non equivale a uscire dalla stanza.
Gli username registrati rimangono riservati ai proprietari dei profili.

## Profili, monete e cosmetici

Dalla pagina iniziale puoi creare un profilo scegliendo uno username libero.
Conserva il codice personale di sei cifre assegnato: permette di accedere nuovamente
al profilo. Dopo l’accesso puoi creare una stanza o entrare con il codice stanza,
che è distinto dal codice personale.

Gli acquisti sono integrati in “Il tuo personaggio”, aperto dall’omino nella stanza.
I profili iniziano con zero monete e possono usare gratuitamente ragazzo/ragazza,
felpa arancione e jeans. Le frecce mostrano tutti gli oggetti: quelli non posseduti
hanno un lucchetto con il prezzo. Premendolo si acquista il pezzo; Salva indossa
il personaggio scelto. Gli acquisti restano anche se si annulla la modifica dell’avatar.

- Vittoria: 30 monete. Pareggio o primo posto condiviso: 15. Sconfitta: 0.
- Just One: 10 monete per parola indovinata a ciascun partecipante a fine partita.
- Teste: 30 monete; corpi: 50; gambe: 40, salvo gli oggetti gratuiti.
- Le partite abbandonate non danno premi. Ricaricare una pagina non accredita di nuovo.

`cpp/main.cpp` legge i comandi; `cpp/economia.cpp` contiene le regole;
`cpp/economia.hpp` dichiara le funzioni. Flask chiama l'eseguibile con `subprocess`,
senza un terzo server. SQLite conserva portafogli, cosmetici, acquisti e premi;
la conclusione di una partita e i relativi premi vengono salvati insieme.

## Avvio manuale

Dopo la prima installazione, compila entrambi gli eseguibili dalla cartella `nickgame`:

```bash
mkdir -p cpp/build
g++ -std=c++17 -Wall -Wextra -Werror -O2 cpp/main.cpp cpp/economia.cpp -o cpp/build/nickgame-economia
g++ -std=c++17 -Wall -Wextra -Werror -O2 cpp/bot/main.cpp cpp/bot/rete_forza4.cpp -o cpp/build/nickgame-bot
cd python
.venv/bin/python -m flask --app app run --port 50010
```

Lascia aperto questo terminale. In un secondo terminale, dalla cartella `nickgame`:

```bash
cd go
go run .
```

Serve Go 1.22 o successivo. Il primo avvio scarica la dipendenza
`github.com/gorilla/websocket`. Avvia Flask almeno una volta prima di Go:
crea la chiave locale condivisa tra i due servizi.

Apri http://127.0.0.1:50010. Per simulare un secondo utente usa un altro browser
oppure una finestra privata. I nuovi ingressi aggiornano automaticamente
l'elenco dei partecipanti. Dopo un aggiornamento, riavvia i server e ricarica le pagine già aperte.

SQLite è incluso in Python. Al primo avvio vengono creati il database
`python/instance/nickgame.sqlite` e la chiave locale che firma le sessioni.
Questa cartella è esclusa da Git. Gli avvii successivi conservano i dati.

## Stanze disponibili

Sotto il form di accesso compaiono codice, admin e numero di partecipanti delle
stanze disponibili. Accedi al profilo oppure inserisci uno username in “Gioca senza account”,
poi premi “Entra” sulla stanza scelta:
il codice viene compilato automaticamente e viene inviato il normale form.
Rimane disponibile anche l'accesso inserendo manualmente il codice.

Il canale WebSocket pubblico `lobby` aggiorna la lista quando una stanza viene
creata o chiusa e quando qualcuno entra o esce. Il browser legge `/api/stanze`
solo alla connessione, agli eventi o dopo un errore; non c'è polling periodico
quando la connessione funziona. La lista è visibile anche prima del login.

## Dati e regole attuali

- `stanze`: `codice` è una chiave primaria testuale di 6 cifre.
- `utenti`: `username` è la chiave primaria; `stanza_codice` collega la stanza;
  `is_admin` vale 1 per il creatore e 0 per gli altri partecipanti.
  `accesso_id` distingue ogni nuova registrazione, anche quando uno username viene riutilizzato.
- Ogni utente appartiene a una sola stanza. Un indice impedisce due admin nella stessa stanza.
- Gli username sono globalmente univoci e distinguono maiuscole e minuscole.
- Il server assegna il ruolo admin; il form non può sceglierlo.
- Il profilo permanente si crea con uno username; il server assegna un codice personale
  segreto di sei cifre per gli accessi successivi. È distinto dal codice stanza.
  Conservarlo: non esiste ancora un recupero del codice perso.
  Il codice è salvato in chiaro in `profili.codice_personale`, con vincolo UNIQUE;
  il login cerca direttamente quel valore tramite query parametrizzata. Non c’è
  un blocco dei tentativi. Questa semplificazione è destinata al progetto locale.
- “Esci dalla stanza” elimina la partecipazione temporanea. Profilo, monete, acquisti
  e avatar rimangono salvati; lo username rimane riservato.
- “Esci e chiudi stanza”, disponibile all'admin, elimina la stanza e tutti i suoi utenti.
  Go notifica il cambiamento; i browser dei partecipanti ricevono HTTP 401 da Flask
  e tornano alla pagina iniziale. I loro profili restano salvati. Le altre stanze restano attive.
- I vecchi cookie non tornano validi quando uno username viene riutilizzato:
  Flask controlla anche `accesso_id`. L’identificatore cambia a ogni nuova partecipazione.
- Il controllo dei campi avviene sul server. Il form usa `novalidate` per evitare
  che un codice incompleto blocchi anche il pulsante “Crea stanza”.

## Catalogo giochi e scelta dell'admin

La tabella `giochi` contiene nome e numero massimo di giocatori. Il primo elemento
è **Forza 4**, massimo **2**; sono disponibili anche **Quiz**, **Nomi, cose, città** e **Just One**, massimo **8**. Ogni stanza conserva la scelta in `stanze.gioco_id`.
Tutti i partecipanti vedono i giochi compatibili con il numero attuale di utenti;
l'admin clicca sull'intera scheda per scegliere un gioco. La scelta viene evidenziata
per tutti tramite Go, senza avviare la partita. In un pannello sotto il catalogo
compare il pulsante Avvia, disponibile solo all'admin. Gli altri vedono la scelta
e attendono. Servono almeno 2 partecipanti, oppure 3 per Just One.
Il controllo del ruolo viene ripetuto sul server; la scheda funziona anche da tastiera.

Con tre o più partecipanti Forza 4 non viene mostrato. Se era già selezionato,
l'ingresso del terzo utente annulla la scelta. Tornando a due utenti il gioco
ricompare e l'admin può avviarlo nuovamente. Il filtro usa il massimo salvato
nel database e si applica anche ai giochi che verranno aggiunti.

Gli eventi Go aggiornano catalogo e selezione per tutti. L'admin può avviare Forza 4 quando ci sono esattamente due giocatori.
Nella prima partita l'admin usa le pedine rosse e comincia; l'altro usa quelle gialle.
A ogni rivincita i colori si scambiano: inizia sempre il rosso.
Premi il numero sopra una colonna per inserire una pedina. Vince chi allinea
quattro pedine in orizzontale, verticale o diagonale; a tabellone pieno senza
vincitore è pareggio. Al termine l'admin può avviare una rivincita.

Python salva griglia, giocatori, turno e risultato in `partite_forza4`.
La funzione Python `regole_forza4.gioca` riceve griglia, turno e colonna e restituisce
griglia aggiornata e risultato. Non accede al database. Go avvisa i browser dopo il salvataggio:
il tabellone dell'avversario si aggiorna senza ricaricare la pagina.
Durante la partita sono visibili solo il gioco e, per l’admin, “Torna alla stanza”.
Il pulsante riporta tutti nella sala tramite Go, conservando la partita e sospendendo
le mosse. Solo l’admin può premere “Torna al gioco” per far riprendere tutti.
Chi gioca invia un normale form e torna al pannello della partita.

Se uno dei giocatori esce, la partita viene cancellata. Se entra un terzo
partecipante, Forza 4 viene deselezionato e la partita annullata.
Ricaricare la pagina o riavviare i server conserva invece la partita nel database.

## Giocatore neurale per Forza 4

Quando è solo nella stanza, l'admin può premere **Aggiungi giocatore AI**.
NickBot occupa il secondo posto e gioca con una piccola rete neurale locale.
Non possiede un profilo o un portafoglio; l'umano registrato conserva i normali
premi. Per accogliere altri giocatori o cambiare gioco, l'admin deve rimuovere
il bot: questo annulla anche la partita corrente.

La rete ha **84 ingressi, due strati intermedi da 128 e 64 neuroni, 7 uscite**
e 19.591 parametri. I primi 42 ingressi indicano le proprie pedine, gli altri
42 quelle avversarie. C++ calcola somme pesate e ReLU; sceglie il valore più
alto fra le colonne libere. Non simula mosse future, non applica correzioni
tattiche e non chiama un LLM. Le colonne piene sono escluse perché non sono
mosse consentite. Python verifica comunque la legalità prima di salvare.

- `cpp/bot/main.cpp`: riceve griglia e colore e restituisce la colonna (0–6).
- `cpp/bot/rete_forza4.cpp` e `.hpp`: caricano i pesi ed eseguono la rete.
- `modelli/forza4/pesi.txt`: pesi già allenati, inclusi nel progetto.
- `python/bot.py`: gestisce partecipante e calcolo del turno in background.
- `python/repository_bot.py`: query per le richieste AI.
- `allenamento/`: strumenti separati per generare esempi, allenare e valutare.

`./run.sh` compila anche la rete con la sola libreria standard C++17:

```bash
mkdir -p cpp/build
g++ -std=c++17 -Wall -Wextra -Werror -O2 cpp/bot/main.cpp cpp/bot/rete_forza4.cpp -o cpp/build/nickgame-bot
```

Non servono PyTorch, GPU, libcurl, chiavi o OmniProxy per giocare. La precedente
configurazione locale `python/instance/bot.json` non viene più letta.
PyTorch e NumPy servono soltanto per rifare l'allenamento: istruzioni in
[allenamento/README.md](allenamento/README.md).

L'insegnante usa una ricerca limitata delle mosse **solo per generare il dataset**;
non fa parte del percorso di gioco. Una rete piccola non garantisce mosse perfette:
le misure e i limiti del modello distribuito sono in [modelli/forza4](modelli/forza4).

Turno, partita, griglia e token vengono ricontrollati prima di applicare la mossa.
Pausa, rimozione e chiusura della stanza invalidano le risposte pendenti. Go
aggiorna i browser. Alla rivincita il bot può iniziare per primo. Dopo un
riavvio, un turno interrotto mostra **Riprova turno AI**. Non ci sono mosse
casuali di riserva se il file dei pesi manca o il calcolo fallisce.
La gestione dei thread è pensata per il processo Flask singolo di `run.sh`.

## Quiz

Il Quiz è implementato in Python: regole e punteggi in `quiz.py`, query SQL in
`repository_quiz.py`. Go riusa le notifiche della stanza per aggiornare tutti.

- Da 2 a 8 giocatori; sopra 8 il gioco non compare nel catalogo.
- Cinque domande fisse salvate in SQLite, con quattro opzioni ciascuna e senza timer.
- Una risposta per giocatore e domanda: un punto se corretta, zero altrimenti.
- Soluzione e classifica compaiono solo quando tutti i partecipanti presenti hanno risposto.
- Solo l'admin avvia, passa alla domanda successiva e mostra la classifica finale.
- I pari merito sono consentiti. “Nuovo Quiz” azzera risposte e punteggi.
- L'admin può riportare tutti nella sala e riprendere il quiz senza perdere le risposte.
- Durante un quiz non concluso sono bloccati nuovi ingressi, anche quando è in pausa.
- Chi esce viene rimosso dalla classifica e non blocca la domanda. Se rimane un solo
  giocatore, il quiz viene annullato; chiudere la stanza elimina quiz e risposte.
- Cambiare gioco annulla la partita precedente. Un reload o il riavvio dei server
  conserva invece domande, risposte e pausa nel database.

Le tabelle sono `domande_quiz`, `partite_quiz` e `risposte_quiz`. La soluzione
corretta viene letta dal server: non si accettano punteggi inviati dal browser.

## Nomi, cose, città

Gioco interamente Python, da 2 a 8 giocatori. L'admin lo avvia dal catalogo.
La partita dura tre manche: ogni volta viene estratta una lettera diversa e si
compilano Nomi, Cose e Città. Il primo invio avvia cinque secondi per gli altri.
Le bozze vengono salvate durante la digitazione; alla scadenza il server blocca
le parole già ricevute, lasciando vuoti i campi non compilati. La scadenza è
salvata nel DB e non riparte ricaricando la pagina.

Le risposte restano nascoste fino alla chiusura della fase di scrittura.
Ogni giocatore seleziona 👎 sulle parole altrui che contesta e conferma i voti,
anche se non contesta nulla. Non si possono votare le proprie risposte.
Confermati i voti di tutti, una parola è annullata con la maggioranza assoluta
degli avversari: floor((giocatori - 1) / 2) + 1 contrari.
Le parole vuote o con iniziale errata valgono automaticamente zero.
Le parole valide valgono 10 punti se uniche, 5 se almeno due giocatori hanno
scritto la stessa parola valida nella stessa categoria. Maiuscole, accenti e
spazi ripetuti vengono ignorati. Il significato è valutato dai giocatori,
senza dizionario automatico.

L'admin avvia la manche successiva e, dopo la terza, mostra la classifica finale;
i pari merito sono consentiti. “Nuova partita” azzera i punteggi.
Gli aggiornamenti Go conservano testi in scrittura e spunte della valutazione.
Le bozze ricevute dal server sono salvate nel database e ripristinate ricaricando
la pagina. Gli ultimi caratteri non ancora trasmessi possono andare persi.

Come nel Quiz, gli ingressi sono bloccati durante la partita, anche in pausa.
Chi esce viene rimosso dalla classifica e non blocca le risposte attese; con meno
di due partecipanti la partita viene annullata. I punti delle manche già valutate
restano quelli assegnati prima dell'uscita. L'admin può tornare nella sala e
riprendere per tutti, conservando i dati. Cambiare gioco cancella la partita precedente.

## Just One

Versione didattica cooperativa in Python, da 3 a 8 giocatori, senza timer.
Una manche a testa per indovinare: comincia l'admin, poi gli altri in ordine di username.
Le parole sono estratte da `parole_justone` in SQLite, senza ripetizioni nella partita.

Solo chi scrive gli indizi vede la parola segreta. Gli altri inviano una sola
parola composta da massimo 30 lettere. Quando tutti hanno inviato, gli indizi
uguali vengono eliminati, ignorando maiuscole e accenti. L'indovino vede solo
quelli rimasti e ha un tentativo, oppure può passare. Ogni risposta corretta vale
un punto per la squadra; l'admin avanza e mostra il risultato finale.

Il server impedisce indizi identici alla parola segreta. Varianti e traduzioni
non vengono riconosciute automaticamente: il rispetto di queste regole è affidato
ai giocatori. Il confronto del tentativo con la soluzione ignora maiuscole e accenti.
La parola segreta e gli indizi eliminati non compaiono nell'HTML dell'indovino;
la parola viene rivelata a tutti solo dopo il tentativo o il passaggio.

La pausa condivisa conserva partita e indizi. Nuovi ingressi attendono la fine.
Per mantenere una rotazione semplice e stabile, se qualcuno esce dalla stanza
la partita di Just One viene annullata. Un reload non equivale a uscire e conserva
i dati già inviati. “Nuova partita” azzera punteggio e indizi.

## Verifica

I test sono conservati solo localmente in `tests/` e `python/tests/` e non sono
inclusi nel repository. Nella copia di sviluppo, dalla cartella `nickgame`,
la suite locale usata per le verifiche recenti si esegue con:

```bash
PYTHONPATH=python python/.venv/bin/python -m unittest discover -s tests -v
```

La suite controlla profili e codici personali, ospiti, economia, votazioni di
Nomi, cose, città, gestione del bot e inferenza C++. Il confronto numerico della
rete richiede NumPy nell’ambiente di test. Queste verifiche non sono un passaggio
necessario per avviare la copia pubblica.

## Riferimento per lo studio

[Flask: connessione a SQLite e gestione della connessione](https://flask.palletsprojects.com/en/stable/tutorial/database/).

## Organizzazione del codice Python

- `app.py`: legge il form, gestisce sessioni, pagine HTML e API.
- `configurazione.py`: prepara percorsi, chiave locale e impostazioni di Flask.
- `sincronizzazione.py`: invia gli avvisi a Go e costruisce l’indirizzo WebSocket.
- `servizi.py`: controlla le regole di accesso, genera i codici e assegna l'admin.
- `forza4.py`: controlla avvio e turni e salva le mosse.
- `regole_forza4.py`: applica le regole di Forza 4 senza Flask o SQL.
- `quiz.py`: gestisce domande, risposte, punti e avanzamento del Quiz.
- `nomi.py`: gestisce manche, convalida e punteggi di Nomi, cose, città.
- `justone.py`: gestisce ruoli, indizi, tentativi e punteggio cooperativo.
- `repository_justone.py`: contiene le query SQL di Just One.
- `repository_nomi.py`: contiene le query SQL di Nomi, cose, città.
- `repository_quiz.py`: contiene le query SQL del Quiz.
- `repository.py`: contiene le query SQL per utenti, stanze, giochi e partite.
- `connessione.py`: apre e chiude la connessione, inizializza lo schema e gestisce commit/rollback.
- `schema.sql`: definisce tabelle e vincoli del database.

Il servizio esegue creazione della stanza e inserimento dell'admin nella stessa
transazione: un errore annulla entrambe le modifiche. Il repository non fa commit
per ogni query. Le letture delle pagine passano direttamente dal repository.
Questa separazione è volutamente semplice; il collegamento al database usa ancora
il contesto Flask, tramite `current_app` e `g`.

Per usare porte diverse, dalla cartella `nickgame`:

```bash
NICKGAME_PY_PORT=50012 NICKGAME_GO_PORT=50013 ./run.sh
```

In questo esempio apri http://127.0.0.1:50012. Lo script configura anche gli
indirizzi usati da Flask per comunicare con Go.

## Organizzazione del codice Go

- `main.go`: configurazione, registrazione degli indirizzi e avvio del server.
- `connessioni.go`: struttura del server, mappa, mutex, apertura e chiusura dei WebSocket.
- `notifiche.go`: ricezione degli avvisi da Flask e invio ai browser della stanza.

I tre file appartengono a `package main`: condividono funzioni e tipi senza
importarsi tra loro. Ogni file importa solo i pacchetti che usa direttamente.
Avvia l'intero package con `go run .` dalla cartella `go`.

## Sincronizzazione in tempo reale

1. Flask salva l'ingresso in SQLite e, dopo il commit, avvisa Go tramite HTTP.
2. Go invia un evento WebSocket ai browser collegati alla stanza interessata
   e un evento `stanze_aggiornate` ai browser sulla pagina di accesso.
3. `python/static/stanza.js` riceve l'evento e legge partecipanti, giochi e partita da Flask.
4. Il browser aggiorna i pannelli senza ricaricare la pagina.

Go non accede a SQLite. Le API Flask ricavano la stanza dalla sessione e
non accettano dal browser il codice di una stanza arbitraria.
Il WebSocket locale riceve il codice della stanza senza un permesso firmato:
chi conosce un codice può ascoltarne gli avvisi di cambiamento, ma questi non
contengono nomi o altri dati. Per leggere i partecipanti serve la sessione Flask
della propria stanza. Le notifiche HTTP da Flask a Go richiedono invece la chiave
locale condivisa, che non viene inviata al browser.

Questa versione è configurata per l'uso sul computer locale: Go ascolta su
`127.0.0.1:50011` e accetta origini browser locali. Per un deployment remoto
servono anche autenticazione dei canali WebSocket, configurazione degli indirizzi,
origini autorizzate e TLS.

Se Go è fermo, gli ingressi restano salvati e il browser tenta la riconnessione
in background, senza mostrare messaggi tecnici nella pagina.
Il browser riprova ogni tre secondi e recupera l'elenco alla nuova connessione.
La versione Go usa una mappa e un mutex: gli invii sono sequenziali e un browser
lento può ritardare gli altri. Senza ping periodici, una connessione interrotta
senza chiusura esplicita può essere rimossa solo quando una lettura o un invio
rilevano il problema.
Le notifiche non sono persistenti: un singolo avviso perso mentre il socket
resta connesso può richiedere una riconnessione o un aggiornamento manuale.
L'elenco rappresenta gli utenti registrati nella stanza, non la presenza online:
chiudere una scheda non rimuove l'utente; occorre usare il pulsante di uscita.
Se Go è fermo, il logout degli altri partecipanti viene riconosciuto alla prossima
richiesta a Flask o alla riconnessione, anziché tramite una notifica immediata.

Configurazioni opzionali:

- Go: `NICKGAME_GO_PORT` (default `50011`) e `NICKGAME_SECRET_FILE`
  (default `../python/instance/secret.key`, relativo alla cartella di avvio).
- Flask: `NICKGAME_GO_HTTP_URL` (default `http://127.0.0.1:50011`) e
  `NICKGAME_GO_WS_URL` (default `ws://127.0.0.1:50011`).
- Se cambi la porta di Go, aggiorna anche i due indirizzi di Flask.

Riferimenti: [Gorilla WebSocket](https://pkg.go.dev/github.com/gorilla/websocket)
e [WebSocket nel browser](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket).
