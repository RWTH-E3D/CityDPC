import numpy as np
from shapely import geometry as slyGeom

import vectorFunctions as vF

def find_party_walls(buildingLike_0: object, buildingLike_1: object):
    """takes to buildings and searches for party walls"""
    party_walls = []
    b_0_normvectors = _coor_dict_to_normvector_dict(buildingLike_0.walls)
    b_1_normvectors = _coor_dict_to_normvector_dict(buildingLike_1.walls)
    for gml_id_0, vector_0 in b_0_normvectors.items():
        for gml_id_1, vector_1 in b_1_normvectors.items():
            if np.array_equal(vector_0, vector_1) or np.array_equal(vector_0, -vector_1):
                # create rotaion matrix, that 3rd axis can be ignored
                # check if rotation is needed
                if np.array_equal(vector_0, np.array([0, 1, 0])) or np.array_equal(vector_0, -np.array([0, 1, 0])):
                    # rotation not needed
                    poly_0_rotated = buildingLike_0.walls[gml_id_0]
                    poly_1_rotated = buildingLike_1.walls[gml_id_1]
                else:
                    # needs to be rotated
                    rotation_matrix = vF.rotation_matrix_from_vectors(
                        vector_0, np.array([0, 1, 0]))
                    # rotate coordinates
                    poly_0_rotated = np.dot(
                        buildingLike_0.walls[gml_id_0], rotation_matrix)
                    poly_1_rotated = np.dot(
                        buildingLike_1.walls[gml_id_1], rotation_matrix)

                # check distance in rotated y direction (if distance is larger than 0.15 [uom] walls shouldn't be considered as party walls)
                if abs(np.mean(poly_0_rotated, axis=0)[1] - np.mean(poly_1_rotated, axis=0)[1]) > 0.15:
                    continue

                # delete 3rd axis
                poly_0_rotated_2D = np.delete(poly_0_rotated, 1, axis=1)
                poly_1_rotated_2D = np.delete(poly_1_rotated, 1, axis=1)
                # create shapely polygons
                p_0 = slyGeom.Polygon(poly_0_rotated_2D)
                p_1 = slyGeom.Polygon(poly_1_rotated_2D)
                # calculate intersection
                intersection = p_0.intersection(p_1)
                if not intersection.is_empty:
                    if intersection.area > 5:
                        id_0 = buildingLike_0.gml_id if not buildingLike_0.is_building_part else buildingLike_0.parent_gml_id + \
                            "/" + buildingLike_0.gml_id
                        id_1 = buildingLike_1.gml_id if not buildingLike_1.is_building_part else buildingLike_1.parent_gml_id + \
                            "/" + buildingLike_1.gml_id
                        party_walls.append(
                            [id_0, gml_id_0, id_1, gml_id_1, intersection.area])
                        # party_walls.append([gml_id_0, gml_id_1, intersection.area])
    return party_walls

def _coor_dict_to_normvector_dict(surface_dict: dict) -> dict:
    """calculates the normvectors of a surface dict based on the first 3 coordinates"""
    results = {}
    for gml_id, coordinates in surface_dict.items():
        vector = vF.get_norm_vector_of_surface(coordinates)
        if vector is None:
            # cross product of first 3 points is null vector -> points don't create a plane
            continue
        results[gml_id] = vector
    return results