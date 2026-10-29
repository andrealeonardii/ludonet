CREATE TABLE IF NOT EXISTS giochi (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    max_giocatori INTEGER NOT NULL CHECK (max_giocatori > 0)
);

INSERT INTO giochi (nome, max_giocatori) VALUES ('Forza 4', 2)
    ON CONFLICT(nome) DO NOTHING;

CREATE TABLE IF NOT EXISTS stanze (
    codice TEXT PRIMARY KEY NOT NULL
        CHECK (length(codice) = 6 AND codice NOT GLOB '*[^0-9]*'),
    gioco_id INTEGER REFERENCES giochi(id)
);

CREATE TABLE IF NOT EXISTS utenti (
    username TEXT PRIMARY KEY NOT NULL
        CHECK (length(trim(username)) BETWEEN 1 AND 30),
    accesso_id TEXT NOT NULL,
    is_ospite INTEGER NOT NULL DEFAULT 0 CHECK (is_ospite IN (0, 1)),
    is_bot INTEGER NOT NULL DEFAULT 0 CHECK (is_bot IN (0, 1)),
    stanza_codice TEXT NOT NULL REFERENCES stanze(codice),
    is_admin INTEGER NOT NULL DEFAULT 0 CHECK (is_admin IN (0, 1))
);

-- Una stanza può avere molti utenti, ma al massimo un admin.
CREATE UNIQUE INDEX IF NOT EXISTS un_admin_per_stanza
    ON utenti(stanza_codice) WHERE is_admin = 1;

-- Una partita per stanza. Se un giocatore esce, la partita viene cancellata.
CREATE TABLE IF NOT EXISTS partite_forza4 (
    stanza_codice TEXT PRIMARY KEY REFERENCES stanze(codice) ON DELETE CASCADE,
    id TEXT NOT NULL,
    rosso TEXT NOT NULL REFERENCES utenti(username) ON DELETE CASCADE,
    giallo TEXT NOT NULL REFERENCES utenti(username) ON DELETE CASCADE,
    griglia TEXT NOT NULL CHECK (length(griglia) = 42 AND griglia NOT GLOB '*[^012]*'),
    turno INTEGER NOT NULL CHECK (turno IN (1, 2)),
    in_sala INTEGER NOT NULL DEFAULT 0 CHECK (in_sala IN (0, 1)),
    risultato INTEGER NOT NULL CHECK (risultato BETWEEN 0 AND 3)
);

-- Il token identifica una richiesta al modello: una risposta vecchia non può giocare.
CREATE TABLE IF NOT EXISTS richieste_bot (
    stanza_codice TEXT PRIMARY KEY REFERENCES partite_forza4(stanza_codice) ON DELETE CASCADE,
    token TEXT NOT NULL,
    stato TEXT NOT NULL CHECK (stato IN ('attesa', 'errore')),
    messaggio TEXT NOT NULL DEFAULT ''
);

INSERT INTO giochi (nome, max_giocatori) VALUES ('Quiz', 8)
    ON CONFLICT(nome) DO NOTHING;

-- Prima versione: cinque domande fisse, quattro opzioni numerate da 0 a 3.
CREATE TABLE IF NOT EXISTS domande_quiz (
    id INTEGER PRIMARY KEY,
    testo TEXT NOT NULL,
    opzione_a TEXT NOT NULL,
    opzione_b TEXT NOT NULL,
    opzione_c TEXT NOT NULL,
    opzione_d TEXT NOT NULL,
    corretta INTEGER NOT NULL CHECK (corretta BETWEEN 0 AND 3)
);
INSERT OR IGNORE INTO domande_quiz VALUES
    (1, 'Quanto fa 7 × 8?', '54', '56', '58', '64', 1),
    (2, 'Qual è la capitale della Francia?', 'Madrid', 'Lione', 'Parigi', 'Berlino', 2),
    (3, 'Quanti lati ha un esagono?', '5', '8', '7', '6', 3),
    (4, 'Quale pianeta è conosciuto come il pianeta rosso?', 'Marte', 'Venere', 'Giove', 'Saturno', 0),
    (5, 'Quanti bit ci sono in un byte?', '4', '8', '16', '32', 1);

CREATE TABLE IF NOT EXISTS partite_quiz (
    stanza_codice TEXT PRIMARY KEY REFERENCES stanze(codice) ON DELETE CASCADE,
    id TEXT NOT NULL,
    domanda INTEGER NOT NULL DEFAULT 1 CHECK (domanda BETWEEN 1 AND 5),
    in_sala INTEGER NOT NULL DEFAULT 0 CHECK (in_sala IN (0, 1)),
    finita INTEGER NOT NULL DEFAULT 0 CHECK (finita IN (0, 1))
);

