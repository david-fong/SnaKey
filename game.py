from time import process_time

from pair import *
import tkinter as tk


class Tile:
    """

    """

    def __init__(self, pos: Pair, key: str = ''):
        self.pos = pos
        self.key = tk.StringVar()
        self.key.set(key)
        self.label: tk.Label = None
        self.ditch = False
        self.canvas_id = None

    def color(self, cs: dict):
        """ cs follows {'bg': _, 'text': _} """
        self.label.configure(cs)


def weighted_choice(weights: dict):
    """
    Values in the weights dict must be of type in or float.
    Returns a key from the weights dict.
    Favors keys with greater value mappings
    """
    from random import uniform
    choice = uniform(0, sum(weights.values()))
    for key, weight in weights.items():
        if choice > weight:
            choice -= weight
        else:
            return key


class Game:
    """
    Attributes:
    -- width        : int               : The length of both the grid's sides in tiles.
    -- ditches_on   : bool              : Whether the player wants to turn on ditches.
    -- populations  : dict{str: int}    : Map from all keys to their #instances in the grid.
                                           The sum of the values should always be width ** 2.
    -- grid         : list{list{Tile}}  : (0, 0) is at the top left of the screen.
    -- pos          : Pair              : The player's current position.
    -- targets      : list{Tile}        : tiles containing the target letter for a round.
    -- trail        : set{Tile}         : tiles the player has visited in a round.

    -- chaser:      : Pair              : The position of an enemy chaser
    -- level:       : float             : number of levels completed by the player.
    -- basket       : dict{str: int}    : total times obtained for each letter.
    -- start        : float             : process time of the start of a round.
    """
    LOWERCASE = {key for key in 'abcdefghijklmnopqrstuvwxyz'}

    def __init__(self, width: int, keyset: dict = None):
        """

        """
        self.width = width
        self.ditches_on = tk.BooleanVar()
        self.ditches_on.set(False)

        if keyset is None:
            keyset = Game.LOWERCASE
        self.populations = {key: 0 for key in keyset}
        self.grid = [
            [Tile(Pair(x, y)) for x in range(width)]
            for y in range(width)]

        self.pos = Pair(width // 2, width // 2)
        self.targets = []
        self.trail = set()

        # initialize letters with random, balanced keys
        for row in self.grid:
            for tile in row:
                self.__shuffle_tile(tile)

        # Setup the first round's targets:
        self.chaser = Pair(0, 0)
        self.level = 0
        self.basket = dict.fromkeys(self.populations, 0)  # TODO: implement updates
        self.start = process_time()
        self.check_round_complete()

    def tile_at(self, pos: Pair):
        """
        Returns the tile at the given Pair coordinate.
        """
        if pos.in_range(self.width, self.width):
            return self.grid[pos.y][pos.x]
        else:
            return None

    def tile_at_pos(self):
        return self.grid[self.pos.y][self.pos.x]

    def tile_at_chaser(self):
        return self.tile_at(self.chaser)

    def __adjacent(self, pos: Pair):
        """
        Returns a dict from Tile objects adjacent to
        the tile at pos to their positions as Pair objects.
        """
        adj = [(1, 0), (1, -1), (0, -1), (-1, -1),
               (-1, 0), (-1, 1), (0, 1), (1, 1)]
        adj = [pos + Pair(offset[0], offset[1]) for offset in adj]
        tile_pos = {self.tile_at(pair): pair for pair in adj}
        if None in tile_pos:
            del tile_pos[None]
        return tile_pos

    def move(self, key: str):
        """
        If the key parameter matches one of the adjacent
        tiles' keys, the player moves to that tile's position.
        The tile being moved out of is added to trail.
        If the user is in a position from the last round's trail,
        they must first press any key to get unstuck.

        Returns whether the player completed a round with this move.
        """
        pos = self.tile_at_pos()
        if pos.ditch:
            # No movement is possible when the player
            # is in a ditch that hasn't been cleared.
            pos.ditch = False
            return False
        elif key not in self.populations.keys():
            return False  # Ignore keys not in the grid.

        # A dict from adjacent tiles to their positions:
        adj = self.__adjacent(self.pos)
        # Adjacent tiles with the same key as the key parameter:
        select = list(filter(lambda tile: tile.key.get() == key, adj))
        if select:  # If an adjacent key has a matching key:
            self.trail |= {self.tile_at_pos()}
            # The selected tile to move to:
            select = select[0]
            self.pos = adj[select]
            if select in self.targets:
                self.targets.remove(select)
            # debug: print(self.pos, select.key.get())
            return self.check_round_complete()
        else:
            return False

    def __wide_adjacent(self, tile: Tile):
        """
        Return a set of keys in the 5x5 ring around tile.
        This represents keys that cannot go in tile, since
        they would create an ambiguity in movement direction.
        """
        adj = []
        for y in range(-2, 3, 1):
            adj.extend([Pair(x, y) + tile.pos for x in range(-2, 3, 1)])
        del adj[12]  # The current position.
        adj = {self.tile_at(pair) for pair in adj}
        if None in adj:
            adj.remove(None)
        return {t.key.get() for t in adj}

    def __shuffle_tile(self, tile: Tile):
        """
        Randomizes the parameter tile's key,
        favoring less-common keys in the current grid.
        """
        lower = min(self.populations.values())
        adj = self.__wide_adjacent(tile)
        weights = {  # Gives zero weight to neighboring keys.
            key: 1 / (count - lower + 1) if key not in adj else 0
            for key, count in self.populations.items()}

        new_key = weighted_choice(weights)
        tile.key.set(new_key)
        self.populations[new_key] += 1

    def check_round_complete(self):
        """
        Should be called at the end of every move.
        Returns True if the player touched the last
        target for the current round in this move.
        """
        if self.targets:
            # The player has not yet touched
            # all tiles with the target key.
            return False

        self.level += 1
        now = process_time()
        elapsed = now - self.start
        self.start = now

        # Shuffle tiles from this round's trail:
        for tile in self.trail:
            self.populations[tile.key.get()] -= 1
            tile.key.set('')
        for tile in self.trail:
            self.__shuffle_tile(tile)

        # Get the new target key and
        # find tiles with matching keys:
        target = weighted_choice(self.populations)
        self.targets.clear()
        for row in self.grid:
            for tile in row:
                tile.ditch = False
                if tile.key.get() == target and tile.pos != self.pos:
                    self.targets.append(tile)
        # debug: self.targets = [self.targets[0], ]

        # Raise ditch flags for
        # trail tiles from this round:
        for tile in self.trail:
            tile.ditch = self.ditches_on.get()
        self.trail.clear()
        return True

    def move_chaser(self):
        """
        Moves the chaser closer to the player.
        Returns True if the chaser is on the player.
        """
        diff = self.pos - self.chaser
        if diff.x < -1:
            diff.x = -1
        if diff.x > 1:
            diff.x = 1
        if diff.y < -1:
            diff.y = -1
        if diff.y > 1:
            diff.y = 1
        self.chaser += diff
        return self.chaser == self.pos

    def chaser_speed(self):
        """
        Returns a speed in tiles per second
        """
        f = self.width ** 2 / len(self.populations)
        sub_level = 2 ** -(len(self.targets) / 0.3 / f)
        level = self.level + sub_level

        high = 2.7  # Tiles per second
        low = 0.75  # Tiles per second
        return (high-low)*(1 - 2 ** -(level/5.4)) + low

    def restart(self):
        """
        Resets the game.
        """
        self.populations = dict.fromkeys(self.populations, 0)

        self.pos = Pair(self.width // 2, self.width // 2)
        self.targets = []
        self.trail = set()

        self.chaser = Pair(0, 0)
        self.level = 0
        self.basket = dict.fromkeys(self.populations, 0)
        self.start = process_time()
        self.check_round_complete()


class SnaKeyGUI(tk.Tk):
    """
    Attributes:
        -- game     : Game
        -- cs       : dict{str: dict{str: str}}
        -- grid:    : Frame
    """
    color_schemes = {
        'default': {
            'tile':     {'bg': 'white',   'fg': 'black'},
            'pos':      {'bg': 'cyan',    'fg': 'black'},
            'target':   {'bg': 'yellow',  'fg': 'black'},
            'trail':    {'bg': 'gray80',  'fg': 'black'},
            'ditch':    {'bg': 'gray60',  'fg': 'black'},
            'ditch_target': {'bg': 'orange', 'fg': 'black'},
            'chaser':   {'bg': 'magenta', 'fg': 'black'},
        },
        '2': {
            'tile':     {'bg': 'black',   'fg': 'white'},
            'pos':      {'bg': 'blue',    'fg': 'white'},
            'target':   {'bg': 'gold',    'fg': 'white'},
            'trail':    {'bg': 'gray20',  'fg': 'white'},
            'ditch':    {'bg': 'gray40',  'fg': 'white'},
            'ditch_target': {'bg': 'brown', 'fg': 'white'},
            'chaser':   {'bg': 'maroon',  'fg': 'white'},
        },
    }

    def __init__(self, width: int = 20):
        super(SnaKeyGUI, self).__init__()
        self.title('Snakey - David Fong')
        self.game = Game(width)

        # Setup the grid display:
        grid = tk.Frame(self)
        for y in range(self.game.width):
            for x in range(self.game.width):
                tile = self.game.grid[y][x]
                tile.label = tk.Label(
                    grid, height=1, width=1,
                    textvariable=tile.key,
                )
                tile.label.grid(row=y, column=x)
        self.grid = grid
        grid.pack()

        # Setup the colors:
        self.cs = SnaKeyGUI.color_schemes['default']
        self.update_cs()

        # Bind key-presses and setup the menu:
        self.__setup_menu()
        self.bind('<Key>', self.move)

        # Start the chaser:
        self.move_chaser()

    def __setup_menu(self):
        """
        Sets up a menu-bar.
        """
        menu_bar = tk.Menu(self)
        self.configure(menu=menu_bar)

        # options menu:
        options = tk.Menu(menu_bar)
        menu_bar.add_cascade(label='options', menu=options)
        options.add_checkbutton(
            label='ditches', offvalue=False, onvalue=True,
            variable=self.game.ditches_on
        )

        # color menu:
        def update_cs(*args):
            self.update_cs(cs_string_var.get())
        colors = tk.Menu(menu_bar)
        menu_bar.add_cascade(label='colors', menu=colors)
        cs_string_var = tk.StringVar()
        cs_string_var.trace('w', update_cs)
        for scheme in SnaKeyGUI.color_schemes.keys():
            colors.add_radiobutton(
                label=scheme, value=scheme,
                variable=cs_string_var
            )

    def move(self, event):
        """

        """
        self.game.tile_at_pos().color(self.cs['trail'])

        # Execute the move in the internal representation
        #  and check if the move resulted in the round ending:
        if self.game.move(event.keysym):
            # If round over, update entire display.
            self.update_cs()

        # Highlight new position tile:
        self.game.tile_at_pos().color(self.cs['pos'])

    def update_cs(self, cs: str = None):
        """
        Updates all tiles based on the new color scheme.
        (or the current one if no new scheme is given).
        """
        if cs is None:
            cs = self.cs
        else:
            cs = SnaKeyGUI.color_schemes[cs]
            self.cs = cs

        # Recolor all tiles:
        for row in self.game.grid:
            for tile in row:
                tile.color(cs['tile'])
                # TODO: change this to RBG math in Tile:
                # if tile.ditch:
                #     tile.color(cs['ditch'])

        # Highlight the player's current position:
        self.game.tile_at_pos().color(cs['pos'])

        # Highlight tiles from the player's trail:
        for tile in self.game.trail:
            tile.color(cs['trail'])

        # Highlight tiles that need to be touched
        #  to complete the current round:
        for tile in self.game.targets:
            tile.color(cs['target'])
            # TODO: change this to RBG math in Tile:
            # if tile.ditch:
            #     tile.color(cs['ditch_target'])

        # Highlight the chaser's current position:
        self.game.tile_at_chaser().color(cs['chaser'])

    def move_chaser(self):
        """
        Moves the chaser toward the player
        and displays the changes in the GUI.
        """
        tile = self.game.tile_at_chaser()
        if tile in self.game.targets:
            tile.color(self.cs['target'])
        elif tile in self.game.trail:
            tile.color(self.cs['trail'])
        else:
            tile.color(self.cs['tile'])

        # Move the chaser in the internal representation:
        if self.game.move_chaser():
            # The chaser caught the player:
            self.game.tile_at_chaser().color(self.cs['chaser'])
            print('game over!')
            return
        else:
            # Loop the chaser while it
            # hasn't caught the player.
            self.game.tile_at_chaser().color(self.cs['chaser'])
            self.after(
                int(1000 // self.game.chaser_speed()),
                func=self.move_chaser
            )


if __name__ == '__main__':
    print({None: 'hi'})
    test = SnaKeyGUI()
    test.mainloop()
