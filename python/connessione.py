import sqlite3
from flask import current_app, g


def get_db():
    # Apre la connessione solo se questa richiesta non ne ha già una.
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        # Permette di leggere le colonne per nome, per esempio riga['username'].
        g.db.row_factory = sqlite3.Row
        # Fa rispettare i collegamenti tra utenti e stanze.
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db


def close_db(error=None):
    # Flask passa l'eventuale errore e chiama questa funzione anche se la richiesta fallisce.
    if 'db' in g:
        g.db.close()
        del g.db


def init_db():
    economia_nuova = get_db().execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='acquisti'"
    ).fetchone() is None
    # root_path è la cartella dell'app, indipendentemente da dove viene avviata.
    with open(current_app.root_path + '/schema.sql', encoding='utf-8') as file:
        get_db().executescript(file.read())

    # Aggiorna anche il database delle versioni precedenti, senza perdere utenti.
    db = get_db()
    colonne = db.execute('PRAGMA table_info(utenti)').fetchall()
    nomi = [colonna['name'] for colonna in colonne]
    if 'accesso_id' not in nomi:
        with db:
            db.execute("ALTER TABLE utenti ADD COLUMN accesso_id TEXT NOT NULL DEFAULT ''")
            # Le vecchie sessioni contenevano solo lo username.
            db.execute('UPDATE utenti SET accesso_id = username')

    if 'is_ospite' not in nomi:
        with db:
            db.execute('ALTER TABLE utenti ADD COLUMN is_ospite INTEGER NOT NULL DEFAULT 0')

    if 'is_bot' not in nomi:
        with db:
            db.execute('ALTER TABLE utenti ADD COLUMN is_bot INTEGER NOT NULL DEFAULT 0')

    # Dopo un riavvio i vecchi thread non esistono più: l'admin può riprovare.
    with db:
        db.execute("UPDATE richieste_bot SET stato = 'errore', messaggio = 'Server riavviato. Premi Riprova.' "
                   "WHERE stato = 'attesa'")

    colonne = db.execute('PRAGMA table_info(stanze)').fetchall()
    nomi = [colonna['name'] for colonna in colonne]
    if 'gioco_id' not in nomi:
        with db:
            db.execute('ALTER TABLE stanze ADD COLUMN gioco_id INTEGER REFERENCES giochi(id)')

    colonne = db.execute('PRAGMA table_info(partite_forza4)').fetchall()
    if 'in_sala' not in [colonna['name'] for colonna in colonne]:
        with db:
            db.execute('ALTER TABLE partite_forza4 ADD COLUMN in_sala INTEGER NOT NULL DEFAULT 0 CHECK (in_sala IN (0, 1))')

    colonne = db.execute('PRAGMA table_info(partite_nomi)').fetchall()
    if 'scadenza' not in [colonna['name'] for colonna in colonne]:
        with db:
            db.execute('ALTER TABLE partite_nomi ADD COLUMN scadenza REAL')

    with transazione():
        # All'introduzione del negozio conserviamo i pezzi già indossati.
        if economia_nuova:
            for parte in ('testa', 'corpo', 'piedi'):
                db.execute(
                    'INSERT OR IGNORE INTO acquisti (username, cosmetico_id) '
                    'SELECT avatar.username, cosmetici.id FROM avatar JOIN cosmetici '
                    'ON cosmetici.parte = ? AND cosmetici.immagine = avatar.' + parte,
                    (parte,)
                )


def transazione():
    db = get_db()
    # Riserva la scrittura prima di controllare username e codice stanza.
    db.execute('BEGIN IMMEDIATE')
    # Usata con "with", la connessione conferma le modifiche o le annulla se c'è un errore.
    return db


def init_app(app):
    app.teardown_appcontext(close_db)
    # Rende disponibili current_app e g durante l'inizializzazione.
    with app.app_context():
        init_db()
