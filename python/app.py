"""Pagine e API web di Nickgame."""
import flask

import avatar
import economia
import repository_economia
import profili
import repository_profili

import justone
import nomi
import quiz
import forza4
import bot
import configurazione
import connessione
import repository
import servizi
import sincronizzazione

app = flask.Flask(__name__)
configurazione.configura(app)
connessione.init_app(app)


def utente_corrente():
    # Questo accesso riguarda la stanza, non il profilo permanente.
    username = flask.session.get('username')
    utente = repository.trova_utente(username)
    accesso_id = flask.session.get('accesso_id', username)
    if utente is None or utente['accesso_id'] != accesso_id or utente['is_bot']:
        flask.session.pop('username', None)
        flask.session.pop('accesso_id', None)
        return None
    if not utente['is_ospite'] and flask.session.get('profilo_username') != username:
        flask.session.pop('username', None)
        flask.session.pop('accesso_id', None)
        return None
    return utente


@app.after_request
def non_memorizzare_pagine(risposta):
    # Le pagine possono contenere il codice personale: non conservarle nella cache.
    if flask.request.endpoint != 'static':
        risposta.headers['Cache-Control'] = 'no-store'
    return risposta


@app.route('/', methods=['GET', 'POST'])
def login():
    if utente_corrente() is not None:
        return flask.redirect(flask.url_for('stanza'))
    profilo = repository_profili.trova(flask.session.get('profilo_username'))
    errore, username, codice = None, '', ''
    if flask.request.method == 'POST':
        azione = flask.request.form.get('azione')
        try:
            if profilo is None:
                if azione in ('crea', 'entra'):
                    username = flask.request.form.get('username', '').strip()
                    codice = flask.request.form.get('codice', '').strip()
                    codice, accesso_id = servizi.accedi(username, azione, codice, ospite=True)
                    flask.session.clear()
                    flask.session['username'] = username
                    flask.session['accesso_id'] = accesso_id
                    sincronizzazione.notifica_stanza(codice)
                    return flask.redirect(flask.url_for('stanza'))
                if azione == 'registra':
                    username = flask.request.form.get('username', '').strip()
                    username, personale = profili.crea(username)
                elif azione == 'accedi':
                    personale = flask.request.form.get('codice_personale', '').strip()
                    username = profili.accedi(personale)['username']
                else:
                    raise ValueError('Accedi al profilo prima di scegliere una stanza.')
                flask.session.clear()
                flask.session['profilo_username'] = username
                flask.session['codice_personale'] = personale
                # Se il profilo è già in una stanza, il nuovo browser la ritrova.
                partecipazione = repository.trova_utente(username)
                if partecipazione:
                    flask.session['username'] = username
                    flask.session['accesso_id'] = partecipazione['accesso_id']
                return flask.redirect(flask.url_for('login'))
            codice = flask.request.form.get('codice', '').strip()
            username = profilo['username']
            codice, accesso_id = servizi.accedi(username, azione, codice)
            flask.session['username'] = username
            flask.session['accesso_id'] = accesso_id
            sincronizzazione.notifica_stanza(codice)
            return flask.redirect(flask.url_for('stanza'))
        except ValueError as problema:
            errore = str(problema)
    avatar_scelto = avatar.carica_profilo(profilo['username']) if profilo else None
    catalogo_avatar = repository_economia.catalogo(profilo['username']) if profilo else []
    return flask.render_template(
        'login.html', profilo=profilo, errore=errore, username=username,
        codice=codice, stanze=repository.stanze_disponibili(),
        avatar_scelto=avatar_scelto, catalogo_avatar=catalogo_avatar
    )


@app.post('/logout')
def logout():
    utente = utente_corrente()
    codice = servizi.esci(utente['username'], utente['accesso_id']) if utente else None
    flask.session.clear()
    if codice is not None:
        sincronizzazione.notifica_stanza(codice)
    return flask.redirect(flask.url_for('login'))


