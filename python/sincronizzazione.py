"""Indirizzo WebSocket e notifiche al server Go locale."""
import urllib.request
from urllib.parse import urlsplit
from flask import current_app, request


def url_websocket(codice):
    """Costruisce un WebSocket raggiungibile dallo stesso client HTTP.

    Usare l'host della richiesta evita incongruenze tra localhost, IP Wi-Fi
    e altri indirizzi LAN, che farebbero rifiutare l'origine a Go.
    """
    configurato = urlsplit(current_app.config['GO_WEBSOCKET_URL'])
    host_client = request.host.split(':', 1)[0].strip('[]')
    porta = configurato.port or 50011
    schema = 'wss' if request.is_secure else 'ws'
    host_url = f'[{host_client}]' if ':' in host_client else host_client
    return f'{schema}://{host_url}:{porta}/ws?stanza={codice}'


def notifica_stanza(codice):
    indirizzo = current_app.config['GO_HTTP_URL']
    url = indirizzo + '/notifica?stanza=' + codice

    # Solo i server conoscono questa chiave: non viene inviata al browser.
    chiave = current_app.config['SECRET_KEY']
    richiesta = urllib.request.Request(url, method='POST')
    richiesta.add_header('Authorization', 'Bearer ' + chiave)

    try:
        # Attendiamo al massimo un secondo per le operazioni di rete.
        with urllib.request.urlopen(richiesta, timeout=1) as risposta:
            risposta.read()
    except OSError:
        # Include gli errori di rete e HTTP: le modifiche al database restano valide.
        current_app.logger.warning('Go non raggiungibile: notifica della stanza non inviata.')
