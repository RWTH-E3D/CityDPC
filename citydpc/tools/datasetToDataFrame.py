from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from citydpc import Dataset
    from citydpc.core.obejct.abstractBuilding import AbstractBuilding

from citydpc.tools.partywall import get_party_walls
import pandas as pd


def getDataFrame(dataset: Dataset, includeFreeWalls: bool, includeBP: bool) -> pd.DataFrame:
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
    if includeFreeWalls:
        partyWalls = get_party_walls(dataset)
    for building in dataset.get_building_list():
        buildingData = _getInfoDictFromBuilding(building, wantedKeys, includeFreeWalls)
        if includeBP:
            buildingData["isBP"] = False
            data.append(buildingData.values())
            for buildingPart in building.get_building_parts():
                buildingPartData = _getInfoDictFromBuilding(
                    buildingPart, wantedKeys, includeFreeWalls
                )
                buildingPartData["isBP"] = True
                data.append(buildingPartData.values())
        else:
            data.append(buildingData)
    if includeFreeWalls:
        wantedKeys.append("freeWalls")
        wantedKeys.append("allWalls")
    if includeBP:
        wantedKeys.append("isBP")
    df = pd.DataFrame(data, columns=wantedKeys)
    if includeFreeWalls:
        # add party wall information
        buildingWallCombs = []
        for b0, w0, b1, w1, *_ in partyWalls:
            if b0 + w0 not in buildingWallCombs:
                buildingWallCombs.append(b0 + w0)
                df.loc[df["gml_id"] == b0, "freeWalls"] -= 1
            if b1 + w1 not in buildingWallCombs:
                buildingWallCombs.append(b1 + w1)
                df.loc[df["gml_id"] == b1, "freeWalls"] -= 1
    return df


def _getInfoDictFromBuilding(building: AbstractBuilding, wantedKeys: list,
                             includeFreeWalls: bool) -> dict:
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
        buildingData[key] = getattr(building, key)
    bps = []
    if not building.is_building_part:
        for buildingPart in building.get_building_parts():
            bps.append(buildingPart.gml_id)
    buildingData["building_parts"] = bps
    if includeFreeWalls:
        numOfWalls = len(building.get_surfaces(surfaceTypes=["WallSurface"]))
        buildingData["freeWalls"] = numOfWalls
        buildingData["allWalls"] = numOfWalls
    return buildingData
