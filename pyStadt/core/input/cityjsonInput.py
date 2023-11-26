from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyStadt.dataset import Dataset
    from pyStadt.core.obejcts.abstractBuilding import AbstractBuilding

import json
import numpy as np
import matplotlib.path as mplP

from pyStadt.core.obejcts.building import Building
from pyStadt.core.obejcts.buildingPart import BuildingPart
from pyStadt.core.obejcts.surfacegml import SurfaceGML
from pyStadt.core.obejcts.fileUtil import CityFile
from pyStadt.tools.cityATB import (
    _border_check,
    check_building_for_border_and_address
)
from pyStadt.logger import logger


def load_buildings_from_json_file(
    dataset: Dataset,
    filepath: str,
    borderCoordinates: list = None,
    addressRestriciton: dict = None,
):
    """adds buldings from filepath to dataset

    Parameters
    ----------
    dataset : Dataset
        Dataset to add buildings to
    filepath : str
        filepath to cityJSON file
    borderCoordinates : list, optional
        list of coordinates ([x0, y0], [x1, y1], ..) in fileCRS to restrict the dataset,
        by default None
    addressRestriciton : dict, optional
        dictionary of address values to restrict the dataset, by default None
    """
    logger.info(f"loading buildings from CityJSON file {filepath}")
    supportedVersions = ["1.0", "1.1", "2.0"]
    requiredMembers = ["type", "version", "transform", "CityObjects", "vertices"]

    with open(filepath, "r") as f:
        data = json.load(f)

    for requiredKey in requiredMembers:
        if requiredKey not in data.keys():
            logger.warning(
                f"invalid CityJSON file ({filepath}) - missing {requiredKey}"
            )
            return

    if data["type"] != "CityJSON":
        logger.warning(f"invalid CityJSON file ({filepath}) - not CityJSON file")
        return

    if data["version"] not in supportedVersions:
        logger.warning(
            f"unsupported CityJSON verion ({data['version']}) " + f"in {filepath}"
        )
        return

    border = None
    newCityFile = CityFile(filepath, f"CityJSONv{data['version']}", [], [])
    if "metadata" in data.keys():
        if "geographicalExtent" in data["metadata"].keys():
            newCityFile.lowerCorner = data["metadata"]["geographicalExtent"][0:3]
            newCityFile.upperCorner = data["metadata"]["geographicalExtent"][3:6]
            if borderCoordinates is not None:
                fileEnvelopeCoor = [
                    newCityFile.lowerCorner[0:2],
                    newCityFile.upperCorner[0:2],
                ]
                border = mplP.Path(np.array(borderCoordinates))
                if not _border_check(border, borderCoordinates, fileEnvelopeCoor):
                    # file envelope is outside of the border coordinates
                    return

        if "title" in data["metadata"].keys():
            newCityFile.gmlName = data["metadata"]["title"]
        if "referenceSystem" in data["metadata"].keys():
            if dataset.srsName is None:
                dataset.srsName = data["metadata"]["referenceSystem"].split("/crs/")[-1]
            elif (
                dataset.srsName
                == data["metadata"]["referenceSystem"].split("/crs/")[-1]
            ):
                pass
            else:
                logger.error(
                    "Unable to load file! Given referenceSystem "
                    + f"({data['metadata']['referenceSystem']}) does not match Dataset "
                    + f"srsName ({dataset.srsName})"
                )

    # transform all vertices to global coordinates
    vertices = data["vertices"]
    for vertex in vertices:
        vertex[0] = (
            vertex[0] * data["transform"]["scale"][0]
            + data["transform"]["translate"][0]
        )
        vertex[1] = (
            vertex[1] * data["transform"]["scale"][1]
            + data["transform"]["translate"][1]
        )
        vertex[2] = (
            vertex[2] * data["transform"]["scale"][2]
            + data["transform"]["translate"][2]
        )

    buildingIDs = []
    buildingPartsToAssign = []

    for id, value in data["CityObjects"].items():
        if value["type"] == "Building":
            newBuilding = Building(id)
            _load_building_information_from_json(newBuilding, value, vertices)
            if id in dataset.buildings.keys():
                logger.warning(
                    f"invalid CityJSON file ({filepath}) - duplicate gml_id ({id})"
                )
                continue
            dataset.buildings[id] = newBuilding
            buildingIDs.append(id)

        elif value["type"] == "BuildingPart":
            newBuildingPart = BuildingPart(id)
            _load_building_information_from_json(newBuildingPart, value, vertices)

            if "parents" in value.keys():
                newBuildingPart.parent_gml_id = value["parents"][0]
            elif "members" in value.keys():
                newBuildingPart.parent_gml_id = value["members"][0]
            else:
                logger.warning(
                    f"invalid CityJSON file ({filepath}) - BuildingPart without "
                    + "parent id"
                )
                continue

            if newBuildingPart.parent_gml_id in dataset.buildings.keys():
                dataset.buildings[newBuildingPart.parent_gml_id].building_parts.append(
                    newBuildingPart
                )
            else:
                buildingPartsToAssign.append(newBuildingPart)

    for buildingPart in buildingPartsToAssign:
        if buildingPart.parent_gml_id in dataset.buildings.keys():
            dataset.buildings[buildingPart.parent_gml_id].building_parts.append(
                buildingPart
            )
        else:
            logger.warning(
                f"invalid CityJSON file ({filepath}) - BuildingPart without parent"
            )

    if border is not None or addressRestriciton is not None:
        for buildingID in buildingIDs:
            building = dataset.buildings[buildingID]
            if not check_building_for_border_and_address(
                building, borderCoordinates, addressRestriciton, border
            ):
                continue

    newCityFile.building_ids = buildingIDs
    dataset._files.append(newCityFile)
    logger.info(f"finished loading buildings from CityJSON file {filepath}")


