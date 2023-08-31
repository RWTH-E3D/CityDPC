import numpy as np
import math
from shapely import geometry as slyGeom
import shapely

import vectorFunctions as vF

def find_party_walls(buildingLike_0: object, buildingLike_1: object) -> list:
    """takes to buildings and searches for party walls"""
    np.set_printoptions(suppress=True)
    party_walls = []
    b_0_surfaces = {**buildingLike_0.walls, **buildingLike_0.closure}
    b_1_surfaces = {**buildingLike_1.walls, **buildingLike_1.closure}
    # b_0_normvectors = _coor_dict_to_normvector_dict(b_0_surfaces)
    # b_1_normvectors = _coor_dict_to_normvector_dict(b_1_surfaces)
    for gml_id_0, surface_0 in b_0_surfaces.items():
        for gml_id_1, surface_1 in b_1_surfaces.items():
            # consider walls if there norm vectors equal or inverse or don't differ more than 15 degrees (= 0.9659 cos(rad))
            if np.array_equal(surface_0.normal_uni, surface_1.normal_uni) or \
               np.array_equal(surface_0.normal_uni, -surface_1.normal_uni) or \
               np.abs(np.dot(surface_0.normal_uni, surface_1.normal_uni)) > 0.9659:
                # check if rotation is needed
                if np.array_equal(surface_0.normal_uni, np.array([0, 1, 0])) or np.array_equal(surface_0.normal_uni, -np.array([0, 1, 0])):
                    # rotation not needed
                    poly_0_rotated = b_0_surfaces[gml_id_0].gml_surface_2array
                    poly_1_rotated = b_1_surfaces[gml_id_1].gml_surface_2array
                    rad_angle = None
                    target_y = b_0_surfaces[gml_id_0].gml_surface_2array[0][1]
                    rot_point = None
                else:
                    # needs to be rotated
                    t_surf_0 = b_0_surfaces[gml_id_0].gml_surface_2array
                    t_surf_1 = b_1_surfaces[gml_id_1].gml_surface_2array
                    # get delta in x- and y-direction for roation
                    # make sure that the vector between the 1st and 2nd point isn't [0 0 *]
                    if not (t_surf_0[0][0] == t_surf_0[1][0] and t_surf_0[0][1] == t_surf_0[1][1]):
                        delta_x = t_surf_0[0][0] - t_surf_0[1][0]
                        delta_y = t_surf_0[0][1] - t_surf_0[1][1]
                    else:
                        # in case the vector between the 1st and 2nd coordiante is only vertical
                        delta_x = t_surf_0[0][0] - t_surf_0[2][0]
                        delta_y = t_surf_0[0][1] - t_surf_0[2][1]

                    rad_angle = -math.atan2(delta_y, delta_x) if delta_x != 0 else math.pi/2
                    target_y = t_surf_0[0][1]
                    rot_point = t_surf_0[0]
                    poly_0_rotated = vF.rotate_polygon_around_point_in_x_y(rot_point, t_surf_0, rad_angle)
                    poly_1_rotated = vF.rotate_polygon_around_point_in_x_y(rot_point, t_surf_1, rad_angle)

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
                        if type(intersection) == shapely.Polygon:
                            threeD_contact = _get_collision_unrotated(intersection, rad_angle, target_y, rot_point)
                            party_walls.append(
                                [id_0, gml_id_0, id_1, gml_id_1, intersection.area, threeD_contact])

                        elif type(intersection) == shapely.GeometryCollection:
                            for section in intersection.geoms:
                                if type(section) == shapely.Polygon and section.area > 5:
                                    threeD_contact = _get_collision_unrotated(section, rad_angle, target_y, rot_point)
                                    party_walls.append(
                                        [id_0, gml_id_0, id_1, gml_id_1, section.area, threeD_contact])

    return party_walls


def _get_collision_unrotated(intersection_poly: shapely.Polygon, rot_angle: float, target_y: float, rot_point: list) -> list:
    """calculates the 3D coordinates of intersection"""
    xx, yy = intersection_poly.exterior.xy
    n = []
    for x, y in zip(xx.tolist(), yy.tolist()):
        n.append([x, target_y, y])
    if type(rot_angle) != None:
        return vF.rotate_polygon_around_point_in_x_y(rot_point, n, -rot_angle)
    else:
        return  n

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