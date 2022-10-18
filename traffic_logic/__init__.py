import secrets

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

class Cell:
    def __init__(self):
        self.tile = None
        self.car = None

    def set_car(self, car):
        self.car = car

    def set_tile(self, tile_dir):
        self.tile = tile_dir

class Player:
    def __init__(self, color, pos):
        self.color = color
        self.pos = pos

    def get_pos(self):
        return self.pos

    def set_pos(self, pos):
        self.pos = pos

class TrafficWardenLogic:
    def __init__(self, n_players):
        self.n_players = n_players
        self.init_grid(10)
        self.init_players(n_players)

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
            p = Player(colors[i], start_positions[i])
            (xy, _) = p.get_pos()
            self.get_cell(xy).set_car(p)
            self.players.append(p)

    def get_cell(self, xy):
        x, y = xy
        return self.grid[x][y]

    def put_tile(self, xy, tile):
        x, y = xy
        self.grid[x][y].set_tile(tile)

    def step(self, player_order):
        for p in player_order:
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

    def get_player_colors(self):
        return [p.color for p in self.players]

    def render_grid(self):
        rgrid = []
        for col in self.grid:
            rcol = []
            for cell in col:
                dirname = ''
                if cell.tile is not None:
                    dirname, dirfun = cell.tile
                playercol = ''
                if cell.car is not None:
                    playercol = '%06x' % cell.car.color
                rcol.append(
                    [dirname, playercol]
                )
            rgrid.append(rcol)
        return rgrid

    def get_projector_render_data(self):
        return {
            'player_colors': self.get_player_colors(),
            'grid': self.render_grid(),
        }

class GameHandler:
    def __init__(self, callback):
        self.state = 'lobby'
        self.game_logic = None
        self.players = {}
        self.notify = callback

    def get_state(self):
        return self.state

    def player_join(self):
        if self.state != 'lobby':
            return # Can only do this action in the lobby
        tok = secrets.token_urlsafe(10)
        self.players[tok] = '[New player]'
        self.notify()
        return tok

    def player_quit(self, tok):
        if self.state != 'lobby':
            return # Can only do this action in the lobby
        if tok not in self.players:
            return
        self.notify()
        del self.players[tok]

    def player_rename(self, tok, name):
        if self.state != 'lobby':
            return # Can only do this action in the lobby
        if tok not in self.players:
            return
        self.notify()
        self.players[tok] = name

    def get_projector_data(self):
        if self.state == 'lobby':
            return {
                'state': self.state,
                'players': self.players,
            }
        if self.state == 'running':
            return {
                'state': self.state,
                'players': self.players,
                'game': self.game_logic.get_projector_render_data()
            }
        return {
            'state': 'error'
        }

    def start(self):
        if self.state != 'lobby':
            return
        if len(self.players) < 2:
            return
        self.game_logic = TrafficWardenLogic(len(self.players))
        self.state = 'running'
        self.notify()
