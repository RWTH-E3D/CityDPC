from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from citydpc import Dataset
    from citydpc.core.obejct.abstractBuilding import AbstractBuilding

from citydpc.logger import logger
from citydpc.core.obejct.building import Building

import pandas as pd


def getDataFrame(dataset: Dataset, includeBP: bool) -> pd.DataFrame:
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
    wantedKeys = ["gml_id", "groundArea", "is_3D", "roof_height", "roof_volume", "lod",
                  "function", "usage", "yearOfConstruction", "roofType",
                  "measuredHeight", "storeysAboveGround", "storeyHeightsAboveGround",
                  "storeysBelowGround", "storeyHeightsBelowGround",
                  "building_parts",
                  ]
    for building in dataset.get_building_list():
        buildingData = _getInfoDictFromBuilding(building, wantedKeys)
        if includeBP:
            buildingData["isBP"] = False
            data.append(buildingData.values())
            for buildingPart in building.get_building_parts():
                buildingPartData = _getInfoDictFromBuilding(buildingPart, wantedKeys)
                buildingPartData["isBP"] = True
                data.append(buildingPartData.values())
        else:
            data.append(buildingData)

    if includeBP:
        wantedKeys.append("isBP")
    return pd.DataFrame(data, columns=wantedKeys)


def _getInfoDictFromBuilding(building: AbstractBuilding, wantedKeys: list) -> dict:
    """get information from a building object

    Parameters
    ----------
    building : AbstractBuilding
        citydpc building object
    wantedKeys : list
        keys to get from building object

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
        buildingData[key] = getattr(building, key)
    bps = []
    if not building.is_building_part:
        for buildingPart in building.get_building_parts():
            bps.append(buildingPart.gml_id)
    buildingData["building_parts"] = bps
    return buildingData