CREATE TABLE IF NOT EXISTS risposte_quiz (
    stanza_codice TEXT NOT NULL REFERENCES partite_quiz(stanza_codice) ON DELETE CASCADE,
    username TEXT NOT NULL REFERENCES utenti(username) ON DELETE CASCADE,
    domanda INTEGER NOT NULL REFERENCES domande_quiz(id),
    risposta INTEGER NOT NULL CHECK (risposta BETWEEN 0 AND 3),
    punti INTEGER NOT NULL CHECK (punti IN (0, 1)),
    PRIMARY KEY (stanza_codice, username, domanda)
);

INSERT INTO giochi (nome, max_giocatori) VALUES ('Nomi, cose, città', 8)
    ON CONFLICT(nome) DO NOTHING;

CREATE TABLE IF NOT EXISTS partite_nomi (
    stanza_codice TEXT PRIMARY KEY REFERENCES stanze(codice) ON DELETE CASCADE,
    id TEXT NOT NULL,
    turno INTEGER NOT NULL DEFAULT 1 CHECK (turno BETWEEN 1 AND 3),
    lettere TEXT NOT NULL,
    scadenza REAL,
    valutato INTEGER NOT NULL DEFAULT 0 CHECK (valutato IN (0, 1)),
    in_sala INTEGER NOT NULL DEFAULT 0 CHECK (in_sala IN (0, 1)),
    finita INTEGER NOT NULL DEFAULT 0 CHECK (finita IN (0, 1))
);

CREATE TABLE IF NOT EXISTS risposte_nomi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stanza_codice TEXT NOT NULL REFERENCES partite_nomi(stanza_codice) ON DELETE CASCADE,
    username TEXT NOT NULL REFERENCES utenti(username) ON DELETE CASCADE,
    turno INTEGER NOT NULL CHECK (turno BETWEEN 1 AND 3),
    categoria TEXT NOT NULL CHECK (categoria IN ('nomi', 'cose', 'citta')),
    testo TEXT NOT NULL CHECK (length(testo) <= 60),
    valida INTEGER NOT NULL DEFAULT 0 CHECK (valida IN (0, 1)),
    punti INTEGER NOT NULL DEFAULT 0 CHECK (punti IN (0, 5, 10)),
    UNIQUE (stanza_codice, username, turno, categoria)
);

INSERT INTO giochi (nome, max_giocatori) VALUES ('Just One', 8)
    ON CONFLICT(nome) DO NOTHING;

CREATE TABLE IF NOT EXISTS parole_justone (
    id INTEGER PRIMARY KEY,
    testo TEXT NOT NULL UNIQUE
);
INSERT OR IGNORE INTO parole_justone (testo) VALUES
    ('montagna'), ('cioccolato'), ('pianoforte'), ('astronauta'),
    ('biblioteca'), ('girasole'), ('vulcano'), ('ombrello'),
    ('castello'), ('delfino'), ('bicicletta'), ('deserto'),
    ('arcobaleno'), ('farfalla'), ('orologio'), ('gelato');

CREATE TABLE IF NOT EXISTS partite_justone (
    stanza_codice TEXT PRIMARY KEY REFERENCES stanze(codice) ON DELETE CASCADE,
    id TEXT NOT NULL,
    turno INTEGER NOT NULL DEFAULT 1 CHECK (turno BETWEEN 1 AND 8),
    in_sala INTEGER NOT NULL DEFAULT 0 CHECK (in_sala IN (0, 1)),
    finita INTEGER NOT NULL DEFAULT 0 CHECK (finita IN (0, 1))
);

CREATE TABLE IF NOT EXISTS manche_justone (
    stanza_codice TEXT NOT NULL REFERENCES partite_justone(stanza_codice) ON DELETE CASCADE,
    turno INTEGER NOT NULL,
    parola_id INTEGER NOT NULL REFERENCES parole_justone(id),
    indovina TEXT NOT NULL REFERENCES utenti(username) ON DELETE CASCADE,
    tentativo TEXT,
    riuscito INTEGER NOT NULL DEFAULT 0 CHECK (riuscito IN (0, 1)),
    PRIMARY KEY (stanza_codice, turno)
);

CREATE TABLE IF NOT EXISTS indizi_justone (
    stanza_codice TEXT NOT NULL,
    turno INTEGER NOT NULL,
    username TEXT NOT NULL REFERENCES utenti(username) ON DELETE CASCADE,
    testo TEXT NOT NULL CHECK (length(testo) BETWEEN 1 AND 30),
    PRIMARY KEY (stanza_codice, turno, username),
    FOREIGN KEY (stanza_codice, turno) REFERENCES manche_justone(stanza_codice, turno) ON DELETE CASCADE
);

-- Il profilo e l'avatar rimangono anche quando il giocatore esce dalla stanza.
CREATE TABLE IF NOT EXISTS profili (
    username TEXT PRIMARY KEY NOT NULL CHECK (length(trim(username)) BETWEEN 1 AND 30),
    codice_personale TEXT NOT NULL UNIQUE
        CHECK (length(codice_personale) = 6 AND codice_personale NOT GLOB '*[^0-9]*')
);

