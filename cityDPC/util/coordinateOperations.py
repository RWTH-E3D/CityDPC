import math


def calc_center(points: list):
    """calculating center of a 2d area"""
    # checking if start points equals endpoint and deleting it if so
    if points[0] == points[-1]:
        del points[-1]
    else:
        # last point is unequal to first point -> no need to delete point
        pass
    return [
        sum([p[0] for p in points]) / len(points),
        sum([p[1] for p in points]) / len(points),
    ]


def distance(p1, p2):
    """calculating the distance between two points"""
    return math.sqrt(((p1[0] - p2[0]) ** 2) + ((p1[1] - p2[1]) ** 2))


def normedDirectionVector(p1, p2):
    """calculating the normed direction vector between two points"""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.sqrt(dx**2 + dy**2)
    return [dx * 1 / length, dy * 1 / length]
