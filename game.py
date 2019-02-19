from random import choice

from webcolors import hex_to_rgb, name_to_hex, rgb_to_hex

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
        self.canvas_id = None

    def color(self, cs: dict):
        """ cs follows {'bg': _, 'text': _} """
        self.label.configure(cs)

    @staticmethod
    def shade(cs: dict):
        shaded = cs.copy()
        if '#' not in cs['bg']:
            shaded['bg'] = name_to_hex(cs['bg'])

        shade = 0x20
        rgb = hex_to_rgb(shaded['bg'])
        average = sum(rgb) // 3

        # Shading light colors makes them lighter:
        if average < shade:
            rgb = (val + shade if val + shade < 0xFF
                   else 0xFF for val in rgb)
        # Shading dark colors makes them darker:
        else:
            rgb = (val - shade if val >= shade
                   else 0x00 for val in rgb)
        shaded['bg'] = rgb_to_hex(rgb)
        return shaded


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
    -- populations  : dict{str: int}    : Map from all keys to their #instances in the grid.
                                           The sum of the values should always be width ** 2.

    -- grid         : list{list{Tile}}  : (0, 0) is at the top left of the screen.
    -- pos          : Pair              : The player's current position.
    -- targets      : list{Tile}        : tiles containing the target letter for a round.
    -- trail        : list{Tile}        : tiles the player has visited in a round.
    -- stuck        : bool              : Whether the Player entered their trail in the last move.

    -- ditches_on   : BooleanVar        : Whether the player wants to turn on ditches.
    -- chaser_diag  : BooleanVar        : Whether the chaser can move in diagonals.
    -- speedup      : BooleanVar        : Whether the chaser will speed up when finishing a round.
    -- sad_mode     : BooleanVar        : Makes the faces sad. Purely aesthetic.
    -- keygen_mode  : StringVar         : How to choose keys for a round. same letter? random?

    -- chaser:      : Pair              : The position of an enemy chaser
    -- level        : int               : number of levels completed by the player.
    -- basket       : dict{str: int}    : total times obtained for each letter.
    -- start        : float             : process time of the start of a round.
    """
    LOWERCASE = {key for key in 'abcdefghijklmnopqrstuvwxyz'}
    faces = {
        'chaser': ':>',
        'player': ':|',
        'nommer': ':O', }

    def __init__(self, width: int, keyset: set = None):
        """

        """
        # Create grid:
        self.width = width
        self.grid = []
        for y in range(width):
            self.grid.extend(
                [Tile(Pair(x, y)) for
                 x in range(width)])

        # initialize letters with random, balanced keys:
        if keyset is None:
            keyset = Game.LOWERCASE
        self.populations = dict.fromkeys(keyset, 0)
        for tile in self.grid:
            self.__shuffle_tile(tile)

        # Initialize game-play options:
        self.__setup_options()

        # Initialize fields:
        self.pos:       Pair = None
        self.targets:   list = None
        self.trail:     list = None
        self.stuck:     bool = None
        self.chaser:    Pair = None
        self.level:      int = None
        self.basket:    dict = None
        self.restart()

    def __setup_options(self):
        """
        Initialize options fields
        for the menu-bar in the GUI.
        """
        self.ditches_on = tk.BooleanVar()
        self.ditches_on.set(False)

        self.chaser_diag = tk.BooleanVar()
        self.chaser_diag.set(True)

        self.speedup = tk.BooleanVar()
        self.speedup.set(True)

        self.sad_mode = tk.BooleanVar()
        self.sad_mode.set(False)

        self.keygen_mode = tk.StringVar()
        self.keygen_mode.set('letter')

    def restart(self):
        """
        Re-initializes all non-option aspects of the game.
        Assumes the keys of the board are all generated.
        """
        self.populations = dict.fromkeys(self.populations, 0)

        self.pos = Pair(self.width // 2, self.width // 2)
        self.targets = []
        self.trail = []
        self.stuck = False

        if self.chaser is not None:
            self.__shuffle_tile(self.tile_at_chaser())
        self.chaser = Pair(0, 0)
        self.level = -1
        self.basket = dict.fromkeys(self.populations, 0)

        # Generate the first round's targets:
        self.tile_at_chaser().key.set(self.get_face_key('chaser'))
        self.tile_at_pos().key.set(self.get_face_key('player'))
        self.check_round_complete()

    def tile_at(self, pos: Pair):
        """
        Returns the tile at the given Pair coordinate.
        """
        if pos.in_range(self.width, self.width):
            return self.grid[self.width * pos.y + pos.x]
        else:
            return None

    def tile_at_pos(self):
        """ Just as a readability aid. """
        return self.grid[self.width * self.pos.y + self.pos.x]

    def tile_at_chaser(self):
        """ Just as a readability aid. """
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
        # The player wants to backtrack:
        if key == 'space' and self.trail:
            self.__shuffle_tile(self.tile_at_pos())
            popped = self.trail.pop(-1)
            self.pos = popped.pos
            self.populations[popped.key.get()] -= 1
            popped.key.set(self.get_face_key('player'))
            return

        tile = self.tile_at_pos()
        # The player just walked into their trail last move:
        if tile in self.trail and self.stuck:
            self.stuck = False
            return False
        elif key not in self.populations.keys():
            return False  # Ignore keys not in the grid.

        # A dict from adjacent tiles to their positions:
        adj = self.__adjacent(self.pos)
        # Adjacent tiles with the same key as the key parameter:
        select = list(filter(lambda t: t.key.get() == key, adj))

        # If the user pressed a key
        # corresponding to an adjacent tile:
        if select:
            # The selected tile to move to:
            select = select[0]

            self.__shuffle_tile(tile)
            self.trail.append(self.tile_at_pos())
            self.pos = adj[select]
            self.populations[select.key.get()] -= 1
            select_key = select.key.get()
            select.key.set(self.get_face_key('player'))

            if select in self.trail and self.ditches_on.get():
                self.stuck = True
            if select in self.targets:
                self.targets.remove(select)
                self.basket[select_key] += 1
                return self.check_round_complete()

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

    def __targets_per_round(self):
        """
        Average expected number of targets per round,
        assuming balanced populations of keys in the grid.
        """
        return self.width ** 2 / len(self.populations)

    def __shuffle_tile(self, tile: Tile):
        """
        Randomizes the parameter tile's key,
        favoring less-common keys in the current grid.

        Does not make required changes to populations
        based on the key of the tile being shuffled.
        These changes should be handled externally.
        """
        lower = min(self.populations.values())
        adj = self.__wide_adjacent(tile)
        weights = {  # Gives zero weight to neighboring keys.
            key: 4 ** (lower - count) if key not in adj else 0
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

        # This makes the chaser move faster
        if self.speedup.get():
            self.level += 1

        if self.keygen_mode.get() == 'letter':
            # Get the new target key and
            # find tiles with matching keys:
            target = weighted_choice(self.populations)
            self.targets = list(filter(
                lambda t: t.key.get() == target and
                t is not self.tile_at_pos(),
                self.grid))
        elif self.keygen_mode.get() == 'random':
            # Get an appropriate number
            # of random keys for targets:
            while len(self.targets) < self.__targets_per_round():
                target = choice(self.grid)
                if target not in self.targets:
                    self.targets.append(target)
        # debug = self.targets = choice(self.targets)

        self.trail.clear()
        return True

    def move_chaser(self):
        """
        Moves the chaser closer to the player.
        Returns True if the chaser is on the player.
        """
        # The chaser changes keys in its wake:
        self.__shuffle_tile(self.tile_at_chaser())

        diff = self.pos - self.chaser
        if diff.x < -1:
            diff.x = -1
        if diff.x > 1:
            diff.x = 1
        if diff.y < -1:
            diff.y = -1
        if diff.y > 1:
            diff.y = 1
        # The user can disable chaser diagonals:
        if diff.x != 0 and diff.y != 0 and not self.chaser_diag.get():
            if weighted_choice(
                    {True: abs(diff.x),
                     False: abs(diff.y)}):
                diff.x = 0
            else:
                diff.y = 0
        self.chaser += diff

        tile = self.tile_at_chaser()
        if tile.key.get() in self.populations:
            self.populations[tile.key.get()] -= 1
        tile.key.set(self.get_face_key('chaser'))
        return self.chaser == self.pos

    def chaser_speed(self):
        """
        Returns a speed in tiles per second
        """
        sub_level = 2 ** -(len(self.targets) / 0.3 /
                           self.__targets_per_round())
        level = self.level + sub_level

        high = 2.5  # Tiles per second
        low = 0.30  # Tiles per second
        slowness = 32
        return (high - low) * (1 - (2 ** -(level / slowness))) + low

    def get_face_key(self, face: str):
        face = Game.faces[face]
        return face[0]+'\''+face[1:] if \
            self.sad_mode.get() else face


class SnaKeyGUI(tk.Tk):
    """
    Attributes:
        -- game     : Game
        -- cs       : dict{str: dict{str: str}}
        -- grid:    : Frame
    """
    color_schemes = {
        'default': {
            'lines':    Tile.shade({'bg':       'white'}),
            'tile':     {'bg': 'white',         'fg': 'black'},
            'chaser':   {'bg': 'violet',        'fg': 'black'},
            'nommer':   {'bg': 'lime',          'fg': 'black'},
            'target':   {'bg': 'gold',          'fg': 'black'},
            'pos':      {'bg': 'deepSkyBlue',   'fg': 'black'},
            'trail':    {'bg': 'powderBlue',    'fg': 'black'},
        },
        'matrix': {
            'lines':    Tile.shade({'bg':       'black'}),
            'tile':     {'bg': 'black',         'fg': 'lightGrey'},
            'chaser':   {'bg': 'red',           'fg': 'black'},
            'nommer':   {'bg': 'red',           'fg': 'black'},
            'target':   {'bg': 'black',         'fg': 'lime'},
            'pos':      {'bg': 'limeGreen',     'fg': 'black'},
            'trail':    {'bg': 'darkGreen',     'fg': 'black'},
        },
        'sheep :>': {
            'lines':    Tile.shade({'bg':       'lawnGreen'}),
            'tile':     {'bg': 'lawnGreen',     'fg': 'darkGreen'},
            'chaser':   {'bg': 'orangeRed',     'fg': 'white'},
            'nommer':   {'bg': 'orangeRed',     'fg': 'white'},
            'target':   {'bg': 'limeGreen',     'fg': 'black'},
            'pos':      {'bg': 'white',         'fg': 'black'},
            'trail':    {'bg': 'greenYellow',   'fg': 'darkGreen'},
        },
    }
    pad = 1

    def __init__(self, width: int = 20):
        super(SnaKeyGUI, self).__init__()
        self.title('SnaKey - David F.')
        self.game = Game(width)

        # Setup the grid display:
        grid = tk.Frame(self)
        for y in range(self.game.width):
            for x in range(self.game.width):
                tile = self.game.tile_at(Pair(x, y))
                tile.label = tk.Label(
                    grid, height=1, width=1,
                    textvariable=tile.key, )
                tile.label.grid(
                    row=y, column=x, ipadx=3,
                    padx=SnaKeyGUI.pad, pady=SnaKeyGUI.pad)
        self.grid = grid
        grid.pack()

        # Setup the colors:
        self.cs = SnaKeyGUI.color_schemes['default']
        self.update_cs()

        # Bind key-presses and setup the menu:
        self.__setup_buttons()
        self.bind('<Key>', self.move)
        self.__setup_menu()

        # Start the chaser:
        self.chaser_cancel_id = self.after(2000, self.move_chaser)

    def __setup_buttons(self):
        """
        Sets up buttons to:
        -- Restart the game.
        """

        def restart():
            self.game.restart()
            self.update_cs()
            self.after_cancel(self.chaser_cancel_id)
            self.chaser_cancel_id = self.after(2000, self.move_chaser)

        self.restart = tk.Button(
            self, text='restart', command=restart,
            activebackground='gainsboro',
        )
        self.restart.pack()

    def __setup_menu(self):
        """
        Sets up a menu-bar with options to:
        -- Edit game options.
        -- Change the color scheme.
        """
        menu_bar = tk.Menu(self)
        self.configure(menu=menu_bar)

        # Options menu:
        options = tk.Menu(menu_bar)
        for name, var in {
                'ditches':      self.game.ditches_on,
                'chaser diag':  self.game.chaser_diag,
                'speedup':      self.game.speedup,
                'sad mode':     self.game.sad_mode, }.items():
            options.add_checkbutton(
                label=name,
                offvalue=False,
                onvalue=True,
                variable=var, )
        menu_bar.add_cascade(label='options', menu=options)

        # Keygen mode menu:
        keygen_mode = tk.Menu(menu_bar)
        for mode in ('letter', 'random'):
            keygen_mode.add_radiobutton(
                label=mode, value=mode,
                variable=self.game.keygen_mode, )
        menu_bar.add_cascade(label='keygen mode', menu=keygen_mode)

        # Color scheme menu:
        def update_cs(*_):
            self.update_cs(cs_string_var.get())

        colors = tk.Menu(menu_bar)
        cs_string_var = tk.StringVar()
        cs_string_var.trace('w', update_cs)
        for scheme in SnaKeyGUI.color_schemes.keys():
            colors.add_radiobutton(
                label=scheme, value=scheme,
                variable=cs_string_var, )
        menu_bar.add_cascade(label='colors', menu=colors)

    def move(self, event):
        """
        Updates the player's position in the internal
        representation and make the corresponding display
        changes to the GUI for the player to see.
        """
        init_pos = self.game.tile_at_pos()
        # Execute the move in the internal representation
        round_over = self.game.move(event.keysym)
        init_pos.color(self.cs['trail'])

        # and check if the move resulted in the round ending:
        if round_over:
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
        self.grid.configure(cs['lines'])
        for tile in self.game.grid:
            tile.color(cs['tile'])

        # Highlight the player's current position:
        self.game.tile_at_pos().color(cs['pos'])

        # Highlight tiles from the player's trail:
        for tile in self.game.trail:
            tile.color(cs['trail'])

        # Highlight tiles that need to be touched
        #  to complete the current round:
        for tile in self.game.targets:
            tile.color(cs['target'])

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
            self.game_over()
            return
        else:
            # Loop the chaser while it
            # hasn't caught the player.
            self.game.tile_at_chaser().color(self.cs['chaser'])
            self.chaser_cancel_id = self.after(
                int(1000 / self.game.chaser_speed()),
                func=self.move_chaser
            )

    def game_over(self):
        """
        Shows the player's score and then restarts the game.
        """
        # TODO: show the score:
        for _ in range(5):
            self.restart.flash()
        print('game over!', self.game.basket)


if __name__ == '__main__':
    test = SnaKeyGUI()
    test.mainloop()
