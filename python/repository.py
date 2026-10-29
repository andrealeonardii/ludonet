"""Query SQL per utenti e stanze, senza regole HTTP o gestione del form."""
from connessione import get_db


def trova_utente(username):
    row = get_db().execute(
        'SELECT * FROM utenti WHERE username = ?', (username,)
    ).fetchone()
    return dict(row) if row is not None else None


def stanza_esiste(codice):
    return get_db().execute(
        'SELECT 1 FROM stanze WHERE codice = ?', (codice,)
    ).fetchone() is not None


def inserisci_stanza(codice):
    get_db().execute('INSERT INTO stanze (codice) VALUES (?)', (codice,))


def inserisci_utente(username, codice, is_admin, accesso_id, ospite=False, bot=False):
    get_db().execute(
        'INSERT INTO utenti (username, stanza_codice, is_admin, accesso_id, is_ospite, is_bot) VALUES (?, ?, ?, ?, ?, ?)',
        (username, codice, int(is_admin), accesso_id, int(ospite), int(bot)),
    )


def partecipanti_stanza(codice):
    rows = get_db().execute(
        'SELECT username, is_admin, is_bot FROM utenti WHERE stanza_codice = ? '
        'ORDER BY is_admin DESC, username', (codice,)
    ).fetchall()
    return [dict(row) for row in rows]


def elimina_utente(username):
    get_db().execute('DELETE FROM utenti WHERE username = ?', (username,))


def elimina_utenti_stanza(codice):
    get_db().execute('DELETE FROM utenti WHERE stanza_codice = ?', (codice,))


def elimina_stanza(codice):
    get_db().execute('DELETE FROM stanze WHERE codice = ?', (codice,))


def stanze_disponibili():
    rows = get_db().execute(
        'SELECT stanze.codice, admin.username AS admin, COUNT(utenti.username) AS partecipanti '
        'FROM stanze '
        'JOIN utenti AS admin ON admin.stanza_codice = stanze.codice AND admin.is_admin = 1 '
        'LEFT JOIN utenti ON utenti.stanza_codice = stanze.codice '
        'GROUP BY stanze.codice, admin.username ORDER BY stanze.codice'
    ).fetchall()
    return [dict(row) for row in rows]


def conta_partecipanti(codice):
    row = get_db().execute(
        'SELECT COUNT(*) AS totale FROM utenti WHERE stanza_codice = ?', (codice,)
    ).fetchone()
    return row['totale']


def giochi_disponibili(codice):
    totale = conta_partecipanti(codice)
    rows = get_db().execute(
        'SELECT giochi.*, giochi.id = stanze.gioco_id AS selezionato '
        'FROM giochi JOIN stanze ON stanze.codice = ? '
        'WHERE giochi.max_giocatori >= ? ORDER BY giochi.nome', (codice, totale)
    ).fetchall()
    bot = any(u['is_bot'] for u in partecipanti_stanza(codice))
    return [dict(row) for row in rows if not bot or row['nome'] == 'Forza 4']


def trova_gioco(gioco_id):
    row = get_db().execute('SELECT * FROM giochi WHERE id = ?', (gioco_id,)).fetchone()
    return dict(row) if row is not None else None


def gioco_selezionato(codice):
    row = get_db().execute(
        'SELECT giochi.* FROM giochi JOIN stanze ON stanze.gioco_id = giochi.id '
        'WHERE stanze.codice = ?', (codice,)
    ).fetchone()
    return dict(row) if row is not None else None


def imposta_gioco(codice, gioco_id):
    get_db().execute('UPDATE stanze SET gioco_id = ? WHERE codice = ?', (gioco_id, codice))


def partita_forza4(codice):
    row = get_db().execute(
        'SELECT * FROM partite_forza4 WHERE stanza_codice = ?', (codice,)
    ).fetchone()
    return dict(row) if row is not None else None


def elimina_partita(codice):
    get_db().execute('DELETE FROM partite_forza4 WHERE stanza_codice = ?', (codice,))


def crea_partita(codice, partita_id, rosso, giallo):
    elimina_partita(codice)
    get_db().execute(
        'INSERT INTO partite_forza4 (stanza_codice, id, rosso, giallo, griglia, turno, risultato) '
        'VALUES (?, ?, ?, ?, ?, 1, 0)',
        (codice, partita_id, rosso, giallo, '0' * 42)
    )


def aggiorna_partita(codice, griglia, turno, risultato):
    get_db().execute(
        'UPDATE partite_forza4 SET griglia = ?, turno = ?, risultato = ? WHERE stanza_codice = ?',
        (griglia, turno, risultato, codice)
    )


def imposta_sala(codice, in_sala):
    get_db().execute('UPDATE partite_forza4 SET in_sala = ? WHERE stanza_codice = ?',
                     (int(in_sala), codice))
    if in_sala:
        get_db().execute('DELETE FROM richieste_bot WHERE stanza_codice = ?', (codice,))


def trova_gioco_per_nome(nome):
    row = get_db().execute('SELECT * FROM giochi WHERE nome = ?', (nome,)).fetchone()
    return dict(row) if row is not None else None