def stato_gioco(utente):
    gioco = repository.gioco_selezionato(utente['stanza_codice'])
    if gioco is not None and gioco['nome'] == 'Just One':
        stato = justone.stato(utente)
    elif gioco is not None and gioco['nome'] == 'Nomi, cose, città':
        stato = nomi.stato(utente)
    elif gioco is not None and gioco['nome'] == 'Quiz':
        stato = quiz.stato(utente)
    else:
        stato = forza4.stato(utente['stanza_codice'])
    partita = stato.get('partita')
    stato['premio_monete'] = repository_economia.premi_partita(
        partita['id'], gioco['nome'], utente['username']
    ) if partita and gioco else None
    stato['gioco_corrente'] = gioco
    stato['minimo_giocatori'] = 3 if gioco is not None and gioco['nome'] == 'Just One' else 2
    return stato


@app.post('/seleziona-gioco')
def seleziona_gioco():
    utente = utente_corrente()
    if utente is None:
        return flask.redirect(flask.url_for('login'))
    if not utente['is_admin']:
        flask.abort(403)
    gioco_id = flask.request.form.get('gioco_id', type=int)
    if gioco_id is None or not 1 <= gioco_id <= 2147483647:
        flask.abort(400)
    try:
        codice = servizi.scegli_gioco(utente['username'], utente['accesso_id'], gioco_id)
    except servizi.ErroreGioco as errore:
        flask.flash(str(errore))
    else:
        sincronizzazione.notifica_stanza(codice)
    return flask.redirect(flask.url_for('stanza'))


@app.get('/stanza')
def stanza():
    utente = utente_corrente()
    if utente is None:
        return flask.redirect(flask.url_for('login'))

    elenco = repository.partecipanti_stanza(utente['stanza_codice'])
    return flask.render_template(
        'stanza.html', utente=utente, partecipanti=elenco,
        avatar_scelto=avatar.carica(utente), catalogo_avatar=[a for a in repository_economia.catalogo(utente['username'])
                         if not utente['is_ospite'] or a['prezzo'] == 0],
        giochi=repository.giochi_disponibili(utente['stanza_codice']),
        **stato_gioco(utente)
    )


@app.context_processor
def saldo_nelle_pagine():
    return {'saldo_monete': repository_economia.saldo(flask.session.get('profilo_username'))}


@app.post('/avatar/acquista')
def acquista_avatar():
    utente = utente_corrente()
    profilo = repository_profili.trova(flask.session.get('profilo_username'))
    if utente is None and profilo is None:
        return flask.jsonify(errore='Accesso scaduto.'), 401
    if utente is not None and utente['is_ospite']:
        return flask.jsonify(errore='Gli acquisti richiedono un profilo registrato.'), 403
    username = utente['username'] if utente is not None else profilo['username']
    errore = None
    try:
        economia.acquista(username, flask.request.form.get('cosmetico_id'))
    except ValueError as problema:
        errore = str(problema)
    return flask.jsonify(
        errore=errore, saldo=repository_economia.saldo(username),
        catalogo=repository_economia.catalogo(username)
    ), 400 if errore else 200


@app.get('/api/economia')
def saldo_economia():
    utente = utente_corrente()
    if utente and utente['is_ospite']:
        return flask.jsonify(saldo=0, catalogo=[a for a in repository_economia.catalogo(utente['username'])
                                              if a['prezzo'] == 0])
    username = flask.session.get('profilo_username')
    if repository_profili.trova(username) is None:
        return flask.jsonify(errore='Accesso richiesto'), 401
    return flask.jsonify(saldo=repository_economia.saldo(username),
                         catalogo=repository_economia.catalogo(username))


@app.post('/avatar')
def salva_avatar():
    utente = utente_corrente()
    profilo = repository_profili.trova(flask.session.get('profilo_username'))
    if utente is None and profilo is None:
        return flask.jsonify(errore='Accesso scaduto.'), 401
    try:
        if utente is not None:
            avatar.salva(utente, flask.request.form)
        else:
            avatar.salva_profilo(profilo['username'], flask.request.form)
    except ValueError as errore:
        return flask.jsonify(errore=str(errore)), 400
    return flask.jsonify(ok=True)


