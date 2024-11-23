from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from citydpc.dataset import Dataset
    from citydpc.core.obejct.abstractBuilding import AbstractBuilding


import numpy as np
import math
from shapely import geometry as slyGeom
import shapely


def get_party_walls(dataset: Dataset) -> list[str, str, str, str, float, list]:
    """checks for adjacent walls in dataset

    Parameters
    ----------
    dataset : Dataset
        dataset object containing all buildings that should be checked

    Returns
    -------
    list
        returns a list of all detected party walls as a list of
        [id of b0, id of w0, id of b1, id of w1, area, list of collision coordinates]
    """
    all_party_walls = []
    updNumOfWalls = []
    for i, building_0 in enumerate(dataset.get_building_list()):
        if building_0.gml_id not in updNumOfWalls:
            building_0.allWalls = len(
                building_0.get_surfaces(surfaceTypes=["WallSurface"])
            )
            building_0.freeWalls = building_0.allWalls
            updNumOfWalls.append(building_0.gml_id)
        polys_in_building_0 = []
        # get coordinates from all groundSurface of building geometry
        if building_0.has_3Dgeometry():
            for groundSurface in building_0.get_surfaces(["GroundSurface"]):
                polys_in_building_0.append(
                    {
                        "poly_id": groundSurface.polygon_id,
                        "coor": groundSurface.gml_surface_2array,
                        "parent": building_0,
                    }
                )

        # get coordinates from all groundSurface of buildingPart geometries
        if building_0.has_building_parts():
            for b_part in building_0.get_building_parts():
                if b_part.has_3Dgeometry():
                    if (
                        f"{building_0.gml_id}/{b_part.gml_id}"
                        not in updNumOfWalls
                    ):
                        b_part.allWalls = len(
                            b_part.get_surfaces(surfaceTypes=["WallSurface"])
                        )
                        b_part.freeWalls = b_part.allWalls
                        updNumOfWalls.append(
                            f"{building_0.gml_id}/{b_part.gml_id}"
                        )
                    for groundSurface in b_part.get_surfaces(
                        ["GroundSurface"]
                    ):
                        parent = dataset.get_building_by_id(
                            b_part.parent_gml_id
                        )
                        polys_in_building_0.append(
                            {
                                "poly_id": groundSurface.polygon_id,
                                "coor": groundSurface.gml_surface_2array,
                                "parent": parent,
                            }
                        )

        # self collision check
        # this includes all walls of the building (and building parts) geometry
        for j, poly_0 in enumerate(polys_in_building_0):
            p_0 = _create_buffered_polygon(poly_0["coor"])
            for poly_1 in polys_in_building_0[j + 1 :]:
                p_1 = slyGeom.Polygon(poly_1["coor"])
                if not p_0.intersection(p_1).is_empty:
                    party_walls = _find_party_walls(poly_0["parent"], poly_1["parent"])
                    if party_walls != []:
                        all_party_walls.extend(party_walls)

        # collision with other buildings
        for building_1 in dataset.get_building_list()[i + 1 :]:
            if building_1.gml_id not in updNumOfWalls:
                building_1.allWalls = len(
                    building_1.get_surfaces(surfaceTypes=["WallSurface"])
                )
                building_1.freeWalls = building_1.allWalls
                updNumOfWalls.append(building_1.gml_id)
            # collision with the building itself
            if building_1.has_3Dgeometry():
                for poly_0 in polys_in_building_0:
                    p_0 = _create_buffered_polygon(poly_0["coor"])
                    for poly_1 in building_1.get_surfaces(["GroundSurface"]):
                        p_1 = slyGeom.Polygon(poly_1.gml_surface_2array)
                        if not p_0.intersection(p_1).is_empty:
                            party_walls = _find_party_walls(
                                poly_0["parent"], building_1
                            )
                            if party_walls != []:
                                all_party_walls.extend(party_walls)
                            break

            # collsion with a building part of the building
            if building_1.has_building_parts():
                for b_part in building_1.get_building_parts():
                    if f"{building_1.gml_id}/{b_part.gml_id}" not in updNumOfWalls:
                        b_part.allWalls = len(
                            b_part.get_surfaces(surfaceTypes=["WallSurface"])
                        )
                        b_part.freeWalls = b_part.allWalls
                        updNumOfWalls.append(f"{building_1.gml_id}/{b_part.gml_id}")
                    if b_part.has_3Dgeometry():
                        for poly_0 in polys_in_building_0:
                            p_0 = _create_buffered_polygon(poly_0["coor"])
                            for poly_1 in b_part.get_surfaces(["GroundSurface"]):
                                p_1 = slyGeom.Polygon(poly_1.gml_surface_2array)
                                if not p_0.intersection(p_1).is_empty:
                                    # To-Do: building (or bp) with other building part
                                    party_walls = _find_party_walls(
                                        poly_0["parent"], b_part
                                    )
                                    if party_walls != []:
                                        all_party_walls.extend(party_walls)
                                    break
    return all_party_walls


