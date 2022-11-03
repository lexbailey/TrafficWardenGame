#!/usr/bin/env python3
import json
import eventlet
eventlet.monkey_patch()
from traffic_logic import GameHandler, Dir
import flask
import secrets
from flask_socketio import SocketIO
import qrcode
from io import BytesIO
import base64

app = flask.Flask(__name__, template_folder='html')
app.secret_key = secrets.token_bytes()

config = json.load(open('config.json'))
host=config.get('host', 'localhost')
port=config.get('port', 8080)

internal_url_base = f'http://{host}:{port}'
url_base = config.get('ext_url', internal_url_base)

print(f'Listening via {internal_url_base}')
print(f'Accesible via {url_base}')

sio = SocketIO(app, cors_allowed_origins=url_base)

games = {}
projectors = {}
players = {}

@app.route('/')
def root():
    is_in_game = False
    if 'game_token' in flask.session:
        if flask.session['game_token'] in games:
            is_in_game = True
    return flask.render_template('index.html', is_in_game=is_in_game)

def notify(tok):
    if tok not in games:
        return
    game = games[tok]
    for p in game.get_projectors():
        sio.emit('new_projector_state', game.get_projector_data(), to=p)
    for ptok, p in game.get_players().items():
        sid = p.get_sid()
        if sid is not None:
            sio.emit('new_player_state', p.get_phone_data(), to=sid)

def join_info(tok):
    join_url = f'{url_base}/join/{tok}'
    buf = BytesIO()
    qr_img = qrcode.make(join_url)
    qr_img.save(buf, format='png')
    qr = f'data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}'
    return join_url, qr
    
@app.route('/game')
def game():
    if 'game_token' in flask.session:
        tok = flask.session['game_token']
        if tok in games:
            join_url, qr = join_info(tok)
            return flask.render_template('projector.html', tok=tok, join_url=join_url, qr=qr)
    tok = secrets.token_urlsafe(10)
    games[tok] = GameHandler(lambda: notify(tok), sio.start_background_task)
    flask.session['game_token'] = tok
    join_url, qr = join_info(tok)
    return flask.render_template('projector.html', tok=tok, join_url=join_url, qr=qr)

@app.route('/abort')
def abort():
    if 'game_token' in flask.session:
        if flask.session['game_token'] in games:
            del games[flask.session['game_token']]
        del flask.session['game_token']
    return flask.redirect('/', code=303)

def unknown_game():
    return flask.render_template('error.html', error='You tried to join or play a game that doesn\'t exist. Perhaps it has already ended?')

def game_full():
    return flask.render_template('error.html', error='Sorry, this game already has the maximum number of players.')

@app.route('/join/<token>')
def join(token):
    if token not in games:
        return unknown_game()
    flask.session['game_token'] = token
    game = games[token]
    player = game.player_join()
    can_join = player is not None
    if can_join:
        flask.session['player_token'] = player.tok
        return flask.redirect('/play', code=303)
    return game_full()

@app.route('/play')
def play():
    if 'game_token' not in flask.session:
        return unknown_game()
    tok = flask.session['game_token']
    if tok not in games:
        return unknown_game()
    game = games[tok]
    ptok = flask.session['player_token']
    return flask.render_template('phone.html', gtok=tok, ptok=ptok)

@sio.on('register_projector')
def register_projector(tok):
    sid = flask.request.sid
    if tok not in games:
        return
    print(f'Projector {sid} joined game {tok}')
    game = games[tok]
    game.add_projector(sid)
    projectors[sid] = tok
    sio.emit('newstate', game.get_projector_data())

    # Test code
    game.player_join()
    game.player_join()

@sio.on('register_player')
def register_player(gtok, ptok):
    sid = flask.request.sid
    if gtok not in games:
        return
    print(f'Player {sid} joined game {gtok}')
    game = games[gtok]
    player = game.get_player(ptok)
    players[sid] = player
    player.set_sid(sid)
    sio.emit('new_player_state', player.get_phone_data())

@sio.on('player_quit')
def player_quit():
    sid = flask.request.sid
    if sid not in players:
        return
    player = players[sid]
    player.quit()

@sio.on('start_game')
def start_game():
    sid = flask.request.sid
    if sid not in projectors:
        return
    tok = projectors[sid]
    if tok not in games:
        return
    game = games[tok]
    game.start()

@sio.on('rename')
def rename(newname):
    sid = flask.request.sid
    if sid not in players:
        return
    player = players[sid]
    player.rename(newname)

@sio.on('place_tile')
def place_tile(tilename, x, y):
    sid = flask.request.sid
    if sid not in players:
        return
    player = players[sid]
    player.place_tile(tilename, x, y)

@sio.on('reset_players')
def reset_players():
    sid = flask.request.sid
    if sid not in projectors:
        return
    tok = projectors[sid]
    if tok not in games:
        return
    game = games[tok]
    game.kick_all()

@sio.on('to_lobby')
def to_lobby():
    sid = flask.request.sid
    if sid not in projectors:
        return
    tok = projectors[sid]
    if tok not in games:
        return
    game = games[tok]
    game.return_to_lobby()

@sio.on('remove_player')
def remove_player(player_index):
    sid = flask.request.sid
    if sid not in projectors:
        return
    tok = projectors[sid]
    if tok not in games:
        return
    game = games[tok]
    game.kick_one(player_index)

if __name__ == '__main__':
    sio.run(app, host=host, port=port)