def _load_building_information_from_json(
    building: AbstractBuilding, jsonDict: dict, vertices: list[list[float]]
) -> None:
    """loads building information from jsonDict and adds it to building object

    Parameters
    ----------
    building : AbstractBuilding
        either Building or BuildingPart object to add information to
    jsonDict : dict
        jsonDict representing the building
    vertices : list[list[float]]
        list of transformed and translated vertices
    """
    if "attributes" in jsonDict.keys():
        attributes = jsonDict["attributes"]
        objAttributes = [
            "function",
            "roofType",
            "usage",
            "yearOfConstruction",
            "storeysAboceGround",
            "storeysBelowGround",
        ]
        for key, value in attributes.items():
            if key in objAttributes:
                setattr(building, key, value)
            else:
                building.genericStrings[key] = value

    if "address" in jsonDict.keys():
        # buildings can have multiple addresses, we are only considering the first
        address = jsonDict["address"][0]
        objAttributes = {
            "country": "countryName",
            "locality": "localityName",
            "thoroughfareNumber": "thoroughfareNumber",
            "thoroughfareName": "thoroughfareName",
            "postcode": "postalCodeNumber",
        }
        for key, value in address.items():
            if key in objAttributes:
                setattr(building.address, objAttributes[key], value)

    if "geometry" in jsonDict.keys() and jsonDict["geometry"] != []:
        for geometry in jsonDict["geometry"]:
            if "semantics" not in geometry.keys():
                logger.warning(f"no semantics in {building.gml_id} - skipping geometry")
                continue

            building.lod = geometry["lod"].split(".")[0]

            if geometry["type"] == "Solid":
                for i, shell in enumerate(geometry["boundaries"]):
                    for j, surface in enumerate(shell):
                        _add_surface_to_building(
                            building, vertices, surface, geometry["semantics"], [i, j]
                        )
            elif (
                geometry["type"] == "MultiSurface"
                or geometry["type"] == "CompositeSurface"
            ):
                for i, surface in enumerate(geometry["boundaries"]):
                    _add_surface_to_building(
                        building, vertices, surface, geometry["semantics"], [i]
                    )
            elif (
                geometry["type"] == "MultiSolid" or geometry["type"] == "CompositeSolid"
            ):
                for i, solid in enumerate(geometry["boundaries"]):
                    for j, shell in enumerate(solid):
                        for k, surface in enumerate(shell):
                            _add_surface_to_building(
                                building,
                                vertices,
                                surface,
                                geometry["semantics"],
                                [i, j, k],
                            )
            else:
                logger.warning(
                    f"unsupported geometry type ({geometry['type']}) in "
                    + f"{building.gml_id}"
                )


def _add_surface_to_building(
    building: AbstractBuilding,
    vertices: list[list[float]],
    vertexList: list[list[float]],
    semantics: dict,
    depthInfo: list[float],
) -> None:
    """creates a new surface from coordinates and semantics

    Parameters
    ----------
    building : AbstractBuilding
        either Building or BuildingPart object to add surface to
    vertices : list[list[float]]
        list of vertices
    coordiantes : list[list[float]]
        list of coordinates
    semantics : dict
        semantic dict from geometry
    depthInfo : list[float]
        list of surface indices
    """
    surfaceCoor = []
    for vertex in vertexList[0]:
        surfaceCoor.append(vertices[vertex])
    surfaceType, surfaceId = _get_semantic_surface_info(semantics, depthInfo)
    if surfaceType is None or surfaceType not in [
        "GroundSurface",
        "RoofSurface",
        "WallSurface",
        "ClosureSurface",
    ]:
        logger.warning(f"unsupported surface type ({surfaceType}) in {building.gml_id}")
        return

    if surfaceId is None:
        surfaceId = (
            f"{building.gml_id}_{surfaceType}_{'_'.join([str(i) for i in depthInfo])}"
        )

    building.add_surface(
        SurfaceGML(np.array(surfaceCoor).flatten(), surfaceId, surfaceType)
    )


def _get_semantic_surface_info(
    semantics: dict, depthInfo: list[float]
) -> [str | None, str | None]:
    """gets semantic surface information from semantics

    Parameters
    ----------
    semantics : dict
        semantic dict from geometry
    depthInfo : list[float]
        list of surface indices

    Returns
    -------
    [str | None, str | None]
        surface type (if available) and (if available) surface id
    """
    value = semantics["values"]
    for index in depthInfo:
        value = value[index]

    if value is None:
        return None, None

    surfaceType = semantics["surfaces"][value]["type"]
    if "id" in semantics["surfaces"][value].keys():
        return surfaceType, semantics["surfaces"][value]["id"]
    else:
        return surfaceType, None