def _find_party_walls(
    buildingLike_0: AbstractBuilding, buildingLike_1: AbstractBuilding
) -> list[str, str, str, str, float, list]:
    """takes to buildings and searches for party walls

    Parameters
    ----------
    buildingLike_0 : AbstractBuilding
        first building to check
    buildingLike_1 : AbstractBuilding
        second building to check

    Returns
    -------
    list
        returns a list of all detected party walls as a list of
        [id of b0, id of w0, id of b1, id of w1, area, list of collision coordinates]
    """
    np.set_printoptions(suppress=True)
    party_walls = []
    b_0_surfaces = buildingLike_0.get_surfaces(["WallSurface", "ClosureSurface"])
    b_1_surfaces = buildingLike_1.get_surfaces(["WallSurface", "ClosureSurface"])
    # b_0_normvectors = _coor_dict_to_normvector_dict(b_0_surfaces)
    # b_1_normvectors = _coor_dict_to_normvector_dict(b_1_surfaces)
    for surface_0 in b_0_surfaces:
        hitS0 = False
        for surface_1 in b_1_surfaces:
            hitS1 = False
            # consider walls if there norm vectors equal or inverse or don't differ
            # more than 15 degrees (= 0.9659 cos(rad))
            if (
                np.array_equal(surface_0.normal_uni, surface_1.normal_uni)
                or np.array_equal(surface_0.normal_uni, -surface_1.normal_uni)
                or np.abs(np.dot(surface_0.normal_uni, surface_1.normal_uni)) > 0.9659
            ):
                # check if rotation is needed
                if np.array_equal(
                    surface_0.normal_uni, np.array([0, 1, 0])
                ) or np.array_equal(surface_0.normal_uni, -np.array([0, 1, 0])):
                    # rotation not needed
                    poly_0_rotated = surface_0.gml_surface_2array
                    poly_1_rotated = surface_1.gml_surface_2array
                    rad_angle = None
                    target_y = surface_0.gml_surface_2array[0][1]
                    rot_point = None
                else:
                    # needs to be rotated
                    t_surf_0 = surface_0.gml_surface_2array
                    t_surf_1 = surface_1.gml_surface_2array
                    # get delta in x- and y-direction for roation
                    # make sure that the vector between the 1st and 2nd point
                    # isn't [0 0 *]
                    if not (
                        t_surf_0[0][0] == t_surf_0[1][0]
                        and t_surf_0[0][1] == t_surf_0[1][1]
                    ):
                        delta_x = t_surf_0[0][0] - t_surf_0[1][0]
                        delta_y = t_surf_0[0][1] - t_surf_0[1][1]
                    else:
                        # in case the vector between the 1st and 2nd coordiante is only
                        # vertical
                        delta_x = t_surf_0[0][0] - t_surf_0[2][0]
                        delta_y = t_surf_0[0][1] - t_surf_0[2][1]

                    rad_angle = (
                        -math.atan2(delta_y, delta_x) if delta_x != 0 else math.pi / 2
                    )
                    target_y = t_surf_0[0][1]
                    rot_point = t_surf_0[0]
                    poly_0_rotated = _rotate_polygon_around_point_in_x_y(
                        t_surf_0, rot_point, rad_angle
                    )
                    poly_1_rotated = _rotate_polygon_around_point_in_x_y(
                        t_surf_1, rot_point, rad_angle
                    )

                # check distance in rotated y direction (if distance is larger than
                # 0.15 [uom] walls shouldn't be considered as party walls)
                if (
                    abs(
                        np.mean(poly_0_rotated, axis=0)[1]
                        - np.mean(poly_1_rotated, axis=0)[1]
                    )
                    > 0.15
                ):
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
                        id_0 = (
                            buildingLike_0.gml_id
                            if not buildingLike_0.is_building_part
                            else buildingLike_0.parent_gml_id
                            + "/"
                            + buildingLike_0.gml_id
                        )
                        id_1 = (
                            buildingLike_1.gml_id
                            if not buildingLike_1.is_building_part
                            else buildingLike_1.parent_gml_id
                            + "/"
                            + buildingLike_1.gml_id
                        )
                        if type(intersection) is shapely.Polygon:
                            threeD_contact = _get_collision_unrotated(
                                intersection, rot_point, rad_angle, target_y
                            )
                            party_walls.append(
                                [
                                    id_0,
                                    surface_0.polygon_id,
                                    id_1,
                                    surface_1.polygon_id,
                                    intersection.area,
                                    threeD_contact,
                                ]
                            )
                            if not hitS0:
                                buildingLike_0.freeWalls -= 1
                            if not hitS1:
                                buildingLike_1.freeWalls -= 1
                            hitS0 = True
                            hitS1 = True

                        elif type(intersection) is shapely.GeometryCollection:
                            for section in intersection.geoms:
                                if (
                                    type(section) is shapely.Polygon
                                    and section.area > 5
                                ):
                                    threeD_contact = _get_collision_unrotated(
                                        section, rot_point, rad_angle, target_y
                                    )
                                    party_walls.append(
                                        [
                                            id_0,
                                            surface_0.polygon_id,
                                            id_1,
                                            surface_1.polygon_id,
                                            section.area,
                                            threeD_contact,
                                        ]
                                    )
                                    if not hitS0:
                                        buildingLike_0.freeWalls -= 1
                                    if not hitS1:
                                        buildingLike_1.freeWalls -= 1
                                    hitS0 = True
                                    hitS1 = True

    return party_walls


