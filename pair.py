from math import sqrt
from random import randrange


class Pair:
    """
    Represents a position in 2D grid space.
    All arguments or their contents must be integers.
    """
    def __init__(self, x=0, y: int = 0):
        if isinstance(x, tuple):
            self.x = x[0]
            self.y = x[1]
        elif isinstance(x, int) and isinstance(y, int):
            self.x = x
            self.y = y
        else:
            raise TypeError

    def in_bound(self, x_bound, y_bound):
        return 0 <= self.x < x_bound and 0 <= self.y < y_bound

    def norm(self):
        return sqrt(self.x ** 2 + self.y ** 2)

    def square_norm(self):
        abs_self = abs(self)
        return max(abs_self.x, abs_self.y)

    def linear_norm(self):
        return abs(self.x) + abs(self.y)

    @staticmethod
    def rand(bounds: int):
        """
        Returns a random pair with
        -bounds <= x <= bounds,
        -bounds <= x <= bounds.
        """
        return Pair(
            randrange(-bounds, bounds+1),
            randrange(-bounds, bounds+1))

    def ceil(self, radius: int):
        x = self.x
        y = self.y
        if self.x < -radius:
            x = -radius
        elif self.x > radius:
            x = radius
        if self.y < -radius:
            y = -radius
        elif self.y > radius:
            y = radius
        return Pair(x, y)

    def wall(self, width: int):
        """
        Returns a unit point in the direction of
        the closest wall bounded by width.
        """
        x = int(round(self.x / width * 2 - 1))
        y = int(round(self.y / width * 2 - 1))
        return Pair(x, y)

    def __abs__(self):
        return Pair(abs(self.x), abs(self.y))

    def __add__(self, other):
        if isinstance(other, Pair):
            return Pair(self.x + other.x, self.y + other.y)
        else:
            return NotImplemented

    def __iadd__(self, other):
        if isinstance(other, Pair):
            self.x += other.x
            self.y += other.y
            return self
        else:
            return NotImplemented

    def __sub__(self, other):
        if isinstance(other, Pair):
            return Pair(self.x - other.x, self.y - other.y)
        else:
            return NotImplemented

    def __neg__(self):
        return Pair(-self.x, -self.y)

    def __mul__(self, other):
        if isinstance(other, int):
            return Pair(self.x * other, self.y * other)
        elif isinstance(other, float):
            x = int(round(self.x * other))
            y = int(round(self.y * other))
            return Pair(x, y)
        else:
            return NotImplemented

    def __imul__(self, other):
        return self.__mul__(other)

    def __floordiv__(self, other):
        return self * (1/other)

    def __repr__(self):
        return f'({self.x},{self.y})'

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
