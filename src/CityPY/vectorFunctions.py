import numpy as np


def get_norm_vector_of_surface(coordinates: np.array) -> np.ndarray:
    """calculates norm vector based on first 3 coordinates of polygon"""
    crossed = np.cross(coordinates[0] - coordinates[1],
                       coordinates[0] - coordinates[2])
    norm = np.linalg.norm(crossed)
    # p is a measure of precission. while coding, i had a test vector pair
    # only differing by one digit at the 16th decimal place therefore roundig to 12 decimal places
    p = 12
    if np.array_equal(crossed, np.array([0, 0, 0])):
        return None
    return np.around((1 / norm) * crossed, p)


def rotation_matrix_from_vectors(vec1: np.array, vec2: np.array) -> (np.ndarray | None):
    """this function was adapted from https://stackoverflow.com/a/59204638"""
    """ Find the rotation matrix that aligns vec1 to vec2
    :param vec1: A 3d "source" vector
    :param vec2: A 3d "destination" vector
    :return mat: A transform matrix (3x3) which when applied to vec1, aligns it with vec2.
    """
    a, b = (vec1 / np.linalg.norm(vec1)), (vec2 / np.linalg.norm(vec2))
    v = np.cross(a, b)
    c = np.dot(a, b)
    s = np.linalg.norm(v)
    kmat = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])

    return np.eye(3) + kmat + kmat.dot(kmat) * ((1 - c) / (s ** 2))
