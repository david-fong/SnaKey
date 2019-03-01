from time import time

import colors as _colors
from pair import *
from languages import LANGUAGES
import tkinter as tk


VERSION_NUM = '1.'


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
        return f'{self.key.get()}:{self.pos}'


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
    -- language     : dict{str: str}    : Map from display keys to their alphabet strings.
    -- populations  : dict{str: int}    : Map from all display keys to their #occurances in the grid.
                                          The sum of the values should always be width ** 2.
    -- grid         : list{Tile}        : Row-order. Index 0 is at the top left of the screen.
    -- num_targets  : int               : Number of targets to maintain on the grid.

    GAME-PLAY OPTIONS -----------------------------------------------------------------------------
    -- lang_choice  : StringVar         : The language to use for the next game.
    -- kick_start   : BooleanVar        : Whether to start a new game with some losses.
    -- diagonals    : BooleanVar        : Whether the player and enemies can move in diagonals.
    -- sad_mode     : BooleanVar        : Makes the faces sad. Purely aesthetic.

    PLAYER POSITION DATA --------------------------------------------------------------------------
    -- targets      : list{Tile}        : tiles containing the target letter for a round.
    -- move_str     : str               : keys the user has recently pressed, which may map to a
                    :                   : display key in self.language.
    -- player       : Pair              : The player's current position.
    -- trail        : list{Tile}        : tiles the player has visited in a round.
    -- time_delta   : list{float}       : period of last few moves in seconds.
    -- time_start   : float             : start time since epoch of last move in seconds.

    SCORING & OPPONENTS ---------------------------------------------------------------------------
    -- chaser       : Pair              : The position of an enemy chaser.
    -- nommer       : Pair              : Competes with player to eat targets.
    -- heat         : int               : Burst level triggered when player touches target.
    -- runner       : Pair              : Runs away from player.
    -- score        : tk.IntVar         : number of targets reached by player.
    -- losses       : tk.IntVar         : number of targets reached by nommer.
    """
    target_thinness = 72
    faces = {
        'chaser': ':>',
        'player': ':|',
        'nommer': ':O',
        'runner': ':D',
    }

    def __init__(self, width: int, lang_choice: str = 'english lower'):
        """
        Keyset MUST have more than 20 unique keys that are
        recognized as part of tk.Event.keysym
        """
        # Create grid:
        self.width = width
        self.grid = []
        for y in range(width):
            self.grid.extend(
                [Tile(Pair(x, y)) for
                 x in range(width)])
        self.num_targets = (self.width ** 2) / Game.target_thinness

        # Initialize game-play options:
        self.lang_choice = tk.StringVar()
        self.lang_choice.set(lang_choice)
        self.__setup_options()

        # Initialize fields - See restart():
        self.language:      dict = None
        self.populations:   dict = None
        self.targets:       list = None
        self.move_str:       str = None
        self.player:        Pair = None
        self.trail:         list = None
        self.time_start:   float = None
        self.time_delta:    list = None
        self.chaser:        Pair = None
        self.nommer:        Pair = None
        self.heat:           int = None
        self.runner:        Pair = None
        self.score = tk.IntVar()
        self.losses = tk.IntVar()
        self.restart()

    def __setup_options(self):
        """
        Initialize options fields
        for the menu-bar in the GUI.
        """
        self.kick_start = tk.BooleanVar()
        self.kick_start.set(False)

        self.diagonals = tk.BooleanVar()
        self.diagonals.set(True)

        self.sad_mode = tk.BooleanVar()
        self.sad_mode.set(False)

    def restart(self):
        """
        Re-initializes all non-option aspects of the game.
        Assumes the keys of the board are all generated.
        """
        self.score.set(0)
        self.losses.set(0 if not self.kick_start.get() else 120)

        # initialize letters with random, balanced keys:
        self.language = LANGUAGES[self.lang_choice.get()].copy()
        self.populations = dict.fromkeys(self.language, 0)
        for tile in self.grid:
            self.__shuffle_tile(tile)

        # Erase the player and all enemies:
        if self.player is not None:
            self.__shuffle_tile(self.player_tile())
        if self.chaser is not None:
            self.__shuffle_tile(self.chaser_tile())
        if self.nommer is not None:
            self.__shuffle_tile(self.nommer_tile())
        if self.runner is not None:
            self.__shuffle_tile(self.runner_tile())

        # Set spawn points:
        self.targets = []
        self.move_str = ''
        self.player = Pair(self.width // 2, self.width // 2)
        self.trail = []
        self.time_start = time()
        self.time_delta = []
        self.chaser = Pair(0, 0)
        self.nommer = Pair(self.width-1, self.width-1)
        self.heat = 0
        self.runner = Pair(self.width-1, 0)

        # 'Clear' the location for the player:
        self.populations[self.player_tile().key.get()] -= 1
        self.populations[self.chaser_tile().key.get()] -= 1
        self.populations[self.nommer_tile().key.get()] -= 1
        self.populations[self.runner_tile().key.get()] -= 1

        # Spawn each character:
        self.player_tile().key.set(self.__get_face_key('player'))
        self.chaser_tile().key.set(self.__get_face_key('chaser'))
        self.nommer_tile().key.set(self.__get_face_key('nommer'))
        self.runner_tile().key.set(self.__get_face_key('runner'))

        # Generate the first round's targets:
        self.spawn_new_targets()

    def __trim_tail(self):
        """
        Controls the formula for the length of the trail.
        """
        net = self.score.get() - 3/4*self.losses.get()
        if net < 0 or len(self.trail) > (11 / 10) * net**(3 / 5):
            if self.trail:
                self.trail.pop(0)

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
            # Fail if trail is empty or is choked by enemy.
            if not self.trail or self.is_character(self.trail[-1]):
                return
            self.__shuffle_tile(self.player_tile())
            popped = self.trail.pop(-1)
            self.player = popped.pos
            self.populations[popped.key.get()] -= 1
            popped.key.set(self.__get_face_key('player'))
            return

        self.move_str += key
        adj = self.__adjacent(self.player)
        adj.remove(self.player_tile())
        # Adjacent tiles with the same key as the key parameter:
        dest_singleton = list(filter(
            lambda t: self.move_str.endswith(
                self.language[t.key.get()]),
            adj))

        # If the user pressed a key
        # corresponding to an adjacent tile:
        round_over = False
        if dest_singleton:
            self.time_delta.append(time() - self.time_start)
            self.time_start = time()
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
                self.score.set(self.score.get() + 1)
                base = self.num_targets
                self.heat = base * sqrt(self.heat / base + 1)
                round_over = self.spawn_new_targets()
            self.__trim_tail()

        return round_over

    def move_chaser(self):
        """
        Moves the chaser closer to the player.
        Returns True if the chaser is on the player.
        """
        target = self.player
        # Emulate the chaser 'missing'
        # the player when they move fast:
        if self.trail:
            # If time_delta is enemy_base_speed/equiv_point,
            # there is a 50/50 chance the enemy will miss.
            # Think of as how easy it is to make the enemy miss.
            # (pivot around 1: 'same speed' -> same weight)
            max_miss_weight = 5
            equiv_point = 5
            enemy_speed = self.enemy_base_speed()
            power = self.player_avg_period() * enemy_speed / equiv_point
            miss_weight = max_miss_weight ** (1 - power)
            target = weighted_choice({
                self.player: 1,
                self.trail[-1].pos: miss_weight})

        self.chaser += self.__enemy_diff(
            self.chaser,
            target=target,
            can_touch_player=True)
        key_var = self.chaser_tile().key
        if key_var.get() != self.__get_face_key('player'):
            # If the chaser did not land on the player:
            self.populations[key_var.get()] -= 1
        key_var.set(self.__get_face_key('chaser'))
        return self.chaser == self.player

    def move_nommer(self):
        """
        hist is the number of the most recent player moves
        used to determine the player's trajectory.
        Decreases the heat if > 1.
        """
        # If there aren't any near certain characters, head
        # for a nearby target that is not close to the player:
        targets = sorted(
            self.targets, key=lambda t:
            (self.player-t.pos).square_norm())
        targets = targets[len(targets)//3:]
        targets.sort(key=lambda t: (self.nommer-t.pos).square_norm())
        dest = targets[0].pos

        # Execute the move:
        if self.heat - 1 >= 0:
            self.heat -= 1
        self.nommer += self.__enemy_diff(
            origin=self.nommer,
            target=dest,
            can_touch_player=False
        )
        # Nommer may consume targets:
        key_var = self.nommer_tile().key
        if self.nommer_tile() in self.targets:
            self.targets.remove(self.nommer_tile())
            self.losses.set(self.losses.get() + 1)
            self.__trim_tail()
        self.populations[key_var.get()] -= 1
        key_var.set(self.__get_face_key('nommer'))
        return self.spawn_new_targets()

    def move_runner(self):
        """
        Just tries to run away from the player.
        If the player catches it, their losses
        due to the nommer will be halved.
        """
        # Check if the player caught up to the runner:
        was_caught = False
        if self.player_tile() in self.__adjacent(self.runner):
            was_caught = True
            self.losses.set(self.losses.get() * 2 // 3)

        # If within safe distance from player,
        # Avoid the nommer and chase the chaser:
        dist = (self.runner - self.player).norm()
        if dist >= self.width / 2:
            to_chaser = self.chaser - self.runner
            from_nommer = self.runner - self.nommer
            from_nommer *= self.width/9/from_nommer.norm()
            target = self.runner + to_chaser + from_nommer + Pair.rand(2)

        # Move toward a nearby corner. The two corners
        # closest to the player are out of the question:
        else:
            d1 = self.width // 5
            d2 = self.width - 1 - d1
            corners = [Pair(d1, d1), Pair(d2, d1),
                       Pair(d1, d2), Pair(d2, d2)]
            corners.sort(
                key=lambda p:
                (self.runner-p).norm(),
                reverse=True)
            corners.sort(key=lambda p: (self.player-p).square_norm())
            corners = corners[2:]
            corners.sort(
                key=lambda p:
                (self.runner-p).norm() -
                (self.player-p).norm())
            target = corners[0]
            # Bias away from the player if the are close:
            run = self.runner - self.player
            run *= ((target-self.runner).norm()**2/run.norm())**0.3
            target += run

        # Cleanup and execute the move:
        self.runner += self.__enemy_diff(
            origin=self.runner,
            target=target,
            can_touch_player=False
        )
        # Move twice if the player caught the runner
        # and one move isn't enough to escape again:
        if was_caught and self.player_tile() in self.__adjacent(self.runner):
            self.runner += self.__enemy_diff(
                origin=self.runner,
                target=target,
                can_touch_player=False
            )
        key_var = self.runner_tile().key
        self.populations[key_var.get()] -= 1
        key_var.set(self.__get_face_key('runner'))

    def spawn_new_targets(self):
        """
        Should be called at the end of every move by
        characters which can consume targets.
        Spawns more targets if necessary and returns
        those newly spawned in a list.

        Targets try to spawn spread out and not too
        close to the player or the nommer.
        """
        def bell(p1: Pair, p2: Pair, radius, lip=1.0, peak=0.0):
            dist = (p1 - p2).norm()
            return (peak-lip) * 2 ** -((2*dist/radius)**2) + lip

        # Get an appropriate number
        # of random keys for targets:
        new_targets = []
        while len(self.targets) < self.num_targets:
            # Favor tiles with few targets nearby:
            available = list(filter(
                lambda tile: tile not in self.targets and
                not self.is_character(tile), self.grid))
            weights = dict.fromkeys(available, 0.0)

            center = Pair(self.width//2, self.width//2)
            for t in weights:
                # Slight bias towards the center:
                weights[t] = bell(center, t.pos, 0.8*self.width, lip=0, peak=1)
                weights[t] += bell(self.player, t.pos, self.width/3, lip=0, peak=0.6)
                weights[t] += bell(self.nommer, t.pos, self.width/3, lip=0, peak=0.6)

            # Use the generated weights to get a new target:
            target = weighted_choice(weights)
            if target not in self.targets and not self.is_character(target):
                self.targets.append(target)
                new_targets.append(target)
                if target in self.trail:
                    self.trail.remove(target)
        return new_targets

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
        # Restrict to D-pad movement if necessary:
        if not self.diagonals.get():
            adj = list(filter(
                lambda t: t.pos.x - pos.x == 0
                or t.pos.y - pos.y == 0, adj))
        return adj

    @staticmethod
    def __enemy_diff_ceil(origin: Pair, target: Pair):
        """
        Returns a valid offset in the direction
        from origin to target. All enemy moves
        should pass through this function before
        being applied.

        Applies the following changes when necessary:
        -- projecting enemy diagonal moves onto axes.
        -- avoiding landing other enemies and the player.
        """
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
        target is the position of the tile targeted by
        the enemy at origin. Automatically shuffles the
        tile in the enemy's original position.

        Assumes that the enemy at origin
        currently has no position on the grid.
        """
        # Automatically shuffle the tile that
        # The enemy will leave behind:
        self.__shuffle_tile(self.tile_at(origin))

        # Get the offset in the direction of target:
        diff = self.__enemy_diff_ceil(origin, target)

        # If the player disabled diagonals:
        if not self.diagonals.get():
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
        if desired is None or self.is_character(desired):
            # Find all possible substitutes:
            adj = list(filter(
                lambda t: not self.is_character(t),
                self.__adjacent(origin)))
            # Favor substitutes in similar direction to that desired:
            weights = {
                t: 4**-(origin + diff*2 - t.pos).linear_norm()
                for t in adj[1:]}
            popped = weighted_choice(weights)
            return popped.pos - origin

        # Everything is fine:
        else:
            return diff

    def enemy_base_speed(self, curve_down: float = 0.0):
        """
        Returns a speed in tiles per second.
        Uses an upside-down bell-curve shape
        as a function of the sum of the absolutes
        of the the player's score and losses.

        curve_down is in the range[0, 1).
        compresses the effect of the dependant
        variable by using fractional powers.
        """
        obtained = self.score.get() + self.losses.get()
        obtained **= 1.0 - curve_down

        high = 1.5  # Tiles per second
        low = 0.35  # Tiles per second
        slowness = 25 * (20 ** 2 / Game.target_thinness)  # self.num_targets
        return (high-low) * (1-(2**-(obtained/slowness)**2)) + low

    def player_avg_period(self):
        if len(self.time_delta) > 5:
            self.time_delta = self.time_delta[-5:]
        total = sum(self.time_delta) + time() - self.time_start
        return total / (len(self.time_delta) + 1)

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

    def is_character(self, tile: Tile):
        """ tile must not be None. """
        return tile.key.get() not in self.language

    def __get_face_key(self, character: str):
        face = Game.faces[character]
        if character == 'nommer' and (
                self.heat >= self.num_targets + 1.5):
            face = '>' + face + ' '
        if self.sad_mode.get():
            return face.replace(':', ':\'')
        else:
            return face

    def __move_nommer(self, hist: int):
        """ Deprecated algorithm. """
        # If no targets are near nommer or the chaser,
        # predict a target location using the player's
        # trajectory, and try to beat them to it:
        # Not enough data. Just chase:
        if not self.trail or len(self.trail) < hist:
            dest = self.player
        else:
            dest = self.player - self.trail[-1].pos
            for i in range(-hist, -1):
                # Weights of past player moves decrease linearly:
                dest += (self.trail[i+1].pos - self.trail[i].pos) * (i+hist)
            # Try to go further ahead of player when player is far away:
            dest *= sqrt((self.player - self.nommer).norm())
            dest *= 2 / sum(range(1, hist + 1))
            dest += self.player
        return dest


