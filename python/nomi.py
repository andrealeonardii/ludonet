"""Regole di Nomi, cose, città: tre manche, timer e voti dei partecipanti."""
import secrets
import time
import sincronizzazione
import economia
import unicodedata

from connessione import transazione
import repository
import repository_nomi as dati
from servizi import ErroreGioco, prepara_gioco

CATEGORIE = {'nomi': 'Nomi', 'cose': 'Cose', 'citta': 'Città'}
LETTERE = 'ABCDEFGILMNOPRSTV'


def normalizza(testo):
    # Ignora maiuscole, accenti e spazi ripetuti nel confronto tra risposte.
    testo = unicodedata.normalize('NFD', testo.casefold())
    testo = ''.join(c for c in testo if not unicodedata.combining(c))
    return ' '.join(testo.split())


def lettera_casuale(usate=''):
    return secrets.choice([lettera for lettera in LETTERE if lettera not in usate])


def aggiorna_scadenza(codice):
    """Blocca le bozze scadute, anche dopo un riavvio o una riconnessione."""
    cambiato = False
    with transazione():
        partita = dati.partita(codice)
        if partita and not partita['finita'] and not partita['valutato']:
            turno = partita['turno']
            ricevute = {r['username'] for r in dati.risposte(codice, turno)}
            if partita['scadenza'] is not None and time.time() >= partita['scadenza']:
                for p in repository.partecipanti_stanza(codice):
                    if p['username'] not in ricevute:
                        dati.inserisci_risposte(codice, p['username'], turno, dati.bozza(codice, p['username'], turno))
                        cambiato = True
            # Se qualcuno esce, non aspettiamo più la sua conferma dei voti.
            if len(dati.valutazioni(codice, turno)) == repository.conta_partecipanti(codice):
                calcola_punti(codice, partita)
                cambiato = True
    if cambiato:
        sincronizzazione.notifica_stanza(codice)


