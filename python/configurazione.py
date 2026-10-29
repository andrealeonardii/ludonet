"""Impostazioni iniziali di Flask e percorsi dei file locali."""
import os
import secrets


def configura(app):
    cartella = app.instance_path
    os.makedirs(cartella, exist_ok=True)
    percorso_chiave = os.path.join(cartella, 'secret.key')

    # 'x' crea un file nuovo: non sovrascrive una chiave già esistente.
    try:
        with open(percorso_chiave, 'x', encoding='utf-8') as file:
            file.write(secrets.token_hex(32))
    except FileExistsError:
        pass

    with open(percorso_chiave, encoding='utf-8') as file:
        app.config['SECRET_KEY'] = file.read()

    app.config['DATABASE'] = os.path.join(cartella, 'nickgame.sqlite')
    app.config['GO_HTTP_URL'] = os.environ.get('NICKGAME_GO_HTTP_URL', 'http://127.0.0.1:50011')
    app.config['GO_WEBSOCKET_URL'] = os.environ.get('NICKGAME_GO_WS_URL', 'ws://127.0.0.1:50011')
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
