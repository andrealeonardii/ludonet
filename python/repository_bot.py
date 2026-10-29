"""Query del giocatore AI e della richiesta attualmente in corso."""
from connessione import get_db


def trova(codice):
    riga = get_db().execute('SELECT * FROM utenti WHERE stanza_codice = ? AND is_bot = 1',
                            (codice,)).fetchone()
    return dict(riga) if riga else None


def richiesta(codice):
    riga = get_db().execute('SELECT * FROM richieste_bot WHERE stanza_codice = ?', (codice,)).fetchone()
    return dict(riga) if riga else None


def avvia(codice, token):
    get_db().execute('INSERT INTO richieste_bot (stanza_codice, token, stato) VALUES (?, ?, ?) '
                     'ON CONFLICT(stanza_codice) DO UPDATE SET token = excluded.token, '
                     "stato = 'attesa', messaggio = ''", (codice, token, 'attesa'))


def errore(codice, token, messaggio):
    get_db().execute("UPDATE richieste_bot SET stato = 'errore', messaggio = ? "
                     'WHERE stanza_codice = ? AND token = ?', (messaggio, codice, token))


def elimina(codice):
    get_db().execute('DELETE FROM richieste_bot WHERE stanza_codice = ?', (codice,))
