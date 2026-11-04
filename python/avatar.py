"""Catalogo e scelta delle tre parti dell'avatar."""
import secrets

from connessione import transazione
import repository
import repository_avatar
import repository_economia

def catalogo(username):
    parti = {'testa': [], 'corpo': [], 'piedi': []}
    for articolo in repository_economia.catalogo(username):
        if articolo['posseduto']:
            parti[articolo['parte']].append(articolo['immagine'])
    return parti


def verifica(utente):
    attuale = repository.trova_utente(utente['username'])
    if attuale is None or attuale['accesso_id'] != utente['accesso_id']:
        raise ValueError('Accesso scaduto.')


def _carica(username, ospite=False):
    parti = repository_avatar.leggi(username, ospite)
    opzioni = catalogo(username)
    if parti is None or any(parti[c] not in opzioni[c] for c in opzioni):
        parti = dict(testa=secrets.choice(['ragazzo', 'ragazza']),
                     corpo='felpa-arancione', piedi='jeans-blu')
        repository_avatar.salva(username, parti, ospite)
    return parti


def carica(utente):
    with transazione():
        verifica(utente)
        return _carica(utente['username'], utente['is_ospite'])


def carica_profilo(username):
    """Carica l'avatar permanente anche fuori da una stanza."""
    with transazione():
        return _carica(username)


def giocatori_forza4(utente, partita):
    """Ordina gli avatar del duello dal punto di vista del giocatore corrente."""
    nomi = [utente['username']]
    nomi.extend(nome for nome in (partita['rosso'], partita['giallo']) if nome != utente['username'])
    giocatori = []
    for nome in nomi:
        partecipante = repository.trova_utente(nome)
        if partecipante is None or partecipante['stanza_codice'] != utente['stanza_codice']:
            continue
        robot = bool(partecipante['is_bot'])
        if robot:
            parti = dict(testa='robot', corpo='robot', piedi='robot')
        else:
            parti = repository_avatar.leggi(nome, partecipante['is_ospite']) or carica(partecipante)
        colore = 1 if nome == partita['rosso'] else 2
        giocatori.append(dict(username=nome, nome='NickBot AI' if robot else nome,
                              avatar=parti, colore=colore, is_bot=robot,
                              turno=partita['risultato'] == 0 and partita['turno'] == colore))
    return giocatori


def giocatori_multigioco(utente):
    """Mostra il giocatore corrente prima degli altri partecipanti della stanza."""
    partecipanti = repository.partecipanti_stanza(utente['stanza_codice'])
    partecipanti.sort(key=lambda partecipante: partecipante['username'] != utente['username'])
    giocatori = []
    for partecipante in partecipanti:
        nome = partecipante['username']
        attuale = repository.trova_utente(nome)
        if attuale is None:
            continue
        parti = repository_avatar.leggi(nome, attuale['is_ospite']) or carica(attuale)
        giocatori.append(dict(username=nome, nome=nome, avatar=parti, colore=None, is_bot=False))
    return giocatori


def _salva(username, parti, ospite=False):
    for categoria, opzioni in catalogo(username).items():
        if parti.get(categoria) not in opzioni:
            raise ValueError('Devi prima acquistare questo oggetto premendo il lucchetto.')
    repository_avatar.salva(username, parti, ospite)


def salva(utente, parti):
    with transazione():
        verifica(utente)
        _salva(utente['username'], parti, utente['is_ospite'])


def salva_profilo(username, parti):
    """Salva l'avatar permanente dalla home autenticata."""
    with transazione():
        _salva(username, parti)
