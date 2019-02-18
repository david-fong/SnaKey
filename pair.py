class Pair:
    """
    Represents a position in 2D grid space.
    """
    def __init__(self, x: int = 0, y: int = 0):
        if isinstance(x, tuple):
            pass
        elif isinstance(x, int) and isinstance(y, int):
            self.x = x
            self.y = y
        else:
            raise TypeError

    def in_range(self, x_bound, y_bound):
        return 0 <= self.x < x_bound and 0 <= self.y < y_bound

    def __add__(self, other):
        if isinstance(other, Pair):
            return Pair(self.x + other.x, self.y + other.y)
        else:
            return NotImplemented

    def __sub__(self, other):
        if isinstance(other, Pair):
            return Pair(self.x - other.x, self.y - other.y)
        else:
            return NotImplemented

    def __iadd__(self, other):
        if isinstance(other, Pair):
            self.x += other.x
            self.y += other.y
            return self
        else:
            return NotImplemented

    def __repr__(self):
        return f'({self.x}, {self.y})'

    def __hash__(self):
        return hash((self.x, self.y))

    def __eq__(self, other):
        if not isinstance(other, Pair):
            return False
        return self.x == other.x and self.y == other.y

    def __ne__(self, other):
        if isinstance(other, Pair):
            return self.x != other.x or self.y != other.y
        else:
            return NotImplemented

    def __lt__(self, other):
        if isinstance(other, Pair):
            return self.y < other.y or \
                   (
                    self.y == other.y and
                    self.x < other.x
                   )
        else:
            return NotImplemented

    def __gt__(self, other):
        if isinstance(other, Pair):
            return self.y > other.y or \
                   (
                    self.y == other.y and
                    self.x > other.x
                   )
        else:
            return NotImplemented

    def __le__(self, other):
        if isinstance(other, Pair):
            return self.y < other.y or \
                   (
                    self.y == other.y and
                    self.x <= other.x
                   )
        else:
            return NotImplemented

    def __ge__(self, other):
        if isinstance(other, Pair):
            return self.y > other.y or \
                   (
                    self.y == other.y and
                    self.x >= other.x
                   )
        else:
            return NotImplemented
