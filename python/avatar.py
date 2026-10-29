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
