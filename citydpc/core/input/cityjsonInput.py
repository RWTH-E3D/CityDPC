from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from citydpc.dataset import Dataset
    from citydpc.core.obejct.abstractBuilding import AbstractBuilding

import json
import numpy as np
import matplotlib.path as mplP

from citydpc.core.obejct.building import Building
from citydpc.core.obejct.buildingPart import BuildingPart
from citydpc.core.obejct.surfacegml import SurfaceGML
from citydpc.core.obejct.fileUtil import CityFile
from citydpc.core.obejct.geometry import GeometryGML
from citydpc.tools.cityATB import (
    _border_check,
    check_building_for_border_and_address,
)
from citydpc.logger import logger
from citydpc.tools.partywall import get_party_walls


def _validate_cityjson_data(
    data: dict, source_identifier: str = "data"
) -> bool:
    """Validates if the provided dictionary has required CityJSON structure.

    Parameters
    ----------
    data : dict
        Dictionary containing CityJSON data
    source_identifier : str
        Identifier for error messages (filepath or "data")

    Returns
    -------
    bool
        True if valid, False otherwise
    """
    required_members = [
        "type",
        "version",
        "transform",
        "CityObjects",
        "vertices",
    ]
    supported_versions = ["1.0", "1.1", "2.0"]

    # Check required keys
    for required_key in required_members:
        if required_key not in data:
            logger.warning(
                f"invalid CityJSON {source_identifier} - missing "
                + str(required_key)
            )
            return False

    # Validate type and version
    if data["type"] != "CityJSON":
        logger.warning(
            f"invalid CityJSON {source_identifier} - not CityJSON file"
        )
        return False

    if data["version"] not in supported_versions:
        logger.warning(
            f"unsupported CityJSON version ({data['version']}) in "
            + str(source_identifier)
        )
        return False

    return True


def _process_metadata(
    data: dict,
    dataset: Dataset,
    city_file: CityFile,
    border_coordinates: list = None,
    ignore_ref_system: bool = False,
) -> tuple:
    """Process CityJSON metadata and update dataset and city_file accordingly.

    Returns
    -------
    tuple
        (border, None) if border checking passes, (None, True) if should return
        early
    """
    border = None

    if "metadata" not in data:
        return border, False

    metadata = data["metadata"]

    # Handle geographical extent and border
    if "geographicalExtent" in metadata:
        city_file.lowerCorner = metadata["geographicalExtent"][0:3]
        city_file.upperCorner = metadata["geographicalExtent"][3:6]

        if border_coordinates is not None:
            file_envelope_coor = [
                city_file.lowerCorner[0:2],
                city_file.upperCorner[0:2],
            ]
            border = mplP.Path(np.array(border_coordinates))
            if not _border_check(
                border, border_coordinates, file_envelope_coor
            ):
                return None, True

    # Handle other metadata
    if "title" in metadata:
        city_file.gmlName = metadata["title"]
        if dataset.title is None:
            dataset.title = metadata["title"]

    if "identifier" in metadata:
        city_file.identifier = metadata["identifier"]

    if "referenceSystem" in metadata:
        if not _handle_reference_system(
            dataset, metadata["referenceSystem"], ignore_ref_system
        ):
            return None, True
        city_file.srsName = metadata["referenceSystem"]

    return border, False


def _handle_reference_system(
    dataset: Dataset, newSrs: str, ignore_ref_system: bool
) -> bool:
    """Handle reference system compatibility checking."""
    if dataset.srsName is None:
        dataset.srsName = newSrs
        return True
    elif dataset.srsName == newSrs:
        return True
    elif ignore_ref_system:
        return True
    else:
        logger.error(
            f"Unable to load data! Given referenceSystem ({newSrs}) "
            f"does not match dataset srsName ({dataset.srs_name})"
        )
        return False


def _process_building(
    building_id: str,
    building_data: dict,
    vertices: list,
    city_objects: dict,
    city_gml_version: str,
) -> Building:
    """Process a single building and its parts from CityJSON data."""
    new_building = Building(building_id)
    _load_building_information_from_json(new_building, building_data, vertices)

    bp_key = (
        "members" if city_gml_version.split("v")[1] == "1.0" else "children"
    )

    if bp_key in building_data:
        for child in building_data[bp_key]:
            if child in city_objects:
                if city_objects[child]["type"] == "BuildingPart":
                    new_building_part = BuildingPart(
                        child, new_building.gml_id
                    )
                    _load_building_information_from_json(
                        new_building_part, city_objects[child], vertices
                    )
                    new_building.building_parts.append(new_building_part)
                else:
                    logger.warning(
                        f"Child ({child}) of building ({building_id}) "
                        "is not a BuildingPart"
                    )
            else:
                logger.warning(
                    f"Child ({child}) of building ({building_id}) "
                    "does not exist"
                )

    return new_building


