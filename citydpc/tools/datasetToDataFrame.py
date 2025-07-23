from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from citydpc import Dataset
    from citydpc.core.object.abstractBuilding import AbstractBuilding

from citydpc.tools.partywall import get_party_walls
import pandas as pd


def getDataFrame(
    dataset: Dataset, includeFreeWalls: bool, includeBP: bool
) -> pd.DataFrame:
    """generate a pandas DataFrame from a Dataset

    Parameters
    ----------
    dataset : Dataset
        citydpc Dataset object containing buildings
    includeBP : bool
        include building parts in DataFrame

    Returns
    -------
    pd.DataFrame
        pandas DataFrame containing building information
    """

    data = []
    wantedKeys = [
        "gml_id",
        "groundArea",
        "is_3D",
        "roof_height",
        "roof_volume",
        "lod",
        "function",
        "usage",
        "yearOfConstruction",
        "roofType",
        "measuredHeight",
        "storeysAboveGround",
        "storeyHeightsAboveGround",
        "storeysBelowGround",
        "storeyHeightsBelowGround",
        "building_parts",
    ]
    if includeFreeWalls:
        wantedKeys.extend(["freeWalls", "allWalls"])
        if dataset.party_walls is None:
            dataset.party_walls = get_party_walls(dataset)
    for building in dataset.get_building_list():
        buildingData = _getInfoDictFromBuilding(building, wantedKeys)
        if includeBP:
            buildingData["isBP"] = False
            data.append(buildingData)
            for buildingPart in building.get_building_parts():
                buildingPartData = _getInfoDictFromBuilding(
                    buildingPart,
                    wantedKeys,
                )
                buildingPartData["isBP"] = True
                data.append(buildingPartData)
        else:
            data.append(buildingData)
    if includeBP:
        wantedKeys.append("isBP")
    df = pd.DataFrame(data, columns=wantedKeys)
    return df


def _getInfoDictFromBuilding(
    building: AbstractBuilding,
    wantedKeys: list,
) -> dict:
    """get information from a building object

    Parameters
    ----------
    building : AbstractBuilding
        citydpc building object
    wantedKeys : list
        keys to get from building object
    includeFreeWalls : bool
        include free walls in DataFrame

    Returns
    -------
    dict
        dict with building information
    """

    buildingData = {}
    buildingData["gml_id"] = building.gml_id
    area = 0
    for surface in building.get_surfaces(surfaceTypes=["GroundSurface"]):
        area += surface.surface_area
    buildingData["groundArea"] = area
    buildingData["is_3D"] = building.has_3Dgeometry()
    for key in wantedKeys[3:]:
        if key != "building_parts":
            buildingData[key] = getattr(building, key)
        else:
            if not building.is_building_part:
                buildingData[key] = []
                for buildingPart in building.get_building_parts():
                    buildingData[key].append(buildingPart.gml_id)
            else:
                buildingData[key] = None
    return buildingData
