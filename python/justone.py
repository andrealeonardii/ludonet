"""Just One cooperativo: una manche a testa, una sola parola per indizio."""
import secrets
import economia
import unicodedata

from connessione import transazione
import repository
import repository_justone as dati
from servizi import ErroreGioco, prepara_gioco


def normalizza(testo):
    testo = unicodedata.normalize('NFD', testo.strip().casefold())
    return ''.join(c for c in testo if not unicodedata.combining(c))


def indizi_unici(indizi):
    frequenze = {}
    for indizio in indizi:
        parola = normalizza(indizio['testo'])
        frequenze[parola] = frequenze.get(parola, 0) + 1
    return sorted(i['testo'] for i in indizi if frequenze[normalizza(i['testo'])] == 1)


def stato(utente):
    codice = utente['stanza_codice']
    partita = dati.partita(codice)
    totale = repository.conta_partecipanti(codice)
    contesto = dict(justone_selezionato=True, partita=partita, numero_partecipanti=totale)
    if partita is not None:
        manche = dati.manche(codice, partita['turno'])
        indizi = dati.indizi(codice, partita['turno'])
        pronti = len(indizi) == totale - 1
        sei_indovino = utente['username'] == manche['indovina']
        conclusa = manche['tentativo'] is not None
        # La parola segreta e gli indizi eliminati non entrano nel template dell'indovino.
        contesto.update(
            numero_manche=partita['turno'] if partita['finita'] else totale,
            indovino=manche['indovina'], sei_indovino=sei_indovino,
            parola=manche['parola'] if not sei_indovino or conclusa else None,
            ha_inviato=any(i['username'] == utente['username'] for i in indizi),
            indizi_ricevuti=len(indizi), tutti_pronti=pronti,
            indizi_visibili=indizi_unici(indizi) if pronti else [],
            conclusa=conclusa, tentativo=manche['tentativo'], riuscito=manche['riuscito'],
            punteggio=dati.punteggio(codice)
        )
    return contesto


def verifica_utente(username, accesso_id, admin=False):
    utente = repository.trova_utente(username)
    if utente is None or utente['accesso_id'] != accesso_id:
        raise ErroreGioco('Accesso non valido.')
    if admin and not utente['is_admin']:
        raise ErroreGioco('Questa azione è riservata all’admin.')
    codice = utente['stanza_codice']
    gioco = repository.gioco_selezionato(codice)
    if gioco is None or gioco['nome'] != 'Just One':
        raise ErroreGioco('Just One non è attivo nella stanza.')
    if not 3 <= repository.conta_partecipanti(codice) <= gioco['max_giocatori']:
        raise ErroreGioco('Servono da 3 a 8 giocatori.')
    return codice


def verifica_turno(codice, partita_id, turno):
    partita = dati.partita(codice)
    if partita is None or partita['id'] != partita_id or partita['turno'] != turno:
        raise ErroreGioco('La manche è cambiata. Riprova.')
    if partita['finita'] or partita['in_sala']:
        raise ErroreGioco('La partita è terminata o è in pausa.')
    return dati.manche(codice, turno)


def nuova_manche(codice, turno):
    partecipanti = repository.partecipanti_stanza(codice)
    parole = dati.parole_disponibili(codice)
    if not parole:
        raise ErroreGioco('Non ci sono abbastanza parole nel database.')
    dati.crea_manche(codice, turno, secrets.choice(parole), partecipanti[turno - 1]['username'])


def avvia(username, accesso_id):
    with transazione():
        prepara_gioco(username, accesso_id, 'Just One')
        codice = verifica_utente(username, accesso_id, admin=True)
        partita = dati.partita(codice)
        if partita is not None and not partita['finita']:
            raise ErroreGioco('La partita è già in corso.')
        dati.crea(codice, secrets.token_hex(16))
        nuova_manche(codice, 1)
    return codice


def invia_indizio(username, accesso_id, partita_id, turno, testo):
    with transazione():
        codice = verifica_utente(username, accesso_id)
        manche = verifica_turno(codice, partita_id, turno)
        if username == manche['indovina'] or manche['tentativo'] is not None:
            raise ErroreGioco('Non puoi inviare un indizio in questa manche.')
        if any(i['username'] == username for i in dati.indizi(codice, turno)):
            raise ErroreGioco('Hai già inviato il tuo indizio.')
        testo = testo.strip()
        if not 1 <= len(testo) <= 30 or not testo.isalpha():
            raise ErroreGioco('Scrivi una sola parola, composta da massimo 30 lettere.')
        if normalizza(testo) == normalizza(manche['parola']):
            raise ErroreGioco('L’indizio non può essere la parola da indovinare.')
        dati.inserisci_indizio(codice, turno, username, testo)
    return codice


def indovina(username, accesso_id, partita_id, turno, testo):
    with transazione():
        codice = verifica_utente(username, accesso_id)
        manche = verifica_turno(codice, partita_id, turno)
        if username != manche['indovina'] or manche['tentativo'] is not None:
            raise ErroreGioco('Non puoi rispondere in questa manche.')
        if len(dati.indizi(codice, turno)) != repository.conta_partecipanti(codice) - 1:
            raise ErroreGioco('Attendi gli indizi di tutti.')
        testo = testo.strip()
        if len(testo) > 60:
            raise ErroreGioco('La risposta può contenere al massimo 60 caratteri.')
        # Una risposta vuota significa passare: nessun punto, ma la manche si conclude.
        dati.salva_tentativo(codice, turno, testo, normalizza(testo) == normalizza(manche['parola']))
    return codice


def prossima(username, accesso_id, partita_id, turno):
    with transazione():
        codice = verifica_utente(username, accesso_id, admin=True)
        manche = verifica_turno(codice, partita_id, turno)
        if manche['tentativo'] is None:
            raise ErroreGioco('Attendi che il giocatore risponda o passi.')
        if turno == repository.conta_partecipanti(codice):
            dati.termina(codice)
            for partecipante in repository.partecipanti_stanza(codice):
                economia.premia(partita_id, 'Just One', partecipante['username'],
                                'cooperativo', dati.punteggio(codice))
        else:
            nuova_manche(codice, turno + 1)
    return codice


def cambia_vista(username, accesso_id, in_sala):
    with transazione():
        codice = verifica_utente(username, accesso_id, admin=True)
        if dati.partita(codice) is None:
            raise ErroreGioco('Nessuna partita da visualizzare.')
        dati.imposta_sala(codice, in_sala)
    return codice