def load_buildings_from_dict(
    dataset: Dataset,
    cityjson_data: dict,
    features: list[dict] = None,
    border_coordinates: list = None,
    address_restriction: dict = None,
    ignore_ref_system: bool = False,
    dont_transform: bool = False,
    ignore_existing_transform: bool = False,
    update_party_walls: bool = False,
    allowed_ids: list[str] = None,
) -> None:
    """Adds buildings from CityJSON dictionary data to dataset.

    Parameters
    ----------
    dataset : Dataset
        Dataset to add buildings to
    cityjson_data : dict
        Dictionary containing main CityJSON data
    features : list[dict], optional
        List of feature dictionaries for CityJSONSeq-style data
    Other parameters are the same as in load_buildings_from_json_file
    """
    logger.info("loading buildings from CityJSON dictionary")

    if not _validate_cityjson_data(cityjson_data):
        return

    new_city_file = CityFile(
        "dict_input", f"CityJSONv{cityjson_data['version']}", [], [], []
    )

    border, should_return = _process_metadata(
        cityjson_data,
        dataset,
        new_city_file,
        border_coordinates,
        ignore_ref_system,
    )
    if should_return:
        return

    if not dont_transform:
        vertices = _transform_vertices(
            dataset,
            cityjson_data,
            cityjson_data["vertices"],
            ignore_existing_transform,
        )
    else:
        if (
            dataset.transform
            and dataset.transform != cityjson_data["transform"]
        ):
            if not ignore_existing_transform:
                raise ValueError(
                    "Trying to add data with different transform object than "
                    + "dataset. Either transform or set "
                    + "ignore_existing_transform=True"
                )
        else:
            dataset.transform = cityjson_data["transform"]
        vertices = cityjson_data["vertices"]

    building_ids = []

    for building_id, value in cityjson_data["CityObjects"].items():
        if allowed_ids is not None and building_id not in allowed_ids:
            continue

        if value["type"] == "Building":
            new_building = _process_building(
                building_id,
                value,
                vertices,
                cityjson_data["CityObjects"],
                new_city_file.cityGMLversion,
            )

            if building_id in dataset.buildings:
                logger.warning(f"duplicate gml_id ({building_id})")
                continue

            if not check_building_for_border_and_address(
                new_building, border_coordinates, address_restriction, border
            ):
                continue

            dataset.buildings[building_id] = new_building
            building_ids.append(building_id)

    if features:
        for feature in features:
            building_id = feature["id"]
            if allowed_ids is not None and building_id not in allowed_ids:
                continue

            if feature["CityObjects"][building_id]["type"] == "Building":
                feature_vertices = (
                    _transform_vertices(
                        dataset,
                        cityjson_data,
                        feature["vertices"],
                        ignore_existing_transform,
                    )
                    if not dont_transform
                    else feature["vertices"]
                )

                new_building = _process_building(
                    building_id,
                    feature["CityObjects"][building_id],
                    feature_vertices,
                    feature["CityObjects"],
                    new_city_file.cityGMLversion,
                )

                if building_id in dataset.buildings:
                    logger.warning(f"duplicate gml_id ({building_id})")
                    continue

                if not check_building_for_border_and_address(
                    new_building,
                    border_coordinates,
                    address_restriction,
                    border,
                ):
                    continue

                dataset.buildings[building_id] = new_building
                building_ids.append(building_id)

    # Update city file information
    new_city_file.building_ids = building_ids
    new_city_file.num_notLoaded_CityObjectMembers = len(
        cityjson_data["CityObjects"]
    ) - len(building_ids)
    dataset._files.append(new_city_file)

    if update_party_walls:
        dataset.party_walls = get_party_walls(dataset)

    logger.info("finished loading buildings from CityJSON dictionary")


def load_buildings_from_json_file(
    dataset: Dataset,
    filepath: str,
    border_coordinates: list = None,
    address_restriction: dict = None,
    ignore_ref_system: bool = False,
    dont_transform: bool = False,
    ignore_existing_transform: bool = False,
    update_party_walls: bool = False,
    cityJSONSeq: bool = False,
    allowed_ids: list[str] = None,
) -> None:
    """Loads buildings from a CityJSON file into the dataset.

    Parameters remain the same as in the original function.
    """
    logger.info(f"loading buildings from CityJSON file {filepath}")

    if cityJSONSeq:
        with open(filepath, "r") as f:
            list_of_dicts = [json.loads(line) for line in f]

        cityjson_data = list_of_dicts[0]
        features = list_of_dicts[1:]

        load_buildings_from_dict(
            dataset=dataset,
            cityjson_data=cityjson_data,
            features=features,
            border_coordinates=border_coordinates,
            address_restriction=address_restriction,
            ignore_ref_system=ignore_ref_system,
            dont_transform=dont_transform,
            ignore_existing_transform=ignore_existing_transform,
            update_party_walls=update_party_walls,
            allowed_ids=allowed_ids,
        )
    else:
        with open(filepath, "r") as f:
            cityjson_data = json.load(f)

        if "CityJSONFeatures" in cityjson_data:
            features = cityjson_data.pop("CityJSONFeatures")
        else:
            features = None

        load_buildings_from_dict(
            dataset=dataset,
            cityjson_data=cityjson_data,
            features=features,
            border_coordinates=border_coordinates,
            address_restriction=address_restriction,
            ignore_ref_system=ignore_ref_system,
            dont_transform=dont_transform,
            ignore_existing_transform=ignore_existing_transform,
            update_party_walls=update_party_walls,
            allowed_ids=allowed_ids,
        )


