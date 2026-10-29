"""Query SQL di Just One."""
from connessione import get_db


def partita(codice):
    row = get_db().execute('SELECT * FROM partite_justone WHERE stanza_codice = ?', (codice,)).fetchone()
    return dict(row) if row is not None else None


def elimina(codice):
    get_db().execute('DELETE FROM partite_justone WHERE stanza_codice = ?', (codice,))


def crea(codice, partita_id):
    elimina(codice)
    get_db().execute('INSERT INTO partite_justone (stanza_codice, id) VALUES (?, ?)', (codice, partita_id))


def parole_disponibili(codice):
    rows = get_db().execute(
        'SELECT id FROM parole_justone WHERE id NOT IN '
        '(SELECT parola_id FROM manche_justone WHERE stanza_codice = ?)', (codice,)
    ).fetchall()
    return [row['id'] for row in rows]


def crea_manche(codice, turno, parola_id, username):
    get_db().execute('INSERT INTO manche_justone (stanza_codice, turno, parola_id, indovina) VALUES (?, ?, ?, ?)',
                     (codice, turno, parola_id, username))
    get_db().execute('UPDATE partite_justone SET turno = ? WHERE stanza_codice = ?', (turno, codice))


def manche(codice, turno):
    row = get_db().execute(
        'SELECT manche_justone.*, parole_justone.testo AS parola FROM manche_justone '
        'JOIN parole_justone ON parole_justone.id = manche_justone.parola_id '
        'WHERE stanza_codice = ? AND turno = ?', (codice, turno)
    ).fetchone()
    return dict(row) if row is not None else None


def indizi(codice, turno):
    rows = get_db().execute('SELECT username, testo FROM indizi_justone WHERE stanza_codice = ? AND turno = ?',
                           (codice, turno)).fetchall()
    return [dict(row) for row in rows]


def inserisci_indizio(codice, turno, username, testo):
    get_db().execute('INSERT INTO indizi_justone VALUES (?, ?, ?, ?)', (codice, turno, username, testo))


def salva_tentativo(codice, turno, tentativo, riuscito):
    get_db().execute('UPDATE manche_justone SET tentativo = ?, riuscito = ? WHERE stanza_codice = ? AND turno = ?',
                     (tentativo, int(riuscito), codice, turno))


def punteggio(codice):
    row = get_db().execute('SELECT COALESCE(SUM(riuscito), 0) AS punti FROM manche_justone WHERE stanza_codice = ?',
                          (codice,)).fetchone()
    return row['punti']


def termina(codice):
    get_db().execute('UPDATE partite_justone SET finita = 1 WHERE stanza_codice = ?', (codice,))


def imposta_sala(codice, in_sala):
    get_db().execute('UPDATE partite_justone SET in_sala = ? WHERE stanza_codice = ?', (int(in_sala), codice))
