"""Query per monete, catalogo, acquisti e premi già assegnati."""
from connessione import get_db


def saldo(username):
    riga = get_db().execute('SELECT saldo FROM portafogli WHERE username = ?', (username,)).fetchone()
    return riga['saldo'] if riga else 0


def imposta_saldo(username, valore):
    get_db().execute('INSERT INTO portafogli VALUES (?, ?) '
                     'ON CONFLICT(username) DO UPDATE SET saldo=excluded.saldo', (username, valore))


def catalogo(username):
    righe = get_db().execute(
        'SELECT cosmetici.*, (prezzo = 0 OR acquisti.username IS NOT NULL) AS posseduto '
        'FROM cosmetici LEFT JOIN acquisti ON acquisti.cosmetico_id = cosmetici.id AND acquisti.username = ? '
        'ORDER BY prezzo, nome', (username,)
    ).fetchall()
    return [dict(riga) for riga in righe]


def registra_acquisto(username, cosmetico):
    get_db().execute('INSERT INTO acquisti VALUES (?, ?)', (username, cosmetico))


def registra_premio(partita, gioco, username, monete):
    risultato = get_db().execute('INSERT OR IGNORE INTO premi VALUES (?, ?, ?, ?)',
                                 (partita, gioco, username, monete))
    return risultato.rowcount == 1


def premi_partita(partita, gioco, username):
    riga = get_db().execute('SELECT monete FROM premi WHERE partita_id=? AND gioco=? AND username=?',
                            (partita, gioco, username)).fetchone()
    return riga['monete'] if riga else None
