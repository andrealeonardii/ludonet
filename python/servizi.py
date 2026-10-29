"""Regole per creare stanze e partecipare, senza SQL né richieste HTTP."""
import secrets

import repository
import repository_profili
import repository_justone
import repository_nomi
import repository_quiz
from connessione import transazione


class ErroreAccesso(ValueError):
    """Errore previsto da mostrare all'utente nel form."""


def accedi(username, azione, codice='', ospite=False):
    """Registra il partecipante e restituisce codice stanza e identificatore di accesso."""
    # Il form passa già lo username senza spazi iniziali e finali.
    lunghezza = len(username.strip())
    if lunghezza < 1 or lunghezza > 30:
        raise ErroreAccesso('Inserisci uno username da 1 a 30 caratteri.')
    if azione not in ('crea', 'entra'):
        raise ErroreAccesso('Scegli se creare una stanza o entrare.')
    # Il codice serve solo quando si entra in una stanza esistente.
    if azione == 'entra':
        if len(codice) != 6:
            raise ErroreAccesso('Il codice deve contenere esattamente 6 cifre.')
        for carattere in codice:
            if carattere not in '0123456789':
                raise ErroreAccesso('Il codice deve contenere esattamente 6 cifre.')

    # Il servizio decide i confini della transazione: stanza e admin sono un'operazione unica.
    with transazione():
        if ospite and repository_profili.trova(username):
            raise ErroreAccesso('Username registrato. Accedi con il codice personale o scegli un altro nome.')
        if repository.trova_utente(username):
            raise ErroreAccesso('Username già occupato. Scegline un altro.')
        if azione == 'entra' and not repository.stanza_esiste(codice):
            raise ErroreAccesso('Stanza non trovata. Controlla il codice.')
        if azione == 'entra':
            if any(u['is_bot'] for u in repository.partecipanti_stanza(codice)):
                raise ErroreAccesso('La stanza ha un giocatore AI. L’admin deve rimuoverlo prima di altri ingressi.')
            quiz = repository_quiz.partita(codice)
            if quiz is not None and not quiz['finita']:
                raise ErroreAccesso('Quiz in corso. Attendi la fine della partita per entrare.')
            nomi = repository_nomi.partita(codice)
            if nomi is not None and not nomi['finita']:
                raise ErroreAccesso('Partita in corso. Attendi la fine per entrare.')
            justone = repository_justone.partita(codice)
            if justone is not None and not justone['finita']:
                raise ErroreAccesso('Just One in corso. Attendi la fine per entrare.')
        if azione == 'crea':
            while True:
                numero = secrets.randbelow(1_000_000)
                codice = str(numero).zfill(6)
                if not repository.stanza_esiste(codice):
                    break
            repository.inserisci_stanza(codice)
        # Solo chi crea la stanza riceve il ruolo di admin.
        is_admin = azione == 'crea'
        accesso_id = secrets.token_hex(16)
        repository.inserisci_utente(username, codice, is_admin, accesso_id, ospite)
        # Un nuovo partecipante può rendere inadatto il gioco selezionato.
        gioco = repository.gioco_selezionato(codice)
        if gioco is not None and repository.conta_partecipanti(codice) > gioco['max_giocatori']:
            repository.imposta_gioco(codice, None)
            repository.elimina_partita(codice)
            repository_quiz.elimina(codice)
            repository_nomi.elimina(codice)
            repository_justone.elimina(codice)
    return codice, accesso_id


def esci(username, accesso_id):
    """Elimina l'utente o, se è admin, tutta la stanza. Restituisce il codice da notificare."""
    with transazione():
        utente = repository.trova_utente(username)
        if utente is None or utente['accesso_id'] != accesso_id:
            return None

        codice = utente['stanza_codice']
        if utente['is_admin']:
            # Prima i partecipanti, poi la stanza: rispettiamo la chiave esterna.
            repository.elimina_utenti_stanza(codice)
            repository.elimina_stanza(codice)
        else:
            # Just One richiede lo stesso gruppo per tutta la rotazione.
            repository_justone.elimina(codice)
            repository.elimina_utente(username)
            if repository.conta_partecipanti(codice) < 2:
                repository_quiz.elimina(codice)
                repository_nomi.elimina(codice)
    return codice


class ErroreGioco(ValueError):
    """Scelta del gioco non consentita."""


def prepara_gioco(username, accesso_id, nome):
    """Seleziona il gioco nella stessa transazione che ne avvia la partita."""
    utente = repository.trova_utente(username)
    if utente is None or utente['accesso_id'] != accesso_id or not utente['is_admin']:
        raise ErroreGioco("Solo l'admin può avviare il gioco.")
    gioco = repository.trova_gioco_per_nome(nome)
    if gioco is None:
        raise ErroreGioco('Gioco non trovato.')
    codice = utente['stanza_codice']
    totale = repository.conta_partecipanti(codice)
    minimo = 3 if nome == 'Just One' else 2
    if totale < minimo or totale > gioco['max_giocatori']:
        raise ErroreGioco(f"Servono da {minimo} a {gioco['max_giocatori']} giocatori.")
    cambia_gioco(codice, gioco['id'])


def cambia_gioco(codice, gioco_id):
    # Chiamata dentro la transazione di scelta o avvio.
    if any(u['is_bot'] for u in repository.partecipanti_stanza(codice)):
        gioco = repository.trova_gioco(gioco_id)
        if gioco is None or gioco['nome'] != 'Forza 4':
            raise ErroreGioco('Rimuovi il giocatore AI per scegliere un altro gioco.')
    precedente = repository.gioco_selezionato(codice)
    if precedente is None or precedente['id'] != gioco_id:
        repository.elimina_partita(codice)
        repository_quiz.elimina(codice)
        repository_nomi.elimina(codice)
        repository_justone.elimina(codice)
    repository.imposta_gioco(codice, gioco_id)


def scegli_gioco(username, accesso_id, gioco_id):
    with transazione():
        utente = repository.trova_utente(username)
        if utente is None or utente['accesso_id'] != accesso_id or not utente['is_admin']:
            raise ErroreGioco("Solo l'admin può scegliere il gioco.")
        gioco = repository.trova_gioco(gioco_id)
        if gioco is None:
            raise ErroreGioco('Gioco non trovato.')
        codice = utente['stanza_codice']
        if repository.conta_partecipanti(codice) > gioco['max_giocatori']:
            raise ErroreGioco('Troppi partecipanti per questo gioco.')
        cambia_gioco(codice, gioco_id)
    return codice
