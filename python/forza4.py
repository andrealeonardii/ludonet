"""Gestione di Forza 4: accesso, turni e salvataggio delle mosse."""
import secrets
import economia

from connessione import transazione
import repository
import repository_bot
from servizi import ErroreGioco, prepara_gioco
from regole_forza4 import gioca


def stato(codice):
    gioco = repository.gioco_selezionato(codice)
    return {
        'forza4_selezionato': gioco is not None and gioco['nome'] == 'Forza 4',
        'partita': repository.partita_forza4(codice),
        'numero_partecipanti': repository.conta_partecipanti(codice),
        'bot': repository_bot.trova(codice),
        'richiesta_bot': repository_bot.richiesta(codice),
    }


def verifica_utente(username, accesso_id):
    utente = repository.trova_utente(username)
    if utente is None or utente['accesso_id'] != accesso_id:
        raise ErroreGioco('Accesso non valido.')
    codice = utente['stanza_codice']
    gioco = repository.gioco_selezionato(codice)
    if gioco is None or gioco['nome'] != 'Forza 4':
        raise ErroreGioco('Forza 4 non è attivo nella stanza.')
    if repository.conta_partecipanti(codice) != 2:
        raise ErroreGioco('Servono esattamente due giocatori.')
    return utente


def avvia(username, accesso_id):
    with transazione():
        prepara_gioco(username, accesso_id, 'Forza 4')
        utente = verifica_utente(username, accesso_id)
        if not utente['is_admin']:
            raise ErroreGioco("Solo l'admin può avviare la partita.")
        codice = utente['stanza_codice']
        partita = repository.partita_forza4(codice)
        if partita is not None and partita['risultato'] == 0:
            raise ErroreGioco('La partita è già in corso.')
        if partita is None:
            partecipanti = repository.partecipanti_stanza(codice)
            rosso, giallo = username, partecipanti[1]['username']
        else:
            # Alla rivincita scambiamo i colori: il rosso gioca sempre per primo.
            rosso, giallo = partita['giallo'], partita['rosso']
        repository.crea_partita(codice, secrets.token_hex(16), rosso, giallo)
    return codice


def muovi(username, accesso_id, colonna, partita_id, griglia_precedente, token_bot=None):
    with transazione():
        utente = verifica_utente(username, accesso_id)
        codice = utente['stanza_codice']
        if utente['is_bot']:
            richiesta = repository_bot.richiesta(codice)
            if not richiesta or richiesta['token'] != token_bot or richiesta['stato'] != 'attesa':
                raise ErroreGioco('Richiesta AI annullata.')
        partita = repository.partita_forza4(codice)
        if partita is None or partita['risultato'] != 0:
            raise ErroreGioco('Nessuna partita in corso.')
        if partita['in_sala']:
            raise ErroreGioco('Attendi che l’admin riprenda il gioco.')
        # Una richiesta vecchia o duplicata non deve modificare una partita nuova.
        if partita['id'] != partita_id or partita['griglia'] != griglia_precedente:
            raise ErroreGioco('La partita è cambiata. Riprova.')
        giocatore = partita['rosso'] if partita['turno'] == 1 else partita['giallo']
        if username != giocatore:
            raise ErroreGioco('Non è il tuo turno.')
        if colonna is None or not 0 <= colonna <= 6:
            raise ErroreGioco('Colonna non valida.')
        try:
            griglia, risultato = gioca(partita['griglia'], partita['turno'], colonna)
        except ValueError as errore:
            raise ErroreGioco(str(errore)) from errore
        repository.aggiorna_partita(codice, griglia, 3 - partita['turno'], risultato)
        repository_bot.elimina(codice)
        if risultato:
            for colore, nome in [(1, partita['rosso']), (2, partita['giallo'])]:
                esito = 'pareggio' if risultato == 3 else ('vittoria' if risultato == colore else 'sconfitta')
                economia.premia(partita['id'], 'Forza 4', nome, esito)
    return codice


def cambia_vista(username, accesso_id, in_sala):
    with transazione():
        utente = verifica_utente(username, accesso_id)
        if not utente['is_admin']:
            raise ErroreGioco("Solo l'admin può tornare alla stanza o riprendere il gioco.")
        codice = utente['stanza_codice']
        if repository.partita_forza4(codice) is None:
            raise ErroreGioco('Nessuna partita da visualizzare.')
        repository.imposta_sala(codice, in_sala)
    return codice