@app.get('/stanza/giochi')
def elenco_giochi():
    utente = utente_corrente()
    if utente is None:
        return '', 401
    risposta = flask.make_response(flask.render_template(
        'giochi.html', utente=utente,
        giochi=repository.giochi_disponibili(utente['stanza_codice']),
        **stato_gioco(utente)
    ))
    risposta.headers['Cache-Control'] = 'no-store'
    return risposta



@app.get('/stanza/partita')
def pannello_partita():
    utente = utente_corrente()
    if utente is None:
        return '', 401
    risposta = flask.make_response(flask.render_template(
        'partita.html', utente=utente, **stato_gioco(utente)
    ))
    risposta.headers['Cache-Control'] = 'no-store'
    return risposta


@app.post('/forza4/<azione>')
def azione_forza4(azione):
    utente = utente_corrente()
    if utente is None:
        return flask.redirect(flask.url_for('login'))
    try:
        if azione == 'avvia':
            codice = forza4.avvia(utente['username'], utente['accesso_id'])
        elif azione in ('stanza', 'riprendi'):
            codice = forza4.cambia_vista(utente['username'], utente['accesso_id'], azione == 'stanza')
        elif azione == 'muovi':
            codice = forza4.muovi(
                utente['username'], utente['accesso_id'],
                flask.request.form.get('colonna', type=int),
                flask.request.form.get('partita_id'),
                flask.request.form.get('griglia')
            )
        else:
            flask.abort(404)
    except servizi.ErroreGioco as errore:
        flask.flash(str(errore))
    else:
        bot.programma(codice)
        sincronizzazione.notifica_stanza(codice)
    return flask.redirect(flask.url_for('stanza') + '#partita')


@app.post('/bot/<azione>')
def gestisci_bot(azione):
    utente = utente_corrente()
    if utente is None:
        return flask.redirect(flask.url_for('login'))
    if not utente['is_admin']:
        flask.abort(403)
    if azione not in ('aggiungi', 'rimuovi', 'riprova'):
        flask.abort(404)
    try:
        codice = bot.gestisci(utente['username'], utente['accesso_id'], azione)
    except servizi.ErroreGioco as errore:
        flask.flash(str(errore))
    else:
        sincronizzazione.notifica_stanza(codice)
    return flask.redirect(flask.url_for('stanza'))


@app.post('/partita/<azione>')
def cambia_vista(azione):
    utente = utente_corrente()
    if utente is None:
        return flask.redirect(flask.url_for('login'))
    if azione not in ('stanza', 'riprendi'):
        flask.abort(404)
    gioco = repository.gioco_selezionato(utente['stanza_codice'])
    if gioco is not None and gioco['nome'] == 'Just One':
        servizio = justone
    elif gioco is not None and gioco['nome'] == 'Nomi, cose, città':
        servizio = nomi
    else:
        servizio = quiz if gioco is not None and gioco['nome'] == 'Quiz' else forza4
    try:
        codice = servizio.cambia_vista(utente['username'], utente['accesso_id'], azione == 'stanza')
    except servizi.ErroreGioco as errore:
        flask.flash(str(errore))
    else:
        if servizio is forza4:
            bot.programma(codice)
        sincronizzazione.notifica_stanza(codice)
    return flask.redirect(flask.url_for('stanza'))


@app.post('/quiz/<azione>')
def azione_quiz(azione):
    utente = utente_corrente()
    if utente is None:
        return flask.redirect(flask.url_for('login'))
    username, accesso_id = utente['username'], utente['accesso_id']
    partita_id = flask.request.form.get('partita_id')
    numero = flask.request.form.get('domanda', type=int)
    try:
        if azione == 'avvia':
            codice = quiz.avvia(username, accesso_id)
        elif azione == 'rispondi':
            risposta = flask.request.form.get('risposta', type=int)
            codice = quiz.rispondi(username, accesso_id, partita_id, numero, risposta)
        elif azione == 'prossima':
            codice = quiz.prossima(username, accesso_id, partita_id, numero)
        else:
            flask.abort(404)
    except servizi.ErroreGioco as errore:
        flask.flash(str(errore))
    else:
        sincronizzazione.notifica_stanza(codice)
    return flask.redirect(flask.url_for('stanza') + '#partita')


