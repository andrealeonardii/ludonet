"""Query SQL dell'avatar; il servizio gestisce le transazioni."""
from connessione import get_db


def leggi(username, ospite=False):
    tabella = 'avatar_ospiti' if ospite else 'avatar'
    riga = get_db().execute('SELECT testa, corpo, piedi FROM ' + tabella + ' WHERE username = ?', (username,)).fetchone()
    return dict(riga) if riga else None


def salva(username, parti, ospite=False):
    tabella = 'avatar_ospiti' if ospite else 'avatar'
    get_db().execute(
        'INSERT INTO ' + tabella + ' (username, testa, corpo, piedi) VALUES (?, ?, ?, ?) '
        'ON CONFLICT(username) DO UPDATE SET testa=excluded.testa, corpo=excluded.corpo, piedi=excluded.piedi',
        (username, parti['testa'], parti['corpo'], parti['piedi'])
    )
