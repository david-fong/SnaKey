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
    w_choice = uniform(0, sum(weights.values()))
    for key, weight in weights.items():
        if w_choice > weight:
            w_choice -= weight
        else:
            return key
    raise ArithmeticError('This should not happen.')


class Game:
    """
    Attributes:
    CORE ATTRIBUTES -------------------------------------------------------------------------------
    -- width        : int               : The length of both the grid's sides in tiles.
    -- populations  : dict{str: int}    : Map from all keys to their #instances in the grid.
                                          The sum of the values should always be width ** 2.
    -- grid         : list{Tile}        : Row-order. Index 0 is at the top left of the screen.

    PLAYER POSITION DATA --------------------------------------------------------------------------
    -- pos          : Pair              : The player's current position.
    -- targets      : list{Tile}        : tiles containing the target letter for a round.
    -- trail        : list{Tile}        : tiles the player has visited in a round.
    -- stuck        : bool              : Whether the Player entered their trail in the last move.

    GAME-PLAY OPTIONS -----------------------------------------------------------------------------
    -- ditches_on   : BooleanVar        : Whether the player wants to turn on ditches.
    -- enemy_diag   : BooleanVar        : Whether the enemies can move in diagonals.
    -- speedup      : BooleanVar        : Whether the chaser will speed up when finishing a round.
    -- sad_mode     : BooleanVar        : Makes the faces sad. Purely aesthetic.
    -- keygen_mode  : StringVar         : How to choose keys for a round. same letter? random?

    SCORING & OPPONENTS ---------------------------------------------------------------------------
    -- chaser       : Pair              : The position of an enemy chaser.
    -- nommer       : Pair              : Competes with player to eat targets.
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
        self.nommer:    Pair = None
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

        self.enemy_diag = tk.BooleanVar()
        self.enemy_diag.set(True)

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
        self.level = -1
        self.basket = dict.fromkeys(self.populations, 0)

        # Initialize the player:
        if self.pos is not None:
            self.__shuffle_tile(self.player_tile())
        self.pos = Pair(self.width // 2, self.width // 2)
        self.targets = []
        self.trail = []
        self.stuck = False
        self.populations[self.player_tile().key.get()] -= 1
        self.player_tile().key.set(self.__get_face_key('player'))

        # Initialize the chaser:
        if self.chaser is not None:
            self.__shuffle_tile(self.chaser_tile())
        self.chaser = Pair(0, 0)
        self.populations[self.chaser_tile().key.get()] -= 1
        self.chaser_tile().key.set(self.__get_face_key('chaser'))

        # Initialize the nommer:
        if self.nommer is not None:
            self.__shuffle_tile(self.nommer_tile())
        self.nommer = Pair(self.width-1, self.width-1)
        self.populations[self.nommer_tile().key.get()] -= 1
        self.nommer_tile().key.set(self.__get_face_key('nommer'))

        # Generate the first round's targets:
        self.check_round_complete()

    def tile_at(self, pos: Pair):
        """
        Returns the tile at the given Pair coordinate.
        """
        if pos.in_bound(self.width, self.width):
            return self.grid[self.width * pos.y + pos.x]
        else:
            return None

    def player_tile(self):
        """ Just as a readability aid. """
        return self.grid[self.width * self.pos.y + self.pos.x]

    def chaser_tile(self):
        """ Just as a readability aid. """
        return self.tile_at(self.chaser)

    def nommer_tile(self):
        """ Just as a readability aid. """
        return self.tile_at(self.nommer)

    def __adjacent(self, pos: Pair):
        """
        Returns a set of tiles
        adjacent to, and on top of pos.
        """
        offsets = []
        for y in range(-1, 2):
            offsets.extend([Pair(x, y) for x in range(-1, 2)])
        adj = {self.tile_at(pos + offset) for offset in offsets}
        if None in adj:
            adj.remove(None)
        return adj

    def move(self, key: str):
        """
        If the key parameter matches one of the adjacent
        tiles' keys, the player moves to that tile's position.
        The tile being moved out of is added to trail.
        If the user is in a position from the last round's trail,
        they must first press any key to get unstuck.

        Built into the fact that the chaser and nommer keys are
        not single characters, the player cannot move onto them.

        Returns whether the player completed a round with this move.
        """
        # The player wants to backtrack:
        if key == 'space':
            if not self.trail:
                # There is no trail yet!
                return
            # Do not allow the player
            # to backtrack onto an enemy:
            if self.trail[-1].key.get() not in self.populations:
                return
            self.__shuffle_tile(self.player_tile())
            popped = self.trail.pop(-1)
            self.pos = popped.pos
            self.populations[popped.key.get()] -= 1
            popped.key.set(self.__get_face_key('player'))
            return

        # The player just walked into their trail last move:
        if self.player_tile() in self.trail and self.stuck:
            self.stuck = False
            return False
        elif key not in self.populations:
            return False  # Ignore keys not in the grid.

        adj = self.__adjacent(self.pos)
        # Adjacent tiles with the same key as the key parameter:
        dest_singleton = list(filter(lambda t: t.key.get() == key, adj))

        # If the user pressed a key
        # corresponding to an adjacent tile:
        if dest_singleton:
            # The selected tile to move to:
            dest = dest_singleton[0]

            self.__shuffle_tile(self.player_tile())
            self.trail.append(self.player_tile())
            self.pos = dest.pos
            self.populations[dest.key.get()] -= 1
            select_key = dest.key.get()
            dest.key.set(self.__get_face_key('player'))

            # Handle ditches if player moved into their trail:
            if dest in self.trail and self.ditches_on.get():
                self.stuck = True
            # Handle scoring if player touched a target:
            if dest in self.targets:
                self.targets.remove(dest)
                self.basket[select_key] += 1
                return self.check_round_complete()

        return False

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
        def __wide_adjacent(origin: Tile):
            """
            Return a set of keys in the 5x5 ring around tile.
            This represents keys that cannot go in tile, since
            they would create an ambiguity in movement direction.
            """
            adjacent = []
            for y in range(-2, 3, 1):
                adjacent.extend(
                    [Pair(x, y) + origin.pos
                     for x in range(-2, 3, 1)])
            del adjacent[12]  # The current position.
            adjacent = {self.tile_at(pair) for pair in adjacent}
            if None in adjacent:
                adjacent.remove(None)
            return {t.key.get() for t in adjacent}

        lower = min(self.populations.values())
        adj = __wide_adjacent(tile)

        weights = {
            # Gives zero weight to neighboring keys.
            key: 4 ** (lower - count) if key not in adj else 0
            for key, count in self.populations.items()}

        new_key = weighted_choice(weights)
        tile.key.set(new_key)
        self.populations[new_key] += 1

    def check_round_complete(self):
        """
        Should be called at the end of every move.
        Spawns the next round's targets if the round ended.
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
                lambda t: t.key.get() == target,
                self.grid))
        elif self.keygen_mode.get() == 'random':
            # Get an appropriate number
            # of random keys for targets:
            while len(self.targets) < self.__targets_per_round():
                target = choice(self.grid)
                if target not in self.targets and \
                        target in self.populations:
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
        self.__shuffle_tile(self.chaser_tile())

        diff = (self.pos - self.chaser).ceil(radius=1)
        self.chaser += self.__enemy_diff(
            self.chaser, diff, can_touch_player=True
        )
        key_var = self.chaser_tile().key
        if key_var.get() in self.populations:
            # If the chaser did not land on the player:
            self.populations[key_var.get()] -= 1
        key_var.set(self.__get_face_key('chaser'))
        return self.chaser == self.pos

    def move_nommer(self):
        """

        """
        def __targets_in_range(origin: Pair, radius: int):
            """
            Returns a list of targets within radius tiles
            from origin (inclusive)- in order of distance-
            that are in the target list for the current round.
            """
            adj = []
            for y in range(-radius, radius+1):
                adj.extend(
                    [Pair(x, y) for x in
                     range(-radius, radius+1)])
            adj.sort(key=Pair.__abs__)
            adj = [self.tile_at(origin + pair) for pair in adj]
            return list(filter(lambda tile: tile in self.targets, adj))

        # Move toward targets within a quarter-grid range:
        targets = __targets_in_range(self.nommer, self.width//4)
        if targets:
            diff = targets[0].pos - self.nommer

        # Otherwise, if the player is more than
        # half of the grid away, follow the player:
        # (Or follow the player if the haven't moved):
        elif (self.pos - self.nommer).norm() > self.width/3 \
                or not self.trail:
            diff = self.pos - self.nommer

        # Follow the player to a target
        # using their trajectory:
        else:
            diff = self.pos.traj(
                list(map(lambda t: t.pos, self.trail)),
                hist=5, lookahead=self.width/5) - self.nommer

        diff = self.__enemy_diff(self.nommer, diff.ceil(1))
        self.__shuffle_tile(self.nommer_tile())

        # Execute the move:
        self.nommer += diff
        if self.nommer_tile() in self.targets:
            self.targets.remove(self.nommer_tile())
        key_var = self.nommer_tile().key
        self.populations[key_var.get()] -= 1
        key_var.set(self.__get_face_key('nommer'))

    def __enemy_diff(self, pos: Pair, diff: Pair,
                     can_touch_player: bool = False):
        """
        Applies the following changes:
        -- optionally projecting enemy diagonal moves onto axes.
        -- avoiding other enemies (and possibly the player).

        Assumes that the enemy at pos
        currently has no position on the grid.
        """
        if not self.enemy_diag.get():
            if weighted_choice({True:  abs(diff.x),
                                False: abs(diff.y)}):
                diff.x = 0
            else:
                diff.y = 0

        # Allow enemies like the chaser to touch the player:
        if pos + diff == self.pos and can_touch_player:
            return diff
        # If the enemy would touch another enemy or the player:
        elif (self.tile_at(pos + diff).key.get()
                not in self.populations):
            # Find a random free tile to move to:
            adj = list(self.__adjacent(pos))
            popped = choice(adj)
            adj.remove(popped)
            while adj:
                if popped.key.get() in self.populations:
                    break
                popped = choice(adj)
                adj.remove(popped)
            return popped.pos - pos
        # Everything is fine:
        else:
            return diff

    def enemy_speed(self):
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

    def __get_face_key(self, face: str):
        face = Game.faces[face]
        if self.sad_mode.get():
            return face.replace(':', ':\'')
        else:
            return face


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
            'nommer':   {'bg': 'chartreuse',    'fg': 'black'},
            'target':   {'bg': 'gold',          'fg': 'black'},
            'pos':      {'bg': 'deepSkyBlue',   'fg': 'black'},
            'trail':    {'bg': 'lightCyan',     'fg': 'black'},
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
            'chaser':   {'bg': 'orangeRed',     'fg': 'black'},
            'nommer':   {'bg': 'orangeRed',     'fg': 'black'},
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
        self.nommer_cancel_id = self.after(2000, self.move_nommer)

    def __setup_buttons(self):
        """
        Sets up buttons to:
        -- Restart the game.
        """

        def restart():
            self.game.restart()
            self.bind('<Key>', self.move)
            self.update_cs()

            self.after_cancel(self.chaser_cancel_id)
            self.chaser_cancel_id = self.after(2000, self.move_chaser)

            self.after_cancel(self.nommer_cancel_id)
            self.nommer_cancel_id = self.after(2000, self.move_nommer)

        self.restart = tk.Button(
            self, text='restart', command=restart,
            activebackground='whiteSmoke',
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
                'enemy diag':   self.game.enemy_diag,
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
        init_pos = self.game.player_tile()
        # Execute the move in the internal representation
        round_over = self.game.move(event.keysym)
        init_pos.color(self.cs['trail'])

        # and check if the move resulted in the round ending:
        if round_over:
            # If round over, update entire display.
            self.update_cs()

        # Highlight new position tile:
        self.game.player_tile().color(self.cs['pos'])

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
        self.game.player_tile().color(cs['pos'])

        # Highlight tiles from the player's trail:
        for tile in self.game.trail:
            tile.color(cs['trail'])

        # Highlight tiles that need to be touched
        #  to complete the current round:
        for tile in self.game.targets:
            tile.color(cs['target'])

        # Highlight the chaser's current position:
        self.game.chaser_tile().color(cs['chaser'])

    def move_chaser(self):
        """
        Moves the chaser toward the player
        and displays the changes in the GUI.
        """
        # TODO: remove debug line:
        print(sum(self.game.populations.values()), self.game.populations)
        self.__erase_enemy(self.game.chaser_tile())

        # Move the chaser in the internal representation:
        if self.game.move_chaser():
            # The chaser caught the player:
            self.game.chaser_tile().color(self.cs['chaser'])
            self.game_over()
            return
        else:
            # Loop the chaser while it
            # hasn't caught the player.
            self.game.chaser_tile().color(self.cs['chaser'])
            self.chaser_cancel_id = self.after(
                int(1000 / self.game.enemy_speed()),
                func=self.move_chaser
            )

    def move_nommer(self):
        """

        """
        self.__erase_enemy(self.game.nommer_tile())

        self.game.move_nommer()

        self.game.nommer_tile().color(self.cs['nommer'])
        self.nommer_cancel_id = self.after(
            int(1000 / self.game.enemy_speed()),
            func=self.move_nommer
        )

    def __erase_enemy(self, tile: Tile):
        if tile in self.game.targets:
            tile.color(self.cs['target'])
        elif tile in self.game.trail:
            tile.color(self.cs['trail'])
        else:
            tile.color(self.cs['tile'])

    def game_over(self):
        """
        Shows the player's score and then restarts the game.
        """
        self.unbind('<Key>')
        # TODO: show the score:
        for _ in range(3):
            self.restart.flash()
        print('game over!', self.game.basket)


if __name__ == '__main__':
    test = SnaKeyGUI()
    test.mainloop()