def _transform_vertices(
    dataset: Dataset,
    data: dict,
    vertices: list[list[float]],
    ignoreExistingTransform: bool,
) -> list[list[float]]:
    if (
        dataset.transform == {}
        or dataset.transform == {"scale": [1, 1, 1], "translate": [0, 0, 0]}
        or ignoreExistingTransform
    ):
        for vertex in vertices:
            vertex[0] = round(
                vertex[0] * data["transform"]["scale"][0]
                + data["transform"]["translate"][0],
                3,
            )
            vertex[1] = round(
                vertex[1] * data["transform"]["scale"][1]
                + data["transform"]["translate"][1],
                3,
            )
            vertex[2] = round(
                vertex[2] * data["transform"]["scale"][2]
                + data["transform"]["translate"][2],
                3,
            )
        if dataset.transform == {}:
            dataset.transform = data["transform"]
    else:
        raise ValueError(
            "Trying to add file with differenet transform object than "
            + "dataset. Either transform or forceIgnore the transformation"
        )
    return vertices


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
            "storeysAboveGround",
            "storeyHeightsAboveGround",
            "storeysBelowGround",
            "storeyHeightsBelowGround",
        ]
        for key, value in attributes.items():
            if key in objAttributes:
                setattr(building, key, value)
            else:
                building.genericStrings[key] = value

    if "address" in jsonDict.keys():
        # buildings can have multiple addresses, we are only considering the
        # first
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
            geometryObj = GeometryGML(
                geometry["type"],
                building.gml_id,
                int(geometry["lod"].split(".")[0]),
            )
            geomKey = building.add_geometry(geometryObj)
            if building.lod is None:
                building.lod = building.geometries[geomKey].lod

            if "semantics" not in geometry.keys():
                logger.warning(
                    f"no semantics in {building.gml_id} - skipping geometry"
                )
                continue

            if geometry["type"] == "Solid":
                for i, shell in enumerate(geometry["boundaries"]):
                    for j, surface in enumerate(shell):
                        _add_cityjson_surface_to_building(
                            building,
                            geometryObj,
                            vertices,
                            surface,
                            geometry["semantics"],
                            [i, j],
                        )
            elif (
                geometry["type"] == "MultiSurface"
                or geometry["type"] == "CompositeSurface"
            ):
                for i, surface in enumerate(geometry["boundaries"]):
                    _add_cityjson_surface_to_building(
                        building,
                        geometryObj,
                        vertices,
                        surface,
                        geometry["semantics"],
                        [i],
                    )
            elif (
                geometry["type"] == "MultiSolid"
                or geometry["type"] == "CompositeSolid"
            ):
                for i, solid in enumerate(geometry["boundaries"]):
                    for j, shell in enumerate(solid):
                        for k, surface in enumerate(shell):
                            _add_cityjson_surface_to_building(
                                building,
                                geometryObj,
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
        building._calc_roof_volume()
        building.create_legacy_surface_dicts()


def _add_cityjson_surface_to_building(
    building: AbstractBuilding,
    geometry: GeometryGML,
    vertices: list[list[float]],
    vertexIndexList: list[list[int]],
    semantics: dict,
    depthInfo: list[float],
) -> None:
    """creates a new surface from coordinates and semantics

    Parameters
    ----------
    building : AbstractBuilding
        either Building or BuildingPart object to add surface to
    geometry : GeometryGML
        geometry object to add surface to
    vertices : list[list[float]]
        list of vertices
    vertexIndexList : list[list[float]]
        list of indices of vertices
    semantics : dict
        semantic dict from geometry
    depthInfo : list[float]
        list of surface indices
    """
    surfaceCoor = []
    for vertex in vertexIndexList[0]:
        surfaceCoor.append(vertices[vertex])
    surfaceType, surfaceId = _get_semantic_surface_info(semantics, depthInfo)
    if surfaceType is None or surfaceType not in [
        "GroundSurface",
        "RoofSurface",
        "WallSurface",
        "ClosureSurface",
    ]:
        logger.warning(
            f"unsupported surface type ({surfaceType}) in {building.gml_id}"
        )
        return

    if surfaceId is None:
        surfaceId = (
            f"citydpc_{building.gml_id}_{surfaceType}_"
            + f"{'_'.join([str(i) for i in depthInfo])}"
        )

    if surfaceCoor[0] != surfaceCoor[-1]:
        surfaceCoor.append(surfaceCoor[0])

    newSurface = SurfaceGML(
        np.array(surfaceCoor).flatten(), surfaceId, surfaceType
    )
    if newSurface.isSurface:
        if len(depthInfo) == 3:
            geometry.add_surface(newSurface, str(depthInfo))
        else:
            geometry.add_surface(newSurface)
    else:
        building._warn_invalid_surface(surfaceId)
        return


def _get_semantic_surface_info(
    semantics: dict, depthInfo: list[float]
) -> list[str | None, str | None]:
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