def _create_buffered_polygon(
    coordinates: np.ndarray, buffer: float = 0.15
) -> slyGeom.Polygon:
    """creates a buffered shapely polygon

    Parameters
    ----------
    coordinates : np.ndarray
        list of coordiantes that should be buffered
    buffer : float, optional
        buffer distance, by default 0.15

    Returns
    -------
    slyGeom.Polygon
        returns a buffered shapely Polygon
    """
    poly = slyGeom.Polygon(coordinates)
    return poly.buffer(buffer)


def _get_collision_unrotated(
    intersection_poly: shapely.Polygon,
    rotation_center: list,
    rot_angle: float,
    target_y: float,
) -> list:
    """calculates the 3D coordinates of intersection

    Parameters
    ----------
    intersection_poly : shapely.Polygon
        shapley Polygon that is in [x,z] plane
    rotation_center : list
        coordinate around which the polygon should be rotaded
    rot_angle : float
        roation angle
    target_y : float
        target y coordiante

    Returns
    -------
    list
        list of coordinates after rotation
    """
    xx, yy = intersection_poly.exterior.xy
    n = []
    for x, y in zip(xx.tolist(), yy.tolist()):
        n.append([x, target_y, y])
    if rot_angle is not None:
        return _rotate_polygon_around_point_in_x_y(
            n, rotation_center, -rot_angle
        )
    else:
        return n


def _rotate_polygon_around_point_in_x_y(
    polygon: list, rotation_center: list, rot_angle: float
) -> list:
    """rotates a polygon around a rotation center by an angle (in radians) in
    counter-clockwise direction

    Parameters
    ----------
    polygon : list
        list of coordinates
    rotation_center : list
        coordinate around which the polygon should be rotaded
    rot_angle : float
        roation angle

    Returns
    -------
    list
        list of coordinates after rotation
    """
    ox, oy, _ = rotation_center
    rotated = []
    for point in polygon:
        px, py, pz = point
        qx = ox + math.cos(rot_angle) * (px - ox) - math.sin(rot_angle) * (py - oy)
        qy = oy + math.sin(rot_angle) * (px - ox) + math.cos(rot_angle) * (py - oy)
        rotated.append([qx, qy, pz])
    return rotated
