from pair import *
import tkinter as tk


class Tile:
    """

    """

    def __init__(self, pos: Pair, key: str = ''):
        self.pos = pos
        self.key = tk.StringVar()
        self.key.set(key)
        self.label: tk.Label
        self.ditch = False
        self.canvas_id = None


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
    -- trail        : set{Tile}         : tiles the player has visited in a round.
    -- ditch        : set{Tile}         : tiles the player visited in the previous round.
    -- stuck        : bool              : Whether the player is in the ditch and has not pressed space.
    """
    LOWERCASE = {key for key in 'abcdefghijklmnopqrstuvwxyz'}

    def __init__(self, width: int = 20, keyset: dict = None):
        """

        """
        self.width = width

        if keyset is None:
            keyset = Game.LOWERCASE
        self.populations = {key: 0 for key in keyset}
        self.grid = [
            [Tile(Pair(x, y)) for x in range(width)]
            for y in range(width)]

        # initialize letters with random, balanced keys
        self.populations[''] = 0
        for row in self.grid:
            for tile in row:
                self.__shuffle_tile(tile)
        del self.populations['']

        self.pos = Pair(width // 2, width // 2)
        self.targets = []
        self.trail = set()

        # Setup the first round's targets:
        self.check_round_complete()

    def tile_at(self, pos: Pair):
        """
        Returns the tile at the given Pair coordinate.
        """
        if pos.in_range(self.width, self.width):
            return self.grid[pos.y][pos.x]
        else:
            return None

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
        they must have first pressed the space-bar to move.

        Returns whether the player completed a round with this move.
        """
        pos = self.tile_at(self.pos)
        if pos.ditch:
            # No movement is possible when the player
            # is in a ditch that hasn't been cleared.
            pos.ditch = key == ' '
            return False
        elif key not in self.populations.keys():
            return False  # Ignore keys not in the grid.

        # A dict from adjacent tiles to their positions:
        adj = self.__adjacent(self.pos)
        # Adjacent tiles with the same key as the key parameter:
        select = list(filter(lambda tile: tile.key.get() == key, adj))
        if select:  # If an adjacent key has a matching key:
            self.trail |= {self.pos}
            # The selected tile to move to:
            select = select[0]
            self.pos = adj[select]
            if select in self.targets:
                self.targets.remove(select)
            print(self.pos, select.key.get())
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
        adj = {self.tile_at(pair) for pair in adj}
        if None in adj:
            adj.remove(None)
        return {t.key.get() for t in adj}

    def __shuffle_tile(self, tile: Tile):
        """
        Randomizes the parameter tile's key,
        favoring less-common keys in the current grid.
        """
        self.populations[tile.key.get()] -= 1

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
        if not self.targets:
            # The player has not yet touched
            # all tiles with the target key.
            return False

        # Shuffle tiles from this round's trail:
        for tile in self.trail:
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
            self.targets.extend(list(filter(
                lambda t: t.key.get() == target, row)
            ))

        # Raise ditch flags for
        # trail tiles from this round:
        for tile in self.trail:
            tile.ditch = True
        self.trail.clear()
        return True


class SnakeyGUI(tk.Tk):
    """

    """
    color_schemes = {
        'default': {
            'bg': 'black',
            'fg': 'white',
            'text': 'black',
            'pos': 'cyan',
            'trail': 'gray80',
            'target': 'yellow'
        }
    }

    def __init__(self, width: int = None):
        super(SnakeyGUI, self).__init__()
        self.title('Snakey - David Fong')
        self.game = Game() if width is None else Game(width)
        self.cs = SnakeyGUI.color_schemes['default']

        # Setup the grid display:
        grid = tk.Frame(self, bg='black')
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

        # Bind key-presses:
        self.bind('<Key>', self.move)

    def move(self, event):
        """

        """
        if self.game.move(event.keysym):
            # TODO: a round has finished. update all tile displays:
            for tile in self.game.targets:
                tile.label.onfigure(fg=self.cs['fg'])

    def update_cs(self, cs: str = 'default'):
        """

        """
        cs = SnakeyGUI.color_schemes[cs]
        self.cs = cs
        for row in self.game.grid:
            for tile in row:
                tile.label.configure(bg=cs['bg'])


if __name__ == '__main__':
    print({None: 'hi'})
    test = SnakeyGUI()
    test.mainloop()
