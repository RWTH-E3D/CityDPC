import numpy as np
import math


def get_norm_vector_of_surface(coordinates: np.array) -> np.ndarray:
    """calculates norm vector based on first 3 coordinates of polygon"""
    crossed = np.cross(coordinates[0] - coordinates[1],
                       coordinates[0] - coordinates[2])
    norm = np.linalg.norm(crossed)
    if np.array_equal(crossed, np.array([0, 0, 0])):
        return None
    return (1 / norm) * crossed


def rotate_polygon_around_point_in_x_y(rotation_center: list, polygon: list, angle: float) -> list:
    """rotates a polygon around a rotation center by an angle (in radians) in counter clockwise direction"""
    ox, oy, _ = rotation_center
    rotated = []
    for point in polygon:
        px, py, pz = point
        qx = ox + math.cos(angle) * (px - ox) - math.sin(angle) * (py - oy)
        qy = oy + math.sin(angle) * (px - ox) + math.cos(angle) * (py - oy)
        rotated.append([qx, qy, pz])
    return rotated