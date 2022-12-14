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
        self.goal = None

    def set_car(self, car):
        self.car = car

    def set_tile(self, tile_dir):
        self.tile = tile_dir

    def set_tile_player(self, p):
        self.tile_player = p

    def is_free(self):
        return self.tile is None and self.car is None

    def is_placeable_by(self, p):
        return self.is_free() or self.car.index == p

    def can_be_goal(self):
        return self.goal is None

    def set_goal(self, pid):
        self.goal = pid

    def clear_goal(self):
        self.goal = None

class Player:
    def __init__(self, index, color, pos):
        self.index = index
        self.color = color
        self.pos = pos
        self.cur_tiles = []
        self.goal = None
        self.score = 0

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
            'score': self.score,
        }

    def assign_goal(self, xy):
        self.goal = xy

    def has_reached_goal(self):
        cur_xy, _ = self.pos
        return self.goal == cur_xy

    def add_score(self, term):
        self.score += term

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
            newdir = Dir.reflect(newdir)
            dirname, dirfun = newdir
            newxy = Dir.clamp(dirfun(xy), 9)
        oldcell = self.get_cell(xy)
        newcell = self.get_cell(newxy)
        if newcell.car is None:
            player.set_pos((newxy, newdir))
            newcell.set_car(player)
            oldcell.set_car(None)
        else:
            newdir = Dir.reflect(newdir)
            dirname, dirfun = newdir
            newxy = Dir.clamp(dirfun(xy), 9)
            newcell = self.get_cell(newxy)
            if newcell.car is None:
                player.set_pos((newxy, newdir))
                newcell.set_car(player)
                oldcell.set_car(None)
            else:
                newxy = xy
                newcell = oldcell
        if newcell.tile is not None:
            player.set_pos((newxy, newcell.tile))
        if player.has_reached_goal():
            player.add_score(1)
            newcell.clear_goal()
            self.assign_one_goal(player)

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

    def assign_one_goal(self, p):
        done = False
        while not done:
            cxy, dir_ = p.get_pos()
            dx = random.randint(2, 6)
            dy = 8 - dx
            cx, cy = cxy
            x, y = (cx + dx) % 10, (cy + dy) % 10
            cell = self.grid[x][y]
            if cell.can_be_goal():
                p.assign_goal((x, y))
                cell.set_goal(p.index)
                done = True

    def assign_initial_goals(self):
        for p in self.players:
            self.assign_one_goal(p)

    def game_is_won(self):
        for p in self.players:
            if p.score >= 5:
                return True

    def step(self):
        if self.state == 'initial':
            self.assign_initial_goals()
            self.to_state('start_round', 0.5)
        elif self.state == 'start_round':
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
                if self.game_is_won():
                    self.to_state('won', 1)
                else:
                    self.to_state('start_round', 2)
        elif self.state == 'won':
            pass # Wait here until the game is reset

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

                tile_placer = -1
                if cell.tile_player is not None:
                    tile_placer = cell.tile_player
                goal = -1
                if cell.goal is not None:
                    goal = cell.goal
                rcol.append(
                    {
                        'tile': dirname,
                        'tile_placed_by': tile_placer,
                        'car': player,
                        'car_dir':  player_dir,
                        'goal': goal,
                    }
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
        self.is_kicked = False

    def kick(self):
        self.is_kicked = True

    def set_sid(self, sid):
        self.sid = sid

    def get_sid(self):
        return self.sid

    def quit(self):
        self.game().player_quit(self.tok)

    def get_player_data(self):
        data = {'name': self.name, 'index': self.index, 'kicked': False}
        game = self.game()
        if game.game_logic is not None:
            game_player = game.game_logic.get_player(self.index)
            if game_player is not None:
                data.update(game_player.get_data())
        return data


    def rename(self, newname):
        game = self.game()
        if game is not None:
            game.polled()
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
        if self.is_kicked:
            return {'projector':{}, 'player':{'kicked':True}}
        game = self.game()
        if game is None:
            return {}
        proj_data = game.get_projector_data(pov=self.index)
        player_data = self.get_player_data()
        return {'projector':proj_data, 'player':player_data}

    def notify(self):
        self.game().notify()

    def place_tile(self, dir_, x, y):
        self.game().polled()
        logic = self.get_game_logic()
        player = self.get_logical_player()
        if logic is not None:
            if logic.get_cell((x, y)).is_placeable_by(self.index) and player.can_place(dir_):
                player.use_tile(dir_)
                logic.put_tile((x, y), Dir.from_name(dir_), self.index)
                self.notify()

class GameHandler:
    MAX_PLAYERS = 8

    def __init__(self, callback, thread_starter):
        self.state = 'lobby'
        self.game_logic = None
        self.players = {}
        self.callback = callback
        self.projectors = []
        self.thread_starter = thread_starter
        self.polled()

    def polled(self):
        self.last_polled_at = time.time()

    def notify(self):
        if time.time() - self.last_polled_at > (60*15): # fifteen minutes with no activity means game gets killed
            self.end()
        self.callback()

    def get_state(self):
        return self.state

    def get_projectors(self):
        return self.projectors

    def add_projector(self, sid):
        self.projectors.append(sid)
        self.polled()

    def player_join(self):
        self.polled()
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
        self.polled()
        if self.state != 'lobby':
            return # Can only do this action in the lobby
        if tok not in self.players:
            return
        del self.players[tok]
        self.reindex_players()
        self.notify()

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
        if self.state == 'game_over':
            return {
                'state': self.state,
                'players': players,
                'game': self.game_logic.get_projector_render_data(pov=pov)
            }
        if self.state == 'ended':
            return {
                'state': self.state,
                'players': [],
            }
        return {
            'state': 'error'
        }

    def thread_func(self):
        while not self.stop_thread.is_set():
            eventlet.sleep(self.game_logic.get_wait())
            self.game_logic.step()
            if self.game_logic.state == 'won':
                self.state = 'game_over'
            self.notify()
            if self.state == 'game_over':
                break

    def start_thread(self):
        self.stop_thread = threading.Event()
        self.thread = self.thread_starter(self.thread_func)

    def start(self):
        self.polled()
        if self.state != 'lobby':
            return
        if len(self.players) < 2:
            return
        self.game_logic = TrafficWardenLogic(len(self.players))
        self.state = 'running'
        self.notify()
        self.start_thread()

    def end(self):
        try:
            self.stop_thread.set()
        except AttributeError: # wow this is a hack
            pass
        for p in self.players.values():
            p.kick()
        self.state = 'ended'

    def kick_all(self):
        self.polled()
        if self.state != 'lobby':
            return
        for p in self.players.values():
            p.kick()
        # lazy double-notify
        self.notify()
        self.players = {}
        self.notify()

    def return_to_lobby(self):
        self.polled()
        if self.state != 'game_over':
            return
        self.state = 'lobby'
        self.game_logic = None
        self.notify()

    def player_tok_from_index(self, index):
        for tok, p in self.players.items():
            if p.index == index:
                return tok

    def reindex_players(self):
        for i, (tok, p) in enumerate(self.players.items()):
            p.index = i

    def kick_one(self, index):
        self.polled()
        if self.state != 'lobby':
            return
        tok = self.player_tok_from_index(index)
        if tok is None:
            return
        p = self.players[tok]
        p.kick()
        # lazy double-notify
        self.notify()
        del self.players[tok]
        self.reindex_players()
        self.notify()
