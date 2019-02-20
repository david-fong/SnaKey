from math import sqrt


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

    def in_bound(self, x_bound, y_bound):
        return 0 <= self.x < x_bound and 0 <= self.y < y_bound

    def norm(self):
        return sqrt(self.x ** 2 + self.y ** 2)

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
