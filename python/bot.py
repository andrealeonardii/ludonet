"""Partecipante AI: Python gestisce la stanza, C++ esegue la rete neurale locale."""
import os
from pathlib import Path
import secrets
import subprocess
import threading

from flask import current_app
from connessione import transazione
import forza4
import repository
import repository_bot as dati
import repository_profili
import servizi
import sincronizzazione


def configurazione():
    predefinito = Path(current_app.root_path).parent / 'modelli/forza4/pesi.txt'
    percorso = Path(current_app.config.get('BOT_PESI', predefinito))
    if not percorso.is_file():
        raise servizi.ErroreGioco('Mancano i pesi della rete Forza 4.')
    return percorso


def verifica_admin(username, accesso_id):
    utente = repository.trova_utente(username)
    if not utente or utente['accesso_id'] != accesso_id or not utente['is_admin']:
        raise servizi.ErroreGioco('Solo l’admin può gestire il giocatore AI.')
    return utente['stanza_codice']


def gestisci(username, accesso_id, azione):
    with transazione():
        codice = verifica_admin(username, accesso_id)
        bot = dati.trova(codice)
        if azione == 'aggiungi':
            configurazione()
            if repository.conta_partecipanti(codice) != 1:
                raise servizi.ErroreGioco('Puoi aggiungere NickBot quando sei solo nella stanza.')
            while True:
                nome = 'NickBot-' + secrets.token_hex(3)
                if not repository.trova_utente(nome) and not repository_profili.trova(nome):
                    break
            repository.inserisci_utente(nome, codice, False, secrets.token_hex(16), ospite=True, bot=True)
            servizi.cambia_gioco(codice, repository.trova_gioco_per_nome('Forza 4')['id'])
        elif azione == 'rimuovi':
            if bot:
                # Le chiavi esterne eliminano anche partita e richiesta pendente.
                repository.elimina_utente(bot['username'])
        elif azione == 'riprova':
            if not bot:
                raise servizi.ErroreGioco('Nessun giocatore AI nella stanza.')
        else:
            raise servizi.ErroreGioco('Azione AI non valida.')
    if azione == 'riprova':
        programma(codice, riprova=True)
    return codice


def programma(codice, riprova=False):
    """Prenota una sola richiesta per turno; il calcolo avviene fuori dalla transazione."""
    with transazione():
        partita = repository.partita_forza4(codice)
        bot = dati.trova(codice)
        if not bot or not partita or partita['risultato'] or partita['in_sala']:
            return
        prossimo = partita['rosso'] if partita['turno'] == 1 else partita['giallo']
        if prossimo != bot['username']:
            return
        richiesta = dati.richiesta(codice)
        if richiesta and (richiesta['stato'] == 'attesa' or not riprova):
            return
        token = secrets.token_hex(16)
        dati.avvia(codice, token)
    app = current_app._get_current_object()
    try:
        threading.Thread(target=esegui, args=(app, bot, partita, token), daemon=True).start()
    except RuntimeError:
        with transazione():
            dati.errore(codice, token, 'Impossibile avviare NickBot. Riprova.')


def scegli_colonna(partita):
    pesi = configurazione()
    nome_binario = 'nickgame-bot.exe' if os.name == 'nt' else 'nickgame-bot'
    binario = Path(current_app.root_path).parent / 'cpp' / 'build' / nome_binario
    try:
        risposta = subprocess.run([str(binario), str(pesi)],
                                  input=f"{partita['griglia']} {partita['turno']}\n",
                                  capture_output=True, text=True, timeout=5)
    except FileNotFoundError:
        raise servizi.ErroreGioco('Modulo AI non compilato. Riavvia con ./run.sh.') from None
    except (OSError, subprocess.TimeoutExpired):
        raise servizi.ErroreGioco('Il calcolo della rete non è riuscito. Riprova.') from None
    if risposta.returncode:
        raise servizi.ErroreGioco(risposta.stderr.strip()[:200] or 'Il modulo AI non ha risposto.')
    try:
        colonna = int(risposta.stdout.strip())
        if not 0 <= colonna <= 6:
            raise ValueError()
        return colonna
    except ValueError:
        raise servizi.ErroreGioco('Il modulo AI ha restituito una mossa non valida.') from None


def esegui(app, bot, partita, token):
    codice = bot['stanza_codice']
    with app.app_context():
        try:
            colonna = scegli_colonna(partita)
            forza4.muovi(bot['username'], bot['accesso_id'], colonna,
                         partita['id'], partita['griglia'], token_bot=token)
        except servizi.ErroreGioco as errore:
            with transazione():
                # Se nel frattempo siamo tornati in sala, il token non esiste più.
                dati.errore(codice, token, str(errore))
        except Exception:
            # Non registriamo eccezioni contenenti input del processo o credenziali.
            with transazione():
                dati.errore(codice, token, 'Errore durante il turno AI. Riprova.')
        finally:
            sincronizzazione.notifica_stanza(codice)
