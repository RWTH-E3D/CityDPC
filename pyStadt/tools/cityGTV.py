"""
implementation of CityGTV (see https://doi.org/10.26868/25222708.2021.30169)
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
        _transform_abstract_building(
            building, inProj, outProj, offset, rotAngle, eleChange
        )
        for buildingPart in building.get_building_parts():
            _transform_abstract_building(
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


def _transform_abstract_building(
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
         ither Building or BuildingPart object to transform
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