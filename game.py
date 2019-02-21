from random import choice

import colors as _colors
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

    def color(self, cs: dict):
        """ cs follows {'bg': _, 'text': _} """
        self.label.configure(cs)

    def __repr__(self):
        return f'{self.key.get()}{self.pos}'


def weighted_choice(weights: dict):
    """
    Returns a key from the weights dict.
    Favors keys with greater value mappings

    Values in weights must be ints or floats.
    weights must not be empty.
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
    -- player       : Pair              : The player's current position.
    -- targets      : list{Tile}        : tiles containing the target letter for a round.
    -- trail        : list{Tile}        : tiles the player has visited in a round.

    GAME-PLAY OPTIONS -----------------------------------------------------------------------------
    -- enemy_diag   : BooleanVar        : Whether the enemies can move in diagonals.
    -- speedup      : BooleanVar        : Whether the chaser will speed up when finishing a round.
    -- sad_mode     : BooleanVar        : Makes the faces sad. Purely aesthetic.
    -- keygen_mode  : StringVar         : How to choose keys for a round. same letter? random?

    SCORING & OPPONENTS ---------------------------------------------------------------------------
    -- chaser       : Pair              : The position of an enemy chaser.
    -- nommer       : Pair              : Competes with player to eat targets.
    -- runner       : Pair              : Runs from player. That's it?
    -- level        : int               : number of levels completed by the player.
    -- basket       : dict{str: int}    : total times obtained for each letter.
    -- start        : float             : process time of the start of a round.
    """
    LOWERCASE = {key for key in 'abcdefghijklmnopqrstuvwxyz'}
    faces = {
        'chaser': ':>',
        'player': ': |',
        'nommer': ':O',
        'runner': ':D',
    }

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
        self.targets:   list = None
        self.player:    Pair = None
        self.trail:     list = None
        self.chaser:    Pair = None
        self.nommer:    Pair = None
        self.runner:    Pair = None
        self.level = tk.IntVar()
        self.basket:    dict = None
        self.restart()

    def __setup_options(self):
        """
        Initialize options fields
        for the menu-bar in the GUI.
        """
        self.enemy_diag = tk.BooleanVar()
        self.enemy_diag.set(True)

        self.speedup = tk.BooleanVar()
        self.speedup.set(True)

        self.sad_mode = tk.BooleanVar()
        self.sad_mode.set(False)

        self.keygen_mode = tk.StringVar()
        self.keygen_mode.set('random')

    def restart(self):
        """
        Re-initializes all non-option aspects of the game.
        Assumes the keys of the board are all generated.
        """
        self.level.set(-1)
        self.basket = dict.fromkeys(self.populations, 0)

        # Initialize the player:
        if self.player is not None:
            self.__shuffle_tile(self.player_tile())
        self.player = Pair(self.width // 2, self.width // 2)
        self.targets = []
        self.trail = []
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

        # Initialize the runner:
        if self.runner is not None:
            self.__shuffle_tile(self.runner_tile())
        self.runner = Pair(self.width-1, 0)
        self.populations[self.runner_tile().key.get()] -= 1
        self.runner_tile().key.set(self.__get_face_key('runner'))

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
        return self.grid[self.width * self.player.y + self.player.x]

    def chaser_tile(self):
        """ Just as a readability aid. """
        return self.grid[self.width * self.chaser.y + self.chaser.x]

    def nommer_tile(self):
        """ Just as a readability aid. """
        return self.grid[self.width * self.nommer.y + self.nommer.x]

    def runner_tile(self):
        """ Just as a readability aid. """
        return self.grid[self.width * self.runner.y + self.runner.x]

    def __adjacent(self, pos: Pair):
        """
        Returns a set of tiles
        adjacent to, and on top of pos.
        """
        adj = set()
        for y in range(-1, 2):
            adj |= {self.tile_at(pos+Pair(x, y))
                    for x in range(-1, 2)}
        if None in adj:
            adj.remove(None)
        return adj

    def move_player(self, key: str):
        """
        If the key parameter matches one of the adjacent
        tiles' keys, the player moves to that tile's position.
        The tile being moved out of is added to trail.

        Built into the fact that the chaser and nommer keys are
        not single characters, the player cannot move onto them.

        Returns whether the player completed a round with this move.
        """
        # The player wants to backtrack:
        if key == 'space':
            if (
                    not self.trail or
                    self.trail[-1].key.get()
                    not in self.populations):
                # Fail if trail is empty or is choked by enemy.
                return
            self.__shuffle_tile(self.player_tile())
            popped = self.trail.pop(-1)
            self.player = popped.pos
            self.populations[popped.key.get()] -= 1
            popped.key.set(self.__get_face_key('player'))
            return

        if key not in self.populations:
            return False  # Ignore keys not in the grid.

        adj = self.__adjacent(self.player)
        # Adjacent tiles with the same key as the key parameter:
        dest_singleton = list(filter(lambda t: t.key.get() == key, adj))

        # If the user pressed a key
        # corresponding to an adjacent tile:
        if dest_singleton:
            # The selected tile to move to:
            dest = dest_singleton[0]

            self.__shuffle_tile(self.player_tile())
            self.trail.append(self.player_tile())
            self.player = dest.pos
            dest_key = dest.key.get()
            self.populations[dest_key] -= 1
            dest.key.set(self.__get_face_key('player'))

            # Handle scoring if player touched a target:
            if dest in self.targets:
                self.targets.remove(dest)
                self.basket[dest_key] += 1
                return self.check_round_complete()
            elif len(self.trail) > sum(self.basket.values()):
                self.trail.pop(0)

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
            self.level.set(self.level.get() + 1)

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
                        target.key.get() in self.populations:
                    self.targets.append(target)
        # debug = self.targets = [choice(self.targets), ]

        self.trail.clear()
        return True

    def move_chaser(self):
        """
        Moves the chaser closer to the player.
        Returns True if the chaser is on the player.
        """
        self.chaser += self.__enemy_diff(
            self.chaser,
            target=self.player,
            can_touch_player=True)
        key_var = self.chaser_tile().key
        if key_var.get() != self.__get_face_key('player'):
            # If the chaser did not land on the player:
            self.populations[key_var.get()] -= 1
        key_var.set(self.__get_face_key('chaser'))
        return self.chaser == self.player

    def move_nommer(self, hist: int = 5):
        """
        hist is the number of the most recent player moves
        used to determine the player's trajectory.
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
                    [self.tile_at(origin + Pair(x, y))
                     for x in range(-radius, radius+1)])
            return list(filter(lambda tile: tile in self.targets, adj))
        # See if there are targets near nommer or other characters:
        dest = None
        for character in (self.nommer, self.chaser, self.runner):
            targets = __targets_in_range(character, 5)
            if targets:
                targets.sort(key=lambda t: (t.pos-self.nommer).norm())
                dest = targets[0].pos
                break

        # If no targets are near nommer or the player,
        # predict a target location using the player's
        # trajectory, and try to beat them to it:
        if dest is None:
            # Not enough data. Just chase:
            if not self.trail or len(self.trail) < hist:
                dest = self.player
            else:
                dest = self.player - self.trail[-1].pos
                for i in range(-hist, -1):
                    # Weights of past player moves decrease linearly:
                    dest += (self.trail[i+1].pos - self.trail[i].pos) * (i+hist)
                dest *= sqrt((self.player - self.nommer).norm())
                dest *= 2 / sum(range(1, hist + 1))

                print(dest)
                dest += self.player

        # Execute the move:
        self.nommer += self.__enemy_diff(
            origin=self.nommer,
            target=dest,
            can_touch_player=False
        )
        # Nommer may consume targets:
        key_var = self.nommer_tile().key
        if self.nommer_tile() in self.targets:
            self.targets.remove(self.nommer_tile())
            self.basket[key_var.get()] -= 1
            if self.trail:
                self.trail.pop(0)
        self.populations[key_var.get()] -= 1
        key_var.set(self.__get_face_key('nommer'))
        return self.check_round_complete()

    def move_runner(self):
        """
        Just tries to run away from the player.
        """
        safe_dist = self.width / 2
        dist = (self.player - self.runner).norm()

        # If within safe distance from player,
        # Avoid the nommer and chase the chaser:
        if dist >= safe_dist:
            to_chaser = self.chaser - self.runner
            from_nommer = self.runner - self.nommer
            from_nommer *= self.width/from_nommer.norm()
            target = self.runner + to_chaser + from_nommer

        else:
            d1 = self.width // 6
            d2 = self.width - 1 - d1
            corners = [Pair(d1, d1), Pair(d2, d1),
                       Pair(d1, d2), Pair(d2, d2)]
            # Move toward a nearby corner. The corner
            # closest to the player is out of the question:
            corners.sort(key=lambda p: (self.player-p).norm())
            corners = corners[2:]
            corners.sort(
                key=lambda p:
                (self.runner-p).norm() -
                (self.player-p).norm())
            run = self.runner-self.player
            target = corners[0] + run*((self.width/4)**-(run.norm()/5))

        # Cleanup and execute the move:
        self.runner += self.__enemy_diff(
            origin=self.runner,
            target=target,
            can_touch_player=False
        )
        key_var = self.runner_tile().key
        self.populations[key_var.get()] -= 1
        key_var.set(self.__get_face_key('runner'))

    @staticmethod
    def __get_diff(origin: Pair, target: Pair):
        diff = abs(target - origin)
        if target == origin:
            return Pair(0, 0)
        axis_percent = abs(diff.x-diff.y) / (diff.x+diff.y)
        diff = target - origin
        if weighted_choice({
                True: axis_percent,
                False: 1 - axis_percent}):
            if abs(diff.x) > abs(diff.y):
                diff.y = 0
            else:
                diff.x = 0
        return diff.ceil(radius=1)

    def __enemy_diff(self, origin: Pair, target: Pair,
                     can_touch_player: bool = False):
        """
        target is the position of the tile
        targeted by the enemy at origin.
        Automatically shuffles the tile in
        the enemy' original position.

        Applies the following changes:
        -- optionally projecting enemy diagonal moves onto axes.
        -- avoiding other enemies (and possibly the player).

        Assumes that the enemy at origin
        currently has no position on the grid.
        """
        # Automatically shuffle the tile that
        # The enemy will leave behind:
        self.__shuffle_tile(self.tile_at(origin))

        # Get the offset in the direction of target:
        diff = self.__get_diff(origin, target)

        # If the player disabled enemy_diag:
        if not self.enemy_diag.get():
            if weighted_choice({True: abs(diff.x), False: abs(diff.y)}):
                diff.y = 0
            else:
                diff.x = 0

        # Allow enemies like the chaser to touch the player:
        if can_touch_player and origin+diff == self.player:
            return diff

        # If the enemy would go out of bounds,
        # or touch another enemy or the player illegally:
        desired = self.tile_at(origin+diff)
        if (
                desired is None or
                desired.key.get() not in self.populations):
            # Find all possible substitutes:
            adj = list(filter(
                lambda t: t.key.get() in self.populations,
                self.__adjacent(origin)))
            # Restrict to D-pad movement if necessary:
            if not self.enemy_diag.get():
                adj = list(filter(
                    lambda t: t.pos.x - origin.x == 0
                    or t.pos.y - origin.y == 0, adj))
            # Favor substitutes in similar direction to that desired:
            weights = {t: 4**-(origin + diff - t.pos).norm() for t in adj[1:]}
            popped = weighted_choice(weights)
            return popped.pos - origin

        # Everything is fine:
        else:
            return diff

    def enemy_speed(self):
        """
        Returns a speed in tiles per second
        """
        sub_level = 2 ** -(len(self.targets) / 0.3 /
                           self.__targets_per_round())
        level = self.level.get() + sub_level

        high = 2.0  # Tiles per second
        low = 0.30  # Tiles per second
        slowness = 30
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
                    row=y, column=x, ipadx=4,
                    padx=SnaKeyGUI.pad, pady=SnaKeyGUI.pad)
        self.grid = grid
        grid.pack()

        # Bind key-presses and setup the menu:
        self.__setup_buttons()
        self.bind('<Key>', self.move_player)
        self.__setup_menu()

        # Setup the colors:
        self.cs = _colors.color_schemes['default']
        self.update_cs()

        # Start the chaser:
        self.chaser_cancel_id = self.after(2000, self.move_chaser)
        self.nommer_cancel_id = self.after(2330, self.move_nommer)
        self.runner_cancel_id = self.after(2660, self.move_runner)

    def __setup_buttons(self):
        """
        Sets up buttons to:
        -- Restart the game.
        """
        bar = tk.Frame(self)

        def restart():
            self.game.restart()
            self.bind('<Key>', self.move_player)
            self.update_cs()
            self.after_cancel(self.chaser_cancel_id)
            self.after_cancel(self.nommer_cancel_id)
            self.after_cancel(self.runner_cancel_id)
            self.chaser_cancel_id = self.after(2000, self.move_chaser)
            self.nommer_cancel_id = self.after(2330, self.move_nommer)
            self.runner_cancel_id = self.after(2660, self.move_runner)

        # Setup the restart button:
        self.restart = tk.Button(
            bar,
            text='restart',
            command=restart,
            relief='ridge', bd=1,
            activebackground='whiteSmoke',
        )
        self.restart.grid(row=0, column=0)

        # Setup the score label:
        level_text = tk.Label(bar, text='  level:')
        level_text.grid(row=0, column=1)
        level = tk.Label(
            bar, width=2,
            textvariable=self.game.level, )
        level.grid(row=0, column=2)

        bar.pack()

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
        for mode in ('random', 'letter', ):
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
        for scheme in _colors.color_schemes.keys():
            colors.add_radiobutton(
                label=scheme, value=scheme,
                variable=cs_string_var, )
        menu_bar.add_cascade(label='colors', menu=colors)

    def move_player(self, event):
        """
        Updates the player's position in the internal
        representation and make the corresponding display
        changes to the GUI for the player to see.
        """
        init_pos = self.game.player_tile()
        trail_tail = init_pos if not self.game.trail else self.game.trail[0]
        # Execute the move in the internal representation
        round_over = self.game.move_player(event.keysym)
        init_pos.color(
            self.cs['tile']  # <- If backtrack.
            if init_pos not in self.game.trail
            else self.cs['trail'])
        # Update if the trail did not lengthen:
        if trail_tail not in self.game.trail:
            trail_tail.color(self.cs['tile'])

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
            cs = _colors.color_schemes[cs]
            self.cs = cs

        # Recolor the menu:
        self.restart.configure(bg='SystemButtonFace')

        # Recolor all tiles:
        self.grid.configure(cs['lines'])
        for tile in self.game.grid:
            tile.color(cs['tile'])

        # Highlight tiles that need to be touched
        #  to complete the current round:
        for tile in self.game.targets:
            tile.color(cs['target'])

        # Highlight the player's current position:
        self.game.player_tile().color(cs['pos'])
        for tile in self.game.trail:
            tile.color(cs['trail'])

        # Highlight the current positions of enemies:
        self.game.chaser_tile().color(cs['chaser'])
        self.game.nommer_tile().color(cs['nommer'])
        self.game.runner_tile().color(cs['runner'])

    def move_chaser(self):
        """
        Moves the chaser toward the player
        and displays the changes in the GUI.
        """
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

        # Perform the move in the internal representation:
        trail_tail = None
        if self.game.trail:
            trail_tail = self.game.trail[0]
        if self.game.move_nommer():
            self.update_cs()
        if trail_tail is not None and trail_tail not in self.game.trail:
            trail_tail.color(self.cs['tile'])

        self.game.nommer_tile().color(self.cs['nommer'])
        self.nommer_cancel_id = self.after(
            int(1000 / self.game.enemy_speed()),
            func=self.move_nommer
        )

    def move_runner(self):
        """
        The runner moves faster when the player is near it.
        """
        self.__erase_enemy(self.game.runner_tile())

        # Perform the move in the internal representation:
        self.game.move_runner()

        self.game.runner_tile().color(self.cs['runner'])

        # Frequency multiplier increases
        # quadratically with distance from player:
        g = self.game
        speedup = 4.5   # The maximum frequency multiplier
        power = 6       # Increasing this makes urgency range 'smaller'
        urgency = (speedup-1) / (g.width**power)
        urgency *= (g.width+1 - (g.runner-g.player).norm()) ** power
        urgency += 1
        self.runner_cancel_id = self.after(
            int(1000 / urgency),
            func=self.move_runner
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
        # Disable player movement:
        self.unbind('<Key>')
        # TODO: show the score:

        # Make sure all enemies stop moving:
        self.after_cancel(self.chaser_cancel_id)
        self.after_cancel(self.nommer_cancel_id)
        self.after_cancel(self.runner_cancel_id)

        # Highlight the restart button:
        self.restart.configure(bg='SystemButtonHighlight')
        print('game over!', self.game.basket)


if __name__ == '__main__':
    root = SnaKeyGUI(20)
    root.mainloop()