@app.post('/nomi/bozza')
def bozza_nomi():
    utente = utente_corrente()
    if utente is None:
        return flask.jsonify(errore='Accesso scaduto.'), 401
    try:
        nomi.rispondi(utente['username'], utente['accesso_id'], flask.request.form.get('partita_id'),
                     flask.request.form.get('turno', type=int), flask.request.form, bozza=True)
    except servizi.ErroreGioco as errore:
        return flask.jsonify(errore=str(errore)), 409
    return flask.jsonify(ok=True)


@app.post('/nomi/scadenza')
def scadenza_nomi():
    utente = utente_corrente()
    if utente is None:
        return flask.jsonify(errore='Accesso scaduto.'), 401
    nomi.aggiorna_scadenza(utente['stanza_codice'])
    return flask.jsonify(ok=True)


@app.post('/nomi/<azione>')
def azione_nomi(azione):
    utente = utente_corrente()
    if utente is None:
        return flask.redirect(flask.url_for('login'))
    username, accesso_id = utente['username'], utente['accesso_id']
    partita_id = flask.request.form.get('partita_id')
    turno = flask.request.form.get('turno', type=int)
    try:
        if azione == 'avvia':
            codice = nomi.avvia(username, accesso_id)
        elif azione == 'rispondi':
            codice = nomi.rispondi(username, accesso_id, partita_id, turno, flask.request.form)
        elif azione == 'valuta':
            codice = nomi.valuta(username, accesso_id, partita_id, turno, flask.request.form.getlist('contestate'))
        elif azione == 'prossima':
            codice = nomi.prossima(username, accesso_id, partita_id, turno)
        else:
            flask.abort(404)
    except servizi.ErroreGioco as errore:
        flask.flash(str(errore))
    else:
        sincronizzazione.notifica_stanza(codice)
    return flask.redirect(flask.url_for('stanza') + '#partita')


@app.post('/justone/<azione>')
def azione_justone(azione):
    utente = utente_corrente()
    if utente is None:
        return flask.redirect(flask.url_for('login'))
    username, accesso_id = utente['username'], utente['accesso_id']
    partita_id = flask.request.form.get('partita_id')
    turno = flask.request.form.get('turno', type=int)
    try:
        if azione == 'avvia':
            codice = justone.avvia(username, accesso_id)
        elif azione == 'indizio':
            codice = justone.invia_indizio(username, accesso_id, partita_id, turno, flask.request.form.get('indizio', ''))
        elif azione == 'indovina':
            testo = '' if flask.request.form.get('passa') else flask.request.form.get('tentativo', '')
            codice = justone.indovina(username, accesso_id, partita_id, turno, testo)
        elif azione == 'prossima':
            codice = justone.prossima(username, accesso_id, partita_id, turno)
        else:
            flask.abort(404)
    except servizi.ErroreGioco as errore:
        flask.flash(str(errore))
    else:
        sincronizzazione.notifica_stanza(codice)
    return flask.redirect(flask.url_for('stanza') + '#partita')


@app.get('/api/stanze')
def elenco_stanze():
    # La lista è visibile prima dell'accesso, come la pagina di login.
    risposta = flask.jsonify(repository.stanze_disponibili())
    risposta.headers['Cache-Control'] = 'no-store'
    return risposta


@app.get('/api/partecipanti')
def partecipanti():
    utente = utente_corrente()
    if utente is None:
        return flask.jsonify(errore='Accesso richiesto'), 401

    elenco = repository.partecipanti_stanza(utente['stanza_codice'])
    risposta = flask.jsonify(elenco)
    risposta.headers['Cache-Control'] = 'no-store'
    return risposta


@app.get('/api/sincronizzazione')
def collegamento():
    utente = utente_corrente()
    if utente is None:
        return flask.jsonify(errore='Accesso richiesto'), 401

    indirizzo = sincronizzazione.url_websocket(utente['stanza_codice'])
    risposta = flask.jsonify(url=indirizzo)
    risposta.headers['Cache-Control'] = 'no-store'
    return risposta


if __name__ == '__main__':
    app.run()