CREATE TABLE IF NOT EXISTS avatar (
    username TEXT PRIMARY KEY REFERENCES profili(username) ON DELETE CASCADE,
    testa TEXT NOT NULL,
    corpo TEXT NOT NULL,
    piedi TEXT NOT NULL
);

-- Economia permanente: non dipende dalla durata delle stanze.
CREATE TABLE IF NOT EXISTS portafogli (
    username TEXT PRIMARY KEY REFERENCES profili(username) ON DELETE CASCADE,
    saldo INTEGER NOT NULL DEFAULT 0 CHECK (saldo BETWEEN 0 AND 2147483647)
);
CREATE TABLE IF NOT EXISTS cosmetici (
    id TEXT PRIMARY KEY,
    parte TEXT NOT NULL CHECK (parte IN ('testa', 'corpo', 'piedi')),
    immagine TEXT NOT NULL,
    nome TEXT NOT NULL,
    prezzo INTEGER NOT NULL CHECK (prezzo >= 0),
    UNIQUE(parte, immagine)
);
INSERT OR IGNORE INTO cosmetici VALUES
    ('testa-ragazzo', 'testa', 'ragazzo', 'Ragazzo', 0),
    ('testa-ragazza', 'testa', 'ragazza', 'Ragazza', 0),
    ('testa-gatto', 'testa', 'gatto', 'Gatto', 30),
    ('testa-zucca', 'testa', 'zucca', 'Zucca', 30),
    ('testa-astronauta', 'testa', 'astronauta', 'Casco astronauta', 30),
    ('testa-robot', 'testa', 'robot', 'Robot turchese', 30),
    ('testa-robot-femminile', 'testa', 'robot-femminile', 'Robot rosa', 30),
    ('corpo-felpa-arancione', 'corpo', 'felpa-arancione', 'Felpa arancione', 0),
    ('corpo-robot', 'corpo', 'robot', 'Corpo robot', 50),
    ('corpo-astronauta-rosa', 'corpo', 'astronauta-rosa', 'Tuta rosa', 50),
    ('corpo-astronauta-turchese', 'corpo', 'astronauta-turchese', 'Tuta turchese', 50),
    ('corpo-peluche-arancione', 'corpo', 'peluche-arancione', 'Corpo peluche', 50),
    ('piedi-jeans-blu', 'piedi', 'jeans-blu', 'Jeans blu', 0),
    ('piedi-robot', 'piedi', 'robot', 'Gambe robot', 40),
    ('piedi-astronauta-rosa', 'piedi', 'astronauta-rosa', 'Pantaloni tuta rosa', 40),
    ('piedi-astronauta-turchese', 'piedi', 'astronauta-turchese', 'Pantaloni tuta turchese', 40),
    ('piedi-peluche-arancione', 'piedi', 'peluche-arancione', 'Zampe peluche', 40);
CREATE TABLE IF NOT EXISTS acquisti (
    username TEXT NOT NULL REFERENCES profili(username) ON DELETE CASCADE,
    cosmetico_id TEXT NOT NULL REFERENCES cosmetici(id),
    PRIMARY KEY(username, cosmetico_id)
);
CREATE TABLE IF NOT EXISTS premi (
    partita_id TEXT NOT NULL,
    gioco TEXT NOT NULL,
    username TEXT NOT NULL REFERENCES profili(username) ON DELETE CASCADE,
    monete INTEGER NOT NULL CHECK (monete >= 0),
    PRIMARY KEY(partita_id, gioco, username)
);

-- Gli avatar ospiti vengono rimossi insieme alla partecipazione temporanea.
CREATE TABLE IF NOT EXISTS avatar_ospiti (
    username TEXT PRIMARY KEY REFERENCES utenti(username) ON DELETE CASCADE,
    testa TEXT NOT NULL,
    corpo TEXT NOT NULL,
    piedi TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bozze_nomi (
    stanza_codice TEXT NOT NULL REFERENCES partite_nomi(stanza_codice) ON DELETE CASCADE,
    username TEXT NOT NULL REFERENCES utenti(username) ON DELETE CASCADE,
    turno INTEGER NOT NULL,
    nomi TEXT NOT NULL, cose TEXT NOT NULL, citta TEXT NOT NULL,
    PRIMARY KEY(stanza_codice, username, turno)
);
CREATE TABLE IF NOT EXISTS voti_nomi (
    risposta_id INTEGER NOT NULL REFERENCES risposte_nomi(id) ON DELETE CASCADE,
    username TEXT NOT NULL REFERENCES utenti(username) ON DELETE CASCADE,
    PRIMARY KEY(risposta_id, username)
);
CREATE TABLE IF NOT EXISTS valutazioni_nomi (
    stanza_codice TEXT NOT NULL REFERENCES partite_nomi(stanza_codice) ON DELETE CASCADE,
    turno INTEGER NOT NULL,
    username TEXT NOT NULL REFERENCES utenti(username) ON DELETE CASCADE,
    PRIMARY KEY(stanza_codice, turno, username)
);