def stato(utente):
    codice = utente['stanza_codice']
    aggiorna_scadenza(codice)
    partita = dati.partita(codice)
    totale = repository.conta_partecipanti(codice)
    contesto = dict(nomi_selezionato=True, partita=partita, numero_partecipanti=totale, categorie=CATEGORIE)
    if partita is not None:
        risposte = dati.risposte(codice, partita['turno'])
        ricevute = {r['username'] for r in risposte}
        lettera = partita['lettere'][-1]
        voti = dati.voti(codice, partita['turno'])
        for risposta in risposte:
            risposta['ammissibile'] = normalizza(risposta['testo']).startswith(lettera.lower())
            risposta['contrari'] = sum(v['risposta_id'] == risposta['id'] for v in voti)
        confermati = dati.valutazioni(codice, partita['turno'])
        contesto.update(
            lettera=lettera, ha_risposto=utente['username'] in ricevute,
            risposte_ricevute=len(ricevute), tutti_pronti=len(ricevute) == totale,
            risposte=risposte if len(ricevute) == totale or partita['valutato'] else [],
            classifica=dati.classifica(codice), ha_votato=utente['username'] in confermati,
            votanti=len(confermati), soglia_voti=(totale - 1) // 2 + 1,
            bozza=dati.bozza(codice, utente['username'], partita['turno']),
            secondi_rimasti=max(0, partita['scadenza'] - time.time()) if partita['scadenza'] else None
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
    if gioco is None or gioco['nome'] != 'Nomi, cose, città':
        raise ErroreGioco('Nomi, cose, città non è attivo nella stanza.')
    if not 2 <= repository.conta_partecipanti(codice) <= gioco['max_giocatori']:
        raise ErroreGioco('Servono da 2 a 8 giocatori.')
    return codice


def verifica_turno(codice, partita_id, turno):
    partita = dati.partita(codice)
    if partita is None or partita['id'] != partita_id or partita['turno'] != turno:
        raise ErroreGioco('La manche è cambiata. Riprova.')
    if partita['finita'] or partita['in_sala']:
        raise ErroreGioco('La partita è terminata o è in pausa.')
    return partita


def avvia(username, accesso_id):
    with transazione():
        prepara_gioco(username, accesso_id, 'Nomi, cose, città')
        codice = verifica_utente(username, accesso_id, admin=True)
        partita = dati.partita(codice)
        if partita is not None and not partita['finita']:
            raise ErroreGioco('La partita è già in corso.')
        dati.crea(codice, secrets.token_hex(16), lettera_casuale())
    return codice


def testi_validati(risposte):
    testi = {categoria: risposte.get(categoria, '').strip() for categoria in CATEGORIE}
    if any(len(testo) > 60 for testo in testi.values()):
        raise ErroreGioco('Ogni risposta può contenere al massimo 60 caratteri.')
    return testi


def rispondi(username, accesso_id, partita_id, turno, risposte, bozza=False):
    codice = verifica_utente(username, accesso_id)
    aggiorna_scadenza(codice)
    with transazione():
        codice = verifica_utente(username, accesso_id)
        partita = verifica_turno(codice, partita_id, turno)
        if partita['valutato'] or any(r['username'] == username for r in dati.risposte(codice, turno)):
            raise ErroreGioco('Risposte già inviate o tempo scaduto.')
        if partita['scadenza'] is not None and time.time() >= partita['scadenza']:
            raise ErroreGioco('Tempo scaduto.')
        testi = testi_validati(risposte)
        if bozza:
            dati.salva_bozza(codice, username, turno, testi)
        else:
            dati.inserisci_risposte(codice, username, turno, testi)
            dati.imposta_scadenza(codice, time.time() + 5)
    return codice


def calcola_punti(codice, partita):
    risposte = dati.risposte(codice, partita['turno'])
    voti = dati.voti(codice, partita['turno'])
    soglia = (repository.conta_partecipanti(codice) - 1) // 2 + 1
    valide = set()
    frequenze = {}
    for risposta in risposte:
        testo = normalizza(risposta['testo'])
        contrari = sum(v['risposta_id'] == risposta['id'] for v in voti)
        if testo.startswith(partita['lettere'][-1].lower()) and contrari < soglia:
            valide.add(risposta['id'])
            chiave = (risposta['categoria'], testo)
            frequenze[chiave] = frequenze.get(chiave, 0) + 1
    for risposta in risposte:
        valida = risposta['id'] in valide
        punti = 0
        if valida:
            chiave = (risposta['categoria'], normalizza(risposta['testo']))
            punti = 5 if frequenze[chiave] >= 2 else 10
        dati.assegna_punti(risposta['id'], valida, punti)
    dati.conferma_valutazione(codice)


def valuta(username, accesso_id, partita_id, turno, contestate):
    codice = verifica_utente(username, accesso_id)
    aggiorna_scadenza(codice)
    with transazione():
        codice = verifica_utente(username, accesso_id)
        partita = verifica_turno(codice, partita_id, turno)
        if partita['valutato'] or username in dati.valutazioni(codice, turno):
            raise ErroreGioco('Hai già confermato i voti.')
        risposte = dati.risposte(codice, turno)
        if len({r['username'] for r in risposte}) != repository.conta_partecipanti(codice):
            raise ErroreGioco('Attendi la fine delle risposte.')
        contestate = set(contestate)
        consentite = {str(r['id']) for r in risposte if r['username'] != username
                      and normalizza(r['testo']).startswith(partita['lettere'][-1].lower())}
        if not contestate <= consentite:
            raise ErroreGioco('Puoi contestare solo le risposte valide degli avversari di questa manche.')
        dati.registra_voti(codice, turno, username, contestate)
        if len(dati.valutazioni(codice, turno)) == repository.conta_partecipanti(codice):
            calcola_punti(codice, partita)
    return codice


def prossima(username, accesso_id, partita_id, turno):
    with transazione():
        codice = verifica_utente(username, accesso_id, admin=True)
        partita = verifica_turno(codice, partita_id, turno)
        if not partita['valutato']:
            raise ErroreGioco('Attendi che tutti confermino i voti.')
        lettera = None if turno == 3 else lettera_casuale(partita['lettere'])
        dati.avanza(codice, lettera)
        if turno == 3:
            economia.premia_classifica(partita_id, 'Nomi, cose, città', dati.classifica(codice))
    return codice


def cambia_vista(username, accesso_id, in_sala):
    with transazione():
        codice = verifica_utente(username, accesso_id, admin=True)
        if dati.partita(codice) is None:
            raise ErroreGioco('Nessuna partita da visualizzare.')
        dati.imposta_sala(codice, in_sala)
    return codice
