"""
implementation of CityGTV (see https://doi.org/10.26868/25222708.2021.30169)
most of the code is directly copied and only slightly
modified to match conventions
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyStadt.dataset import Dataset
    from pyStadt.core.obejcts.abstractBuilding import AbstractBuilding
    from pyStadt.core.obejcts.surfacegml import SurfaceGML
    from pyproj import Proj

import copy
from pyproj import transform
from math import sin, cos
import numpy as np


def transform_dataset(
    dataset: Dataset,
    inProj: Proj,
    outProj: Proj,
    refPIn: list,
    refPOut: list,
    newSrsName: str,
    rotAngle: float = 0,
    eleChange: float = 0,
    inplace: bool = False,
) -> Dataset:
    """transforms a dataset to a different coordinates system

    Parameters
    ----------
    dataset : Dataset
        pyStadt dataset
    inProj : Proj
        pyproj.Proj projection of inital coordinate system
    outProj : Proj
        pyproj.Proj projection of wanted coordinate system
    refPIn : tuple
        reference point in input CRS
    refPOut : tuple
        reference point in output CRS
    newSrsName : str
        str of new srsName for CityGML files
    rotAngle : float, optional
       rotation angle arount pivotPoint, by default 0
    eleChange : float, optional
        relative elevation change, by default 0
    inplace : bool, optional
         default False, if True edits current dataset, if False creates deepcopy

    Returns
    -------
    Dataset
        pyStadt dataset after transformation
    """

    if inplace:
        newDataset = dataset
    else:
        newDataset = copy.deepcopy(dataset)

    resX, resY = transform(inProj, outProj, refPIn[0], refPIn[1])
    pivT = [resX, resY]

    offset = np.subtract(np.array(refPOut), np.array(pivT))

    # transform buildings
    for building in newDataset.get_building_list():
        _transform_abstractBuilding(
            building, inProj, outProj, offset, rotAngle, eleChange
        )
        for buildingPart in building.get_building_parts():
            _transform_abstractBuilding(
                buildingPart, inProj, outProj, offset, rotAngle, eleChange
            )

    # transform file info
    for file in newDataset._files:
        [x0, y0] = file.lowerCorner
        res_x, res_y = transform(inProj, outProj, x0, y0)
        file.lowerCorner = (res_x, res_y)
        [x1, y1] = file.upperCorner
        res_x, res_y = transform(inProj, outProj, x1, y1)
        file.upperCorner = (res_x, res_y)

    newDataset.srsName = newSrsName

    return newDataset


def _transform_abstractBuilding(
    building: AbstractBuilding,
    inProj: Proj,
    outProj: Proj,
    offset: list,
    rotAngle: float,
    eleChange: float,
):
    """transforms Building or BuildingPart to given coordinate system

    Parameters
    ----------
    building : AbstractBuilding
        either Building or BuildingPart object to transform
    inProj : Proj
        pyproj.Proj projection of inital coordinate system
    outProj : Proj
        pyproj.Proj projection of wanted coordinate system
    offset : list
        offset for transformation
    rotAngle : float
        rotation angle arount pivotPoint
    eleChange : float
        relative elevation change
    """
    pivot = _get_surface_min_max_avg(list(building.roofs.values())[0])
    resX, resY = transform(inProj, outProj, pivot[0], pivot[1])
    pivot = [resX + offset[0], resY + offset[1]]

    for surfaceDict in [
        building.roofs,
        building.grounds,
        building.walls,
        building.closure,
    ]:
        for surface in surfaceDict.values():
            # update gml surface element
            surface.gml_surface = _transform_posList(
                surface.gml_surface,
                inProj,
                outProj,
                pivot,
                offset,
                rotAngle,
                eleChange,
            )
            surface.gml_surface_2array = np.reshape(surface.gml_surface, (-1, 3))
            surface.get_gml_area()
            surface.get_gml_orientation()
            surface.get_gml_tilt()

    # delete terrainIntersection
    building.terrainIntersections = None


def _transform_posList(
    posList: np.ndarray,
    inProj: Proj,
    outProj: Proj,
    pivot: list,
    offset: list,
    rotAngle: float,
    eleChange: float,
) -> np.ndarray:
    """transform a list of positions

    Parameters
    ----------
    posList : np.ndarray
        array of coordinates (1D array)
    inProj : Proj
        pyproj.Proj projection of inital coordinate system
    outProj : Proj
        pyproj.Proj projection of wanted coordinate system
    pivot : list
        pivot point
    offset : list
        offset for transformation
    rotAngle : float
        rotation angle arount pivotPoint
    eleChange : float
        relative elevation change

    Returns
    -------
    np.ndarray
        array of transformed coordinates
    """
    newPosList = []
    # iterate over coordinates and transform points
    for k in range(int(len(posList) / 3)):
        res_x, res_y = transform(inProj, outProj, posList[3 * k], posList[3 * k + 1])
        res_x = res_x + offset[0]
        res_y = res_y + offset[1]
        dx = (res_x - pivot[0]) * cos(rotAngle) - (res_y - pivot[1]) * sin(rotAngle)
        dy = (res_x - pivot[0]) * sin(rotAngle) + (res_y - pivot[1]) * cos(rotAngle)
        newPosList.append(dx + pivot[0])
        newPosList.append(dy + pivot[1])
        newPosList.append(posList[3 * k + 2] + eleChange)

    return np.array(newPosList)


def _get_surface_min_max_avg(surface: SurfaceGML) -> tuple[float, float]:
    """calculates the avg from the min and max value of a surface

    Parameters
    ----------
    surface : SurfaceGML
        surface for which the average should be calculated

    Returns
    -------
    tuple
        tuple of (avg x values, avg y values)
    """
    allX = surface.gml_surface[0::3]
    allY = surface.gml_surface[1::3]

    avgX = float((min(allX) + max(allX)) / 2)
    avgY = float((min(allY) + max(allY)) / 2)
    return (avgX, avgY)


def validate_dataset(dataset: Dataset) -> dict:
    """validate geometry of polygons of Dataset

    Parameters
    ----------
    dataset : Dataset
        pyStadt Dataset

    Returns
    -------
    dict
        nested dict with validation results
    """

    compRes = {}
    for building in dataset.get_building_list():
        res = _validate_abstractBuilding(building)
        compRes[f"{building.gml_id}_poly"] = res
        if building.has_building_parts():
            bpRes = {}
            for bp in building.get_building_parts():
                res = _validate_abstractBuilding(bp)
                bpRes[f"{bp.gml_id}_poly"] = res
            compRes[f"{building.gml_id}_bp"] = bpRes
    return compRes


def _validate_abstractBuilding(building: AbstractBuilding) -> dict:
    """validate geometry of polygons of Building or BuildingPart

    Parameters
    ----------
    building : AbstractBuilding
        either Building or BuildingPart object to transform

    Returns
    -------
    dict
        dict of validation results
    """

    valResult = {}
    for surfaceDict in [
        building.roofs,
        building.grounds,
        building.walls,
        building.closure,
    ]:
        for id, surface in surfaceDict.items():
            valResult[id] = _validate_polygon(surface)
    return valResult


class _Edge:
    """help class for storing info about polygon edges"""

    def __init__(self, head, tail):
        self.head = head
        self.tail = tail


def _is_poly_CPS(polyPoints: list) -> bool:
    """
    102: check if there is consecutive same points (CPS)??
    Actually it checks for all points (except the last point) in a ring that are
    repeated.
    Thus, it should be called as REPEATED_POINTS

    Parameters
    ----------
    polyPoints : list


    Returns
    -------
    bool
        True if points are repeated
    """
    points = polyPoints[:-1]  # take out the last point, which is same as the first.
    seen = []
    for pt in points:
        for s in seen:
            if np.array_equal(s, pt):
                return True
        seen.append(pt)
    return False


def _orientation(pA: list, pB: list, pC: list, dim: str, tol: float) -> -1 | 0 | 1:
    """
    Orientation determination
    from Jonathan Richard Schewchuk, http://www.cs.cmu.edu/~quake/robust.html
    Evaluating the sign of a determinant:
        | A.x-C.x   A.y-C.y |
        | B.x-C.x   B.y-C.y |
    which is the volume of vector CA, and CB.
    if the vloume is ZERO, then C is on line AB;
    if the volume is positive, then C is on the left side of line AB; negative for the
    right side.


    Parameters
    ----------
    pA : list
        point A
    pB : list
        point B
    pC : list
        point C
    dim : str
        dimension character
    tol : float
        tolerance

    Returns
    -------
    int
        one of [-1 | 0 | 1]
    """

    if dim == "x":
        res = (pA[1] - pC[1]) * (pB[2] - pC[2]) - (pB[1] - pC[1]) * (pA[2] - pC[2])
    elif dim == "y":
        res = (pA[0] - pC[0]) * (pB[2] - pC[2]) - (pB[0] - pC[0]) * (pA[2] - pC[2])
    elif dim == "z":
        res = (pA[0] - pC[0]) * (pB[1] - pC[1]) - (pB[0] - pC[0]) * (pA[1] - pC[1])
    if np.abs(res) < tol:
        return 0
    elif res > 0:
        return -1
    else:
        return 1


def _on_segment(pA: list, pB: list, pC: list, dim: str) -> bool:
    """check if the third point is on the segment of AB

    Parameters
    ----------
    pA : list
        point A
    pB : list
        point B
    pC : list
        point C
    dim : str
        dimension character

    Returns
    -------
    bool
        True if the third point is on the segment of AB
    """
    if dim == "x":
        if (pC[1] <= max(pA[1], pB[1]) and pC[1] >= min(pA[1], pB[1])) and (
            pC[2] <= max(pA[2], pB[2]) and pC[2] >= min(pA[2], pB[2])
        ):
            return True
    elif dim == "y":
        if (pC[0] <= max(pA[0], pB[0]) and pC[0] >= min(pA[0], pB[0])) and (
            pC[2] <= max(pA[2], pB[2]) and pC[2] >= min(pA[2], pB[2])
        ):
            return True
    elif dim == "z":
        if (pC[0] <= max(pA[0], pB[0]) and pC[0] >= min(pA[0], pB[0])) and (
            pC[1] <= max(pA[1], pB[1]) and pC[1] >= min(pA[1], pB[1])
        ):
            return True
    return False


def _is_seg_intersected(
    h0: list, t0: list, h1: list, t1: list, dim: str, tol: float
) -> bool:
    """
    Unfortunately, points are in 3-dimension, so we have to check the intersection at
    xy, yz, xz planes.
    [Important] Assume our points are on a same plane (pass the planar test), then
    true intersection happens to all three planes "xy,yz,xz" at the same time.

    Parameters
    ----------
    h0 : list
        head 0
    t0 : list
        tail 0
    h1 : list
        head 1
    t1 : list
        tail 1
    dim : str
        dimensions character
    tol : float
        tolerance float

    Returns
    -------
    bool
        True for detected intersections
    """
    orientation_CD_A = _orientation(h1, t1, h0, dim, tol)
    orientation_CD_B = _orientation(h1, t1, t0, dim, tol)
    orientation_AB_C = _orientation(h0, t0, h1, dim, tol)
    orientation_AB_D = _orientation(h0, t0, t1, dim, tol)
    # Normal cases: A&B are seperated by CD, while C&D are seperated by AB.
    if (orientation_CD_A != orientation_CD_B) and (
        orientation_AB_C != orientation_AB_D
    ):
        return True
    # for special cases, some points are alighed in a same line.
    elif orientation_CD_A == 0 and _on_segment(h1, t1, h0, dim):
        return True
    elif orientation_CD_B == 0 and _on_segment(h1, t1, t0, dim):
        return True
    elif orientation_AB_C == 0 and _on_segment(h0, t0, h1, dim):
        return True
    elif orientation_AB_D == 0 and _on_segment(h0, t0, t1, dim):
        return True
    else:
        return False


def _is_edge_intersected(edge0: _Edge, edge1: _Edge, tol: float) -> bool:
    """Check two edges if they are intersected, using function isSegIntersected(A,B,C,D)

    Parameters
    ----------
    edge0 : _Edge
        first _Edge
    edge1 : _Edge
        second _Edge
    tol : float
        tolearnce

    Returns
    -------
    bool
        True for detected intersections
    """
    if (
        _is_seg_intersected(edge0.head, edge0.tail, edge1.head, edge1.tail, "x", tol)
        and _is_seg_intersected(
            edge0.head, edge0.tail, edge1.head, edge1.tail, "y", tol
        )
        and _is_seg_intersected(
            edge0.head, edge0.tail, edge1.head, edge1.tail, "z", tol
        )
    ):
        return True
    else:
        return False


def _is_poly_self_intersected(polyPoints: list, tol: float = 0.001) -> bool:
    """104: check self intersection

    Parameters
    ----------
    polyPoints : list
        list of coordinates
    tol : float, optional
        tolerance, by default 0.001

    Returns
    -------
    bool
        True for self intersections
    """
    edgeList = []
    for i in range(len(polyPoints) - 1):
        newEdge = _Edge(polyPoints[i], polyPoints[i + 1])
        edgeList.append(newEdge)

    for i in range(len(edgeList) - 1):
        edge0 = edgeList[i]

        for j in range(i + 1, len(edgeList)):
            edge1 = edgeList[j]
            if np.array_equal(edge0.tail, edge1.head) or np.array_equal(
                edge1.tail, edge0.head
            ):
                # check the connection of the edge. skip its adjacent two edges.
                continue
            elif _is_edge_intersected(edge0, edge1, tol):
                # check the edge intersection issues.
                print("Intersected at [i,j]", i, " and ", j)
                return True
    return False


def _calc_dist_to_plane(p0: list, p1: list, p2: list, pt: list) -> float:
    """Calculate the distance from point pt to plane p0p1p2.

    Parameters
    ----------
    p0 : list
        point 0
    p1 : list
        point 1
    p2 : list
        point 2
    pt : list
        point to test

    Returns
    -------
    float
        distance from plane p0p1p2
    """
    normal = np.cross(p1 - p0, p2 - p0)
    magnitude = np.linalg.norm(normal)

    normal = np.true_divide(normal, magnitude)
    distance = np.absolute(np.dot(normal, pt - p0))
    return distance


def _is_poly_planar_DSTP(polyPoints: list, tol: float = 0.1) -> tuple(bool, float):
    """203: NON_PLANAR_POLYGON_DISTANCE_PLANE

    Parameters
    ----------
    polyPoints : list
        list of coordinates
    tol : float
        tolerance in degree, by default 0.1

    Returns
    -------
    float
        (True if max dist < tolerance,
         max distance of point from plane)
    """
    distance = 0.0
    tempDis = 0.0
    p0 = np.array(polyPoints[0])
    p1 = np.array(polyPoints[1])
    # ensure the three points are not aligned
    for i in range(2, len(polyPoints) - 1):
        p2 = np.array(polyPoints[i])
        tolOri = 0.001
        if (
            _orientation(p0, p1, p2, "x", tolOri) != 0
            or _orientation(p0, p1, p2, "y", tolOri) != 0
            or _orientation(p0, p1, p2, "z", tolOri) != 0
        ):
            break
    # test for the rest of points
    for t in range(i + 1, len(polyPoints) - 1):
        pt = np.array(polyPoints[t])
        distance = _calc_dist_to_plane(p0, p1, p2, pt)
        if distance > tol:
            if tempDis < distance:
                tempDis = distance

    return (tempDis < tol, tempDis)


def _calculate_angle_deviation(p0: list, p1: list, p2: list, p3: list) -> float:
    """
    calculate the angle between p3p0 and the normal of plane p0p1p2,
    then calculate the deviation to 90 degree.

    Parameters
    ----------
    p0 : list
        point 0
    p1 : list
        point 1
    p2 : list
        point 2
    p3 : list
        point 3

    Returns
    -------
    float
        deviation angle
    """
    # get the normal of plane p0p1p2
    normal = np.cross(p1 - p0, p2 - p0)
    magnitude = np.linalg.norm(normal)

    normal = np.true_divide(normal, magnitude)
    # get the vector p3p0
    vector = p3 - p0
    magnitude = np.linalg.norm(vector)
    vector = np.true_divide(vector, magnitude)
    # get angle and deviation to 90 degree
    angleDeviation = np.arccos(np.clip(np.dot(vector, normal), -1.0, 1.0)) / np.pi * 180
    return np.absolute(angleDeviation - 90)


def _is_poly_planar_normal(
    polyPoints: list, tolInDegree: float = 9
) -> tuple(bool, float):
    """
    204: NON_PLANAR_POLYGON_NORMALS_DEVIATION,
    checks if the max angel deviation < tolInDegree

    Parameters
    ----------
    polyPoints : list
        list of coordinates
    tolInDegree : float
        tolerance in degreee, by default 9

    Returns
    -------
    tuple
        True if max deviation < tolerance, max deviation
    """
    # -- Normal of the polygon from the first three points
    angleDeviation = 0
    tempDev = 0
    # -- Number of points, last point is as same as the first.
    nPolyPoints = len(polyPoints)
    # after filtering by Error code 101, a polygon at least has 4 point: p0 p1 p2 ~ p3
    p0 = np.array(polyPoints[0])
    p1 = np.array(polyPoints[1])
    # ensure the three points are not aligned
    for i in range(2, len(polyPoints) - 1):
        p2 = np.array(polyPoints[i])
        tolOri = 0.01
        if (
            _orientation(p0, p1, p2, "x", tolOri) != 0
            or _orientation(p0, p1, p2, "y", tolOri) != 0
            or _orientation(p0, p1, p2, "z", tolOri) != 0
        ):
            break

    # test for the rest of points
    for nt in range(i + 1, nPolyPoints - 1):
        p3 = np.array(polyPoints[nt])
        angleDeviation = _calculate_angle_deviation(p0, p1, p2, p3)
        if angleDeviation > tolInDegree:
            if tempDev < angleDeviation:
                tempDev = angleDeviation

    return (tempDev < tolInDegree, tempDev)


def _validate_polygon(surface: SurfaceGML):
    result = ""
    # usually, one polygon only contains one rings.
    # But still possible to have one external and multiple inner rings

    polyPoints = surface.gml_surface_2array
    # -- Number of points of the polygon (including the doubled first/last point)
    nPolyPoints = len(polyPoints)
    # 101 - TOO_FEW_POINTS
    # Four because the first point is doubled as the last one in the ring
    if nPolyPoints < 4:
        result += "Invalid: 101 TOO_FEW_POINTS.\n"
    # 102 – CONSECUTIVE_POINTS_SAME: Points in a ring should not be repeated
    if _is_poly_CPS(polyPoints):
        result += "Invalid: 102 CONSECUTIVE_POINTS_SAME.\n"

    # 103 – RING_NOT_CLOSED: Check if last point equal
    if not np.array_equal(polyPoints[0], polyPoints[-1]):
        result += "Invalid: 103 NOT_CLOSED.\n"

    # 104 – RING_SELF_INTERSECTION
    if _is_poly_self_intersected(polyPoints):
        result += "Invalid: 104: RING_SELF_INTERSECTION.\n"
        pass
    # -- Check if the points are planar, 203 and 204:
    # 203 – NON_PLANAR_POLYGON_DISTANCE_PLANE
    res, maxDis = _is_poly_planar_DSTP(polyPoints)
    if not res:
        result += (
            "Invalid: 203 NON_PLANAR_POLYGON_DISTANCE_PLANE."
            + f"\nDistance_Deviation_in_meter = {maxDis}\n"
        )
    # 204 – NON_PLANAR_POLYGON_NORMALS_DEVIATION
    res, maxDev = _is_poly_planar_normal(polyPoints)
    if not res:
        result += (
            "Invalid: '204 NON_PLANAR_POLYGON_NORMALS_DEVIATION."
            + f"\nAngle_Deviation_in_Degree = {maxDis}\n"
        )

    # currently no support for multi ring cases
    # therefore not needed for now

    # check the validation for multiple-ring cases
    # if len(polygon.ring) > 1:
    #     if areRingsIntersected(polygon):
    #         valid += "Invalid 201: INTERSECTION_RINGS.\n"
    #     if areRingsDuplicated(polygon):
    #         valid += "Invalid 202: DUPLICATED_RINGS.\n"
    #     if areInnerRingsOutside(polygon):
    #         valid += "Invalid 206: INNER_RING_OUTSIDE.\n"
    #     if areInnerRingsNested(polygon):
    #         valid += "Invalid 207: INNER_RINGS_NESTED.\n"
    #     if areRingsOrientationSame(polygon):
    #         valid += "Invalid 208: ORIENTATION_RINGS_SAME.\n"

    if result == "":
        result = "Valid"
    return result
