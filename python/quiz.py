"""Regole del Quiz: avvio, risposte, punteggi e avanzamento delle domande."""
import secrets
import economia

from connessione import transazione
import repository
import repository_quiz as dati
from servizi import ErroreGioco, prepara_gioco


def stato(utente):
    codice = utente['stanza_codice']
    partita = dati.partita(codice)
    totale = repository.conta_partecipanti(codice)
    contesto = dict(quiz_selezionato=True, partita=partita, numero_partecipanti=totale)
    if partita is not None:
        domanda = dati.domanda(partita['domanda'])
        risposte = dati.risposte(codice, partita['domanda'])
        contesto.update(
            domanda=domanda,
            opzioni=[domanda['opzione_a'], domanda['opzione_b'], domanda['opzione_c'], domanda['opzione_d']],
            ha_risposto=any(r['username'] == utente['username'] for r in risposte),
            risposte_ricevute=len(risposte), tutti_pronti=len(risposte) == totale,
            classifica=dati.classifica(codice)
        )
    return contesto


def verifica_utente(username, accesso_id, admin=False):
    utente = repository.trova_utente(username)
    if utente is None or utente['accesso_id'] != accesso_id:
        raise ErroreGioco('Accesso non valido.')
    if admin and not utente['is_admin']:
        raise ErroreGioco("Questa azione è riservata all’admin.")
    codice = utente['stanza_codice']
    gioco = repository.gioco_selezionato(codice)
    if gioco is None or gioco['nome'] != 'Quiz':
        raise ErroreGioco('Quiz non è attivo nella stanza.')
    if not 2 <= repository.conta_partecipanti(codice) <= gioco['max_giocatori']:
        raise ErroreGioco('Servono da 2 a 8 giocatori.')
    return codice


def verifica_domanda(codice, partita_id, numero):
    partita = dati.partita(codice)
    if partita is None or partita['id'] != partita_id or partita['domanda'] != numero:
        raise ErroreGioco('La domanda è cambiata. Riprova.')
    if partita['finita'] or partita['in_sala']:
        raise ErroreGioco('Il quiz è terminato o è in pausa.')
    return partita


def avvia(username, accesso_id):
    with transazione():
        prepara_gioco(username, accesso_id, 'Quiz')
        codice = verifica_utente(username, accesso_id, admin=True)
        partita = dati.partita(codice)
        if partita is not None and not partita['finita']:
            raise ErroreGioco('Il quiz è già in corso.')
        dati.crea(codice, secrets.token_hex(16))
    return codice


def rispondi(username, accesso_id, partita_id, numero, risposta):
    with transazione():
        codice = verifica_utente(username, accesso_id)
        verifica_domanda(codice, partita_id, numero)
        if risposta is None or not 0 <= risposta <= 3:
            raise ErroreGioco('Scegli una delle quattro risposte.')
        if any(r['username'] == username for r in dati.risposte(codice, numero)):
            raise ErroreGioco('Hai già risposto a questa domanda.')
        domanda = dati.domanda(numero)
        punti = 1 if risposta == domanda['corretta'] else 0
        dati.inserisci_risposta(codice, username, numero, risposta, punti)
    return codice


def prossima(username, accesso_id, partita_id, numero):
    with transazione():
        codice = verifica_utente(username, accesso_id, admin=True)
        verifica_domanda(codice, partita_id, numero)
        if len(dati.risposte(codice, numero)) != repository.conta_partecipanti(codice):
            raise ErroreGioco('Attendi le risposte di tutti.')
        dati.avanza(codice, numero)
        if numero == 5:
            economia.premia_classifica(partita_id, 'Quiz', dati.classifica(codice))
    return codice


def cambia_vista(username, accesso_id, in_sala):
    with transazione():
        codice = verifica_utente(username, accesso_id, admin=True)
        if dati.partita(codice) is None:
            raise ErroreGioco('Nessun quiz da visualizzare.')
        dati.imposta_sala(codice, in_sala)
    return codice
