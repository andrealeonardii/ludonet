"""Creazione dei profili e accesso tramite codice personale."""
import secrets

from connessione import transazione
import repository_profili
import repository


def nuovo_codice():
    # Il codice è una stringa: anche gli zeri iniziali fanno parte del codice.
    for _ in range(1000):
        codice = str(secrets.randbelow(1_000_000)).zfill(6)
        if repository_profili.da_codice(codice) is None:
            return codice
    raise ValueError('Impossibile generare un codice. Riprova più tardi.')


def crea(username):
    username = username.strip()
    if not 1 <= len(username) <= 30:
        raise ValueError('Inserisci uno username da 1 a 30 caratteri.')
    with transazione():
        if repository_profili.trova(username) or repository.trova_utente(username):
            raise ValueError('Username già registrato. Accedi con il tuo codice o scegli un altro nome.')
        codice = nuovo_codice()
        repository_profili.inserisci(username, codice)
    return username, codice


def accedi(codice):
    if len(codice) != 6 or any(c not in '0123456789' for c in codice):
        raise ValueError('Codice personale non valido.')
    profilo = repository_profili.da_codice(codice)
    if profilo is None:
        raise ValueError('Codice personale non valido.')
    return profilo
