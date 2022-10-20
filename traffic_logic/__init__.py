import eventlet
eventlet.monkey_patch()
import secrets
import weakref
import threading
import time
import random

class Dir:
    down = ('down', lambda xy: (xy[0], xy[1]-1))
    up = ('up', lambda xy: (xy[0], xy[1]+1))
    left = ('left', lambda xy: (xy[0]-1, xy[1]))
    right = ('right', lambda xy: (xy[0]+1, xy[1]))

    def clamp(xy, size):
        x,y=xy
        return (
            max(0, min(x,size))
            ,max(0, min(y,size))
        )

    def reflect(d):
        if d == Dir.down:
            return Dir.up
        if d == Dir.up:
            return Dir.down
        if d == Dir.left:
            return Dir.right
        if d == Dir.right:
            return Dir.left

    def from_name(name):
        if name == 'down':
            return Dir.down
        if name == 'up':
            return Dir.up
        if name == 'left':
            return Dir.left
        if name == 'right':
            return Dir.right

class Cell:
    def __init__(self):
        self.tile = None
        self.car = None
        self.tile_player = None

    def set_car(self, car):
        self.car = car

    def set_tile(self, tile_dir):
        self.tile = tile_dir

    def set_tile_player(self, p):
        self.tile_player = p

    def is_free(self):
        return self.tile is None

class Player:
    def __init__(self, index, color, pos):
        self.index = index
        self.color = color
        self.pos = pos
        self.cur_tiles = []

    def get_pos(self):
        return self.pos

    def set_pos(self, pos):
        self.pos = pos

    def assign_tiles(self):
        options = ['up', 'down', 'left', 'right'] * 2
        random.shuffle(options)
        self.cur_tiles = options[0:3]

    def can_place(self, tile):
        return tile in self.cur_tiles

    def use_tile(self, tile):
        self.cur_tiles.remove(tile)

    def drain_tiles(self):
        self.cur_tiles = []

    def get_data(self):
        return {
            'color': self.color,
            'tiles': self.cur_tiles,
        }

class TrafficWardenLogic:
    def __init__(self, n_players):
        self.n_players = n_players
        self.init_grid(10)
        self.init_players(n_players)
        self.last_state = 'initial'
        self.state = 'initial'
        self.wait = 3
        self.play_order = []

    def init_grid(self, size):
        self.grid = []
        for i in range(size):
            line = []
            for j in range(size):
                line.append(Cell())
            self.grid.append(line)

    def init_players(self, n):
        self.players = []
        colors = [0xff0000, 0x00ffff, 0x8000ff, 0x80ff00, 0xff0098, 0x00ff3e, 0xffce00, 0x0042ff]
        start_positions = [
            ((3,9), Dir.down),
            ((6,0), Dir.up),
            ((3,0), Dir.up),
            ((6,9), Dir.down),
            ((9,3), Dir.left),
            ((0,6), Dir.right),
            ((0,3), Dir.right),
            ((9,6), Dir.left),
        ]
        for i in range(n):
            p = Player(i, colors[i], start_positions[i])
            (xy, _) = p.get_pos()
            self.get_cell(xy).set_car(p)
            self.players.append(p)

    def get_cell(self, xy):
        x, y = xy
        return self.grid[x][y]

    def put_tile(self, xy, tile, player_index):
        x, y = xy
        self.grid[x][y].set_tile(tile)
        self.grid[x][y].set_tile_player(player_index)

    def step_player(self, player_id):
        p = player_id
        player = self.players[p]
        (xy, dir_) = player.get_pos()
        cell = self.get_cell(xy)
        newdir = dir_
        if cell.tile is not None:
            newdir = cell.tile
        dirname, dirfun = newdir
        newxy = Dir.clamp(dirfun(xy), 9)
        if newxy == xy:
            newdir = Dir.reflect(dir_)
            dirname, dirfun = newdir
            newxy = Dir.clamp(dirfun(xy), 9)
        oldcell = self.get_cell(xy)
        newcell = self.get_cell(newxy)
        if newcell.car is None:
            player.set_pos((newxy, newdir))
            newcell.set_car(player)
            oldcell.set_car(None)
        else:
            newdir = Dir.reflect(dir_)
            dirname, dirfun = newdir
            newxy = Dir.clamp(dirfun(xy), 9)
            newcell = self.get_cell(newxy)
            player.set_pos((newxy, newdir))
            newcell.set_car(player)
            oldcell.set_car(None)

    def to_state(self, newstate, wait):
        self.last_state = self.state
        self.state = newstate
        self.wait = wait

    def assign_tiles(self):
        for p in self.players:
            p.assign_tiles()
        
    def decide_order(self):
        ids = list(range(self.n_players))
        random.shuffle(ids)
        self.play_order = ids

    def clear_tiles(self):
        for x in range(10):
            for y in range(10):
                self.grid[x][y].set_tile(None)

    def drain_tiles(self):
        for p in self.players:
            p.drain_tiles()

    def step(self):
        if self.state == 'initial':
            self.clear_tiles()
            self.to_state('assign_tiles', 2)
        elif self.state == 'assign_tiles':
            self.decide_order()
            self.assign_tiles()
            self.to_state('await_play', 20)
        elif self.state == 'await_play':
            self.drain_tiles()
            self.sim_rounds = 5
            self.cur_player = 0
            self.to_state('simulate', 1)
        elif self.state == 'simulate':
            if self.sim_rounds > 0:
                next_ = self.play_order[self.cur_player]
                self.step_player(next_)
                self.cur_player += 1
                if self.cur_player > self.n_players-1:
                    self.sim_rounds -= 1
                    self.cur_player = 0
                self.to_state('simulate', 1)
            else:
                self.to_state('initial', 2)

    def get_wait(self):
        return self.wait

    def get_player_colors(self):
        return [p.color for p in self.players]

    def get_player(self, i):
        return self.players[i]

    def render_grid(self, pov):
        rgrid = []
        for col in self.grid:
            rcol = []
            for cell in col:
                dirname = ''
                if cell.tile is not None:
                    dirname, dirfun = cell.tile
                    if self.state != 'simulate':
                        if pov is None:
                            dirname = '?'
                        if pov != cell.tile_player:
                            dirname = '?'
                player = -1
                player_dir = ''
                if cell.car is not None:
                    player = cell.car.index
                    _, (player_dir, _) = cell.car.get_pos()
                rcol.append(
                    [dirname, player, player_dir]
                )
            rgrid.append(rcol)
        return rgrid

    def get_projector_render_data(self, pov=None):
        return {
            'player_colors': self.get_player_colors(),
            'grid': self.render_grid(pov),
            'last_state': self.last_state,
            'cur_state': self.state,
            'play_order': self.play_order
        }

