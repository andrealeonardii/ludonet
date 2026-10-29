"""Query SQL per Nomi, cose, città."""
from connessione import get_db


def partita(codice):
    row = get_db().execute('SELECT * FROM partite_nomi WHERE stanza_codice = ?', (codice,)).fetchone()
    return dict(row) if row is not None else None


def elimina(codice):
    get_db().execute('DELETE FROM partite_nomi WHERE stanza_codice = ?', (codice,))


def crea(codice, partita_id, lettera):
    elimina(codice)
    get_db().execute('INSERT INTO partite_nomi (stanza_codice, id, lettere) VALUES (?, ?, ?)',
                     (codice, partita_id, lettera))


def risposte(codice, turno):
    rows = get_db().execute(
        'SELECT * FROM risposte_nomi WHERE stanza_codice = ? AND turno = ? ORDER BY username, id',
        (codice, turno)
    ).fetchall()
    return [dict(row) for row in rows]


def inserisci_risposte(codice, username, turno, risposte):
    for categoria, testo in risposte.items():
        get_db().execute(
            'INSERT INTO risposte_nomi (stanza_codice, username, turno, categoria, testo) VALUES (?, ?, ?, ?, ?)',
            (codice, username, turno, categoria, testo)
        )


def assegna_punti(risposta_id, valida, punti):
    get_db().execute('UPDATE risposte_nomi SET valida = ?, punti = ? WHERE id = ?',
                     (int(valida), punti, risposta_id))


def conferma_valutazione(codice):
    get_db().execute('UPDATE partite_nomi SET valutato = 1 WHERE stanza_codice = ?', (codice,))


def avanza(codice, lettera):
    if lettera is None:
        get_db().execute('UPDATE partite_nomi SET finita = 1 WHERE stanza_codice = ?', (codice,))
    else:
        get_db().execute(
            'UPDATE partite_nomi SET turno = turno + 1, lettere = lettere || ?, valutato = 0, scadenza = NULL WHERE stanza_codice = ?',
            (lettera, codice)
        )


def imposta_sala(codice, in_sala):
    get_db().execute('UPDATE partite_nomi SET in_sala = ? WHERE stanza_codice = ?', (int(in_sala), codice))


def classifica(codice):
    rows = get_db().execute(
        'SELECT utenti.username, COALESCE(SUM(risposte_nomi.punti), 0) AS punti '
        'FROM utenti LEFT JOIN risposte_nomi ON risposte_nomi.username = utenti.username '
        'AND risposte_nomi.stanza_codice = utenti.stanza_codice '
        'WHERE utenti.stanza_codice = ? GROUP BY utenti.username ORDER BY punti DESC, utenti.username',
        (codice,)
    ).fetchall()
    return [dict(row) for row in rows]


def imposta_scadenza(codice, quando):
    get_db().execute('UPDATE partite_nomi SET scadenza=? WHERE stanza_codice=? AND scadenza IS NULL',
                     (quando, codice))


def bozza(codice, username, turno):
    riga = get_db().execute('SELECT nomi, cose, citta FROM bozze_nomi WHERE stanza_codice=? AND username=? AND turno=?',
                            (codice, username, turno)).fetchone()
    return dict(riga) if riga else dict(nomi='', cose='', citta='')


def salva_bozza(codice, username, turno, testi):
    get_db().execute('INSERT INTO bozze_nomi VALUES (?, ?, ?, ?, ?, ?) '
                     'ON CONFLICT(stanza_codice, username, turno) DO UPDATE SET '
                     'nomi=excluded.nomi, cose=excluded.cose, citta=excluded.citta',
                     (codice, username, turno, testi['nomi'], testi['cose'], testi['citta']))


def valutazioni(codice, turno):
    return [r['username'] for r in get_db().execute(
        'SELECT username FROM valutazioni_nomi WHERE stanza_codice=? AND turno=?', (codice, turno))]


def voti(codice, turno):
    return [dict(r) for r in get_db().execute(
        'SELECT voti_nomi.* FROM voti_nomi JOIN risposte_nomi ON risposte_nomi.id=voti_nomi.risposta_id '
        'WHERE stanza_codice=? AND turno=?', (codice, turno))]


def registra_voti(codice, turno, username, contestate):
    for risposta_id in contestate:
        get_db().execute('INSERT INTO voti_nomi VALUES (?, ?)', (risposta_id, username))
    get_db().execute('INSERT INTO valutazioni_nomi VALUES (?, ?, ?)', (codice, turno, username))