class SnaKeyGUI(tk.Tk):
    """
    Attributes:
    -- game             : Game
    -- cs               : dict{str: dict{str: str}}
    -- grid:            : Frame

    -- restart_button   : tk.Button
    -- pause_button     : tk.Button
    """

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
                    textvariable=tile.key,
                    font=('system', 9, 'bold'),)
                tile.label.grid(
                    row=y, column=x, ipadx=4,
                    padx=1, pady=1)
        self.grid = grid
        grid.pack()

        # Bind key-presses and setup the menu:
        self.__setup_status_bar()
        self.__setup_menu()

        # Setup the colors:
        self.cs = _colors.color_schemes['dark - nw']
        self.update_cs()

        # Start the chaser:
        self.bind('<Key>', self.move_player)
        self.chaser_cancel_id: int = None
        self.nommer_cancel_id: int = None
        self.runner_cancel_id: int = None
        self.__pause(force_to=False)

    def __setup_status_bar(self):
        """
        Sets up buttons to restart and pause the game.
        Sets up labels to display the player's score and losses.
        """
        bar = tk.Frame(self)

        # Setup the restart button:
        self.restart_button = tk.Button(
            bar,
            text='restart', width=8,
            command=self.__restart,
            relief='ridge', bd=1, )
        self.restart_button.grid(row=0, column=0)

        # Setup the pause button:
        self.pause_button = tk.Button(
            bar,
            text='pause', width=8,
            command=self.__pause,
            relief='ridge', bd=1, )
        self.pause_button.grid(row=0, column=1)

        # Setup the score label:
        score_text = tk.Label(bar, text='  score:')
        score_text.grid(row=0, column=2)
        score = tk.Label(
            bar, width=2,
            textvariable=self.game.score, )
        score.grid(row=0, column=3)

        # Setup the losses label:
        losses_text = tk.Label(bar, text='  losses:')
        losses_text.grid(row=0, column=4)
        losses = tk.Label(
            bar, width=2,
            textvariable=self.game.losses, )
        losses.grid(row=0, column=5)

        bar.pack()

    def __setup_menu(self):
        """
        Sets up a menu-bar with options to:
        -- Edit game options.
        -- Change the color scheme.
        """
        menu_bar = tk.Menu(self)
        self.configure(menu=menu_bar)

        # Controls menu:
        menu_bar.add_command(
            label='how to play',
            command=self.__print_controls, )

        # Language menu:
        language_menu = tk.Menu(menu_bar)
        for language in LANGUAGES:
            language_menu.add_radiobutton(
                label=language, value=language,
                variable=self.game.lang_choice, )
        menu_bar.add_cascade(label='language', menu=language_menu)

        # Color scheme menu:
        def update_cs(*_):
            self.update_cs(cs_string_var.get())

        colors_menu = tk.Menu(menu_bar)
        cs_string_var = tk.StringVar()
        cs_string_var.trace('w', update_cs)
        for scheme in _colors.color_schemes.keys():
            colors_menu.add_radiobutton(
                label=scheme, value=scheme,
                variable=cs_string_var, )
        menu_bar.add_cascade(label='colors', menu=colors_menu)

        # Options menu:
        options_menu = tk.Menu(menu_bar)
        for name, var in {
                'kick-start':   self.game.kick_start,
                'diagonals':    self.game.diagonals,
                'sad mode':     self.game.sad_mode, }.items():
            options_menu.add_checkbutton(
                label=name,
                offvalue=False,
                onvalue=True,
                variable=var, )
        menu_bar.add_cascade(label='options', menu=options_menu)

    def move_player(self, event):
        """
        Updates the player's position in the internal
        representation and make the corresponding display
        changes to the GUI for the player to see.
        """
        init_pos = self.game.player_tile()
        trail_tail = init_pos if not self.game.trail else self.game.trail[0]

        # Execute the move in the internal representation
        new_targets = self.game.move_player(event.keysym)
        init_pos.color(
            self.cs['tile']  # <- If backtrack.
            if init_pos not in self.game.trail
            else self.cs['trail'])

        # Update if the trail did not lengthen:
        if (trail_tail not in self.game.trail and
                not self.game.is_character(trail_tail)):
            trail_tail.color(self.cs['tile'])

        # Check if new targets spawned:
        if new_targets:
            for target in new_targets:
                target.label.configure(self.cs['target'])

        # Highlight new position tile:
        self.game.player_tile().color(self.cs['player'])

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
                int(1000 / self.game.enemy_base_speed()),
                func=self.move_chaser
            )

    def move_nommer(self):
        """
        Gains a short speed burst when
        the player reaches targets.
        """
        self.__erase_enemy(self.game.nommer_tile())

        trail_tail = None
        if self.game.trail:
            trail_tail = self.game.trail[0]

        # Perform the move in the internal representation:
        new_targets = self.game.move_nommer()
        if new_targets:
            for target in new_targets:
                target.label.configure(self.cs['target'])

        # Player losses caused by nommer may shorten the player's trail:
        if trail_tail is not None and trail_tail not in self.game.trail:
            trail_tail.color(self.cs['tile'])

        self.game.nommer_tile().color(self.cs['nommer'])
        burst = self.game.heat / 5 + 1
        self.nommer_cancel_id = self.after(
            int(1000 / self.game.enemy_base_speed(curve_down=0.05) / burst),
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
        speedup = 2.8   # The maximum frequency multiplier.
        power = 5.5     # Increasing this shrinks high-urgency range.
        urgency = (speedup-1) / (g.width**power)
        urgency *= (g.width+1 - (g.runner-g.player).square_norm()) ** power
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

    def __restart(self):
        self.__pause(force_to=True)

        # Trigger a restart in the internal implementation:
        self.game.restart()
        self.update_cs()

        # Unfreeze player and enemy movement:
        self.__pause(force_to=False)
        self.pause_button['state'] = 'normal'

    def __pause(self, force_to: bool = None):
        """
        Setting force_to to True will pause the game,
        and setting it to False will un-pause it. If
        left as none, it will behave as if the player
        pressed the button to toggle a frozen game-state.
        """
        if force_to is True:
            self.pause_button['text'] = 'pause'
            self.__pause()
            return
        elif force_to is False:
            # Rebind the pause button for the player
            # in case it was unbound due to game-over:
            self.pause_button['text'] = 'un-pause'
            self.__pause()
            return

        # Change to the paused state:
        if self.pause_button['text'] == 'pause':
            self.pause_button.configure(
                text='un-pause',
                bg='SystemButtonHighlight', )
            # Disable player movement:
            self.unbind('<Key>')
            self.after_cancel(self.chaser_cancel_id)
            self.after_cancel(self.nommer_cancel_id)
            self.after_cancel(self.runner_cancel_id)

        # Change to the un-paused state:
        else:
            self.pause_button.configure(
                text='pause',
                bg='SystemButtonFace', )
            # Unfreeze player and enemy movement:
            self.bind('<Key>', self.move_player)
            self.chaser_cancel_id = self.after(800, self.move_chaser)
            self.nommer_cancel_id = self.after(150, self.move_nommer)
            self.runner_cancel_id = self.after(500, self.move_runner)

    def __print_controls(self):
        """
        Pauses the game while a popup window
        with an explanation of the game appears.
        """
        self.__pause(force_to=True)
        self.pause_button['state'] = 'disabled'
        self.restart_button['state'] = 'disabled'
        description = (
            ['player',
             'Type a letter in the eight tiles',
             'adjacent to your location to move.',
             'Eat highlighted tiles to gain score',
             'and grow your trail, which you can',
             'use to backtrack by pressing space.', ],
            ['chaser',
             'The game ends if the chaser catches',
             'you, so be quick on your toes! ...',
             '(or your fingers- whatever you type',
             'with- I don\'t judge)', ],
            ['nommer',
             'This guy will compete with you for',
             'food. While he\'s quite harmless,',
             'he hasn\'t paid his bill, and the',
             'chaser is after you for it!', ],
            ['runner',
             'What a cheeky little fellow. Maybe he',
             'just wants to play a game of tag? Wait-',
             'is that a stolen wallet in his hand?', ],
        )
        max_line_length = max([max(map(
            lambda line: len(line), character))
            for character in description])

        popup = tk.Toplevel(self, bd=3)
        popup.configure(self.cs['lines'])

        def __continue():
            popup.destroy()
            self.restart_button['state'] = 'normal'
            self.pause_button['state'] = 'normal'
        popup.protocol('WM_DELETE_WINDOW', __continue)
        for i in range(len(description)):
            character = description[i].copy()
            character[0] = self.game.faces[character[0]]
            label = tk.Label(
                popup, text='\n'.join(character),
                font=('system', 9, 'bold'), width=max_line_length, )
            # label.configure(self.cs[description[i][0]])
            label.configure(self.cs['tile'])
            label.grid(row=i, column=0, ipady=10, padx=3, pady=3)
        popup.mainloop()

    def game_over(self):
        """
        Disable most player actions except restart.
        """
        self.__pause(force_to=True)
        # Prevent un-pausing while player is dead:
        self.pause_button['state'] = 'disabled'

        # Highlight the restart button:
        self.restart_button['bg'] = 'SystemButtonHighlight'

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
        self.restart_button.configure(bg='SystemButtonFace')

        # Recolor all tiles:
        self.grid.configure(cs['lines'])
        for tile in self.game.grid:
            tile.color(cs['tile'])

        # Highlight tiles that need to be touched
        #  to complete the current round:
        for tile in self.game.targets:
            tile.color(cs['target'])

        # Highlight the player's current position:
        self.game.player_tile().color(cs['player'])
        for tile in self.game.trail:
            tile.color(cs['trail'])

        # Highlight the current positions of enemies:
        self.game.chaser_tile().color(cs['chaser'])
        self.game.nommer_tile().color(cs['nommer'])
        self.game.runner_tile().color(cs['runner'])


if __name__ == '__main__':
    root = SnaKeyGUI(20)
    root.mainloop()
