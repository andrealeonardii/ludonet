"""Collegamento al modulo C++ e transazioni per premi e acquisti."""
import os
import subprocess
from pathlib import Path

from connessione import transazione
import repository_profili
import repository_economia as dati
from servizi import ErroreGioco

NOME_ESEGUIBILE = 'nickgame-economia.exe' if os.name == 'nt' else 'nickgame-economia'
ESEGUIBILE = Path(__file__).resolve().parent.parent / 'cpp' / 'build' / NOME_ESEGUIBILE


def esegui(*argomenti):
    # Niente shell: ogni valore è un argomento separato del programma C++.
    try:
        risultato = subprocess.run([str(ESEGUIBILE), *map(str, argomenti)],
                                   capture_output=True, text=True, timeout=3)
    except (OSError, subprocess.TimeoutExpired) as errore:
        raise ErroreGioco('Economia non disponibile. Riavvia il progetto con run.sh.') from errore
    if risultato.returncode != 0:
        raise ErroreGioco(risultato.stderr.strip() or 'Operazione non riuscita.')
    try:
        numero = int(risultato.stdout.strip())
        if not 0 <= numero <= 2147483647:
            raise ValueError()
        return numero
    except ValueError as errore:
        raise ErroreGioco('Risposta del modulo economia non valida.') from errore


def acquista(username, cosmetico_id):
    with transazione():
        if repository_profili.trova(username) is None:
            raise ValueError('Profilo non trovato.')
        articolo = next((c for c in dati.catalogo(username) if c['id'] == cosmetico_id), None)
        if articolo is None:
            raise ValueError('Oggetto non trovato.')
        nuovo_saldo = esegui('acquista', dati.saldo(username), articolo['prezzo'], articolo['posseduto'])
        dati.imposta_saldo(username, nuovo_saldo)
        dati.registra_acquisto(username, cosmetico_id)


def premia(partita, gioco, username, esito, parole=0):
    # Gli ospiti giocano senza portafoglio permanente.
    if repository_profili.trova(username) is None:
        return
    # Chiamata nella stessa transazione che conclude la partita: tutto o niente.
    if dati.premi_partita(partita, gioco, username) is not None:
        return
    monete = esegui('premio', esito, parole)
    saldo = dati.saldo(username) + monete
    if saldo > 2147483647:
        raise ErroreGioco('Limite del saldo raggiunto.')
    if dati.registra_premio(partita, gioco, username, monete):
        dati.imposta_saldo(username, saldo)


def premia_classifica(partita, gioco, classifica):
    massimo = max(riga['punti'] for riga in classifica)
    primi = [riga['username'] for riga in classifica if riga['punti'] == massimo]
    for riga in classifica:
        esito = 'sconfitta'
        if riga['username'] in primi:
            esito = 'vittoria' if len(primi) == 1 else 'pareggio'
        premia(partita, gioco, riga['username'], esito)