class PlayerHandler:
    def __init__(self, game, index):
        self.index = index
        self.game = weakref.ref(game)
        tok = secrets.token_urlsafe(10)
        self.tok = tok
        self.name = '[New player]'
        self.sid = None

    def set_sid(self, sid):
        self.sid = sid

    def get_sid(self):
        return self.sid

    def get_player_data(self):
        return {'name': self.name}

    def rename(self, newname):
        game = self.game()
        if game is not None:
            if game.get_state() != 'lobby':
                return # Can only do this action in the lobby
            self.name = newname
            self.game().notify()

    def get_game_logic(self):
        game = self.game()
        if game is not None:
            return game.game_logic

    def get_logical_player(self):
        game = self.game()
        if game is None:
            return None
        if game.game_logic is not None:
            return game.game_logic.get_player(self.index)

    def get_phone_data(self):
        game = self.game()
        if game is None:
            return {}
        proj_data = game.get_projector_data(pov=self.index)
        player_data = self.get_player_data()
        if game.game_logic is not None:
            game_player = game.game_logic.get_player(self.index)
            if game_player is not None:
                player_data.update(game_player.get_data())
        return {'projector':proj_data, 'player':player_data}

    def notify(self):
        self.game().notify()

    def place_tile(self, dir_, x, y):
        logic = self.get_game_logic()
        player = self.get_logical_player()
        if logic is not None:
            if logic.get_cell((x, y)).is_free():
                if player.can_place(dir_):
                    player.use_tile(dir_)
                    logic.put_tile((x, y), Dir.from_name(dir_), self.index)
                    self.notify()

class GameHandler:
    MAX_PLAYERS = 8

    def __init__(self, callback, thread_starter):
        self.state = 'lobby'
        self.game_logic = None
        self.players = {}
        self.notify = callback
        self.projectors = []
        self.thread_starter = thread_starter

    def get_state(self):
        return self.state

    def get_projectors(self):
        return self.projectors

    def add_projector(self, sid):
        self.projectors.append(sid)

    def player_join(self):
        if self.state != 'lobby':
            return # Can only do this action in the lobby
        n = len(self.players)
        if n < GameHandler.MAX_PLAYERS:
            player = PlayerHandler(self, n)
            self.players[player.tok] = player
            self.notify()
            return player
        return None

    def get_player(self, tok):
        return self.players.get(tok)

    def get_players(self):
        return self.players

    def player_quit(self, tok):
        if self.state != 'lobby':
            return # Can only do this action in the lobby
        if tok not in self.players:
            return
        self.notify()
        del self.players[tok]

    def get_projector_data(self, pov=None):
        players = [p.get_player_data() for tok, p in self.players.items()]
        if self.state == 'lobby':
            return {
                'state': self.state,
                'players': players,
            }
        if self.state == 'running':
            return {
                'state': self.state,
                'players': players,
                'game': self.game_logic.get_projector_render_data(pov=pov)
            }
        return {
            'state': 'error'
        }

    def thread_func(self):
        while not self.stop_thread.is_set():
            eventlet.sleep(self.game_logic.get_wait())
            self.game_logic.step()
            self.notify()

    def start_thread(self):
        self.stop_thread = threading.Event()
        self.thread = self.thread_starter(self.thread_func)

    def start(self):
        if self.state != 'lobby':
            return
        if len(self.players) < 2:
            return
        self.game_logic = TrafficWardenLogic(len(self.players))
        self.state = 'running'
        self.notify()
        self.start_thread()
