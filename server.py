#!/usr/bin/env python3
from traffic_logic import GameHandler
import flask
import secrets

app = flask.Flask(__name__, template_folder='html')
app.secret_key = secrets.token_bytes()

games = {}

@app.route('/')
def root():
    is_in_game = False
    if 'game_token' in flask.session:
        if flask.session['game_token'] in games:
            is_in_game = True
    return flask.render_template('index.html', is_in_game=is_in_game)

def notify(tok):
    print(f"Game with token {tok} has a new sate")

@app.route('/game')
def game():
    if 'game_token' in flask.session:
        tok = flask.session['game_token']
        if tok in games:
            return flask.render_template('projector.html', tok=tok)
    tok = secrets.token_urlsafe(10)
    games[tok] = GameHandler(lambda: notify(tok))
    flask.session['game_token'] = tok
    return flask.render_template('projector.html', tok=tok)

@app.route('/abort')
def abort():
    if 'game_token' in flask.session:
        if flask.session['game_token'] in games:
            del games[flask.session['game_token']]
        del flask.session['game_token']
    return flask.redirect('/', code=303)

def unknown_game():
    return flask.render_template('error.html', error='You tried to join or play a game that doesn\'t exist. Perhaps it has already ended?')

@app.route('/join/<token>')
def join(token):
    if token not in games:
        return unknown_game()
    flask.session['game_token'] = token
    game = games[token]
    flask.session['player_token'] = game.player_join()
    return flask.redirect('/play', code=303)

@app.route('/play')
def play():
    if 'game_token' not in flask.session:
        return unknown_game()
    tok = flask.session['game_token']
    if tok not in games:
        return unknown_game()
    game = games[tok]
    return flask.render_template('phone.html', game=game)
