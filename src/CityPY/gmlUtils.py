import numpy as np


def get_3D_posList_from_str(text: str) -> list:
    """convert string to a 3D list of coordinates"""
    coor_list = [float(x) for x in text.split()]
    # creating 3D coordinate array from 1D array
    coor_list = [list(x) for x in zip(
        coor_list[0::3], coor_list[1::3], coor_list[2::3])]
    return np.array(coor_list)
