"""Query SQL dei profili permanenti."""
from connessione import get_db


def trova(username):
    riga = get_db().execute('SELECT username FROM profili WHERE username = ?', (username,)).fetchone()
    return dict(riga) if riga else None


def da_codice(codice):
    riga = get_db().execute(
        'SELECT username FROM profili WHERE codice_personale = ?', (codice,)
    ).fetchone()
    return dict(riga) if riga else None


def inserisci(username, codice):
    get_db().execute(
        'INSERT INTO profili (username, codice_personale) VALUES (?, ?)', (username, codice)
    )
