"""Query SQL del Quiz, separate dalle regole del gioco."""
from connessione import get_db


def partita(codice):
    row = get_db().execute('SELECT * FROM partite_quiz WHERE stanza_codice = ?', (codice,)).fetchone()
    return dict(row) if row is not None else None


def elimina(codice):
    get_db().execute('DELETE FROM partite_quiz WHERE stanza_codice = ?', (codice,))


def crea(codice, partita_id):
    elimina(codice)
    get_db().execute('INSERT INTO partite_quiz (stanza_codice, id) VALUES (?, ?)', (codice, partita_id))


def domanda(numero):
    row = get_db().execute('SELECT * FROM domande_quiz WHERE id = ?', (numero,)).fetchone()
    return dict(row)


def risposte(codice, numero):
    rows = get_db().execute(
        'SELECT username, risposta, punti FROM risposte_quiz WHERE stanza_codice = ? AND domanda = ?',
        (codice, numero)
    ).fetchall()
    return [dict(row) for row in rows]


def inserisci_risposta(codice, username, numero, risposta, punti):
    get_db().execute('INSERT INTO risposte_quiz VALUES (?, ?, ?, ?, ?)',
                     (codice, username, numero, risposta, punti))


def avanza(codice, numero):
    if numero == 5:
        get_db().execute('UPDATE partite_quiz SET finita = 1 WHERE stanza_codice = ?', (codice,))
    else:
        get_db().execute('UPDATE partite_quiz SET domanda = domanda + 1 WHERE stanza_codice = ?', (codice,))


def imposta_sala(codice, in_sala):
    get_db().execute('UPDATE partite_quiz SET in_sala = ? WHERE stanza_codice = ?', (int(in_sala), codice))


def classifica(codice):
    rows = get_db().execute(
        'SELECT utenti.username, COALESCE(SUM(risposte_quiz.punti), 0) AS punti '
        'FROM utenti LEFT JOIN risposte_quiz ON risposte_quiz.username = utenti.username '
        'AND risposte_quiz.stanza_codice = utenti.stanza_codice '
        'WHERE utenti.stanza_codice = ? GROUP BY utenti.username ORDER BY punti DESC, utenti.username',
        (codice,)
    ).fetchall()
    return [dict(row) for row in rows]
