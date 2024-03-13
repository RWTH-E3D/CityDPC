from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyStadt.dataset import Dataset
    from pyStadt.core.obejcts.abstractBuilding import AbstractBuilding
    from pyStadt.core.obejcts.surfacegml import SurfaceGML
    from pyStadt.core.obejcts.geometry import GeometryGML

from pyStadt.logger import logger
from pyStadt.util.envelope import update_min_max

import json


def write_cityjson_file(
    dataset: Dataset,
    filename: str,
    version: str = "2.0",
    identifier: str = None,
    pointOfContact: dict = {},
    referenceDate: str = None,
    referenceSystem: str = None,
    title: str = None,
    transfromNew: dict = {"scale": [1, 1, 1], "translate": [0, 0, 0]},
) -> None:
    """writes a dataset to a cityjson file

    Parameters
    ----------
    dataset : Dataset
        dataset to be written to a file
    filename : str
        name of the file to be written
    version : str, optional
        version of the cityjson file, by default "2.0"
    identifier : str, optional
        metadata identifier of the dataset, by default None
    pointOfContact : dict, optional
        metadata pointOfContact of the dataset, by default {}
    referenceDate : str, optional
        metadata referenceDate of the dataset, by default None
    referenceSystem : str, optional
        metadata referenceSystem of the dataset, by default None
    title : str, optional
        metadata title of the dataset, by default None
    transfromNew : dict, optional
        export transformation dict
        by default {"scale": [1, 1, 1], "translate": [0, 0, 0]}
    """

    supportedVersions = ["1.1", "2.0"]
    if version not in supportedVersions:
        logger.error(
            f"Unsopported version ({version}) for CityJSON export "
            + f"choose one of {supportedVersions}"
        )

    # create the cityjson file
    cityjson = {
        "type": "CityJSON",
        "version": version,
        "metadata": {},
        "CityObjects": {},
        "vertices": [],
    }

    cityjson["metadata"] = __create_metadata_dict(
        dataset, identifier, pointOfContact, referenceDate, referenceSystem, title
    )

    if dataset.transform != {}:
        transfromOld = dataset.transform
    else:
        transfromOld = {"scale": [1, 1, 1], "translate": [0, 0, 0]}
    vertices = []
    # add the cityobjects
    cityjson["CityObjects"], vertices = __create_cityobjects_dict(
        dataset, transfromOld, transfromNew, vertices
    )
    cityjson["metadata"]["geographicalExtent"] = [*dataset._minimum, *dataset._maximum]

    cityjson["transform"] = transfromNew

    # add the vertices
    cityjson["vertices"] = vertices

    # write the file
    with open(filename, "w") as f:
        json.dump(cityjson, f, indent=2)


def __create_metadata_dict(
    dataset: Dataset,
    identifier: str = None,
    pointOfContact: dict = None,
    referenceDate: str = None,
    referenceSystem: str = None,
    title: str = None,
) -> dict:
    """creates the metadata dict for the cityjson file

    Parameters
    ----------
    dataset : Dataset
        dataset to be written to a file
    identifier : str, optional
        metadata identifier of the dataset, by default None
    pointOfContact : dict, optional
        metadata pointOfContact of the dataset, by default None
    referenceDate : str, optional
        metadata referenceDate of the dataset, by default None
    referenceSystem : str, optional
        metadata referenceSystem of the dataset, by default None
    title : str, optional
        metadata title of the dataset, by default None

    Returns
    -------
    dict
        metadata dict
    """

    metadata = {}

    # add the metadata
    metadata["geographicalExtent"] = None
    if identifier is not None:
        metadata["identifier"] = identifier
    if pointOfContact != {}:
        metadata["pointOfContact"] = pointOfContact
    if referenceDate is not None:
        metadata["referenceDate"] = referenceDate
    if referenceSystem is not None:
        metadata["referenceSystem"] = referenceSystem
    elif dataset.srsName is not None and dataset.srsName.startswith(
        "http://www.opengis.net/def/crs/"
    ):
        metadata["referenceSystem"] = dataset.srsName
    else:
        logger.warning(
            "Dataset is using invalid format for srsName (/referenceSystem). Leaving "
            + "referecnceSystem in metadata empty"
        )
    if title is not None:
        metadata["title"] = title

    return metadata


def __create_cityobjects_dict(
    dataset: Dataset,
    transformOld: dict,
    transfromNew: dict,
    vertices: list[list[float]],
) -> tuple[dict, list[list[float]]]:
    """creates the cityobject dict for the cityjson file

    Parameters
    ----------
    dataset : Dataset
        dataset to be written to a file
    transformOld : dict
        old transformation dict
    transfromNew : dict
        export transformation dict
    vertices : list[list[float]]
        list of vertices

    Returns
    -------
    dict
        cityobject dict
    """

    cityobjects = {}

    # add the cityobjects
    for building in dataset.get_building_list():
        cityobjects[building.gml_id], vertices = __create_cityobject_dict(
            dataset, building, transformOld, transfromNew, vertices
        )

        if building.has_building_parts():
            for building_part in building.get_building_parts():
                cityobjects[building_part.gml_id], vertices = __create_cityobject_dict(
                    dataset, building_part, transformOld, transfromNew
                )

    return cityobjects, vertices


def __create_cityobject_dict(
    dataset: Dataset,
    building: AbstractBuilding,
    transformOld: dict,
    transformNew: dict,
    vertices: list[list[float]],
) -> tuple[dict, list[list[float]]]:
    """creates the cityobject dict for the cityjson file

    Parameters
    ----------
    dataset : Dataset
        dataset to be written to a file
    building : AbstractBuilding
        either a building or a building part object to be written to the file
    transformOld : dict
        old transformation dict
    transfromNew : dict
        export transformation dict
    vertices : list[list[float]]
        list of vertices

    Returns
    -------
    dict
        cityobject dict
    """

    cityobject = {}

    # add the cityobject
    if not building.is_building_part:
        cityobject["type"] = "Building"
    else:
        cityobject["type"] = "BuildingPart"

    # add the attributes
    attributes = {}
    for i in [
        "function",
        "usage",
        "yearOfConstruction",
        "roofType",
        "measuredHeight",
        "storeysAboveGround",
        "storeyHeightsAboveGround",
        "storeysBelowGround",
        "storeyHeightsBelowGround",
    ]:
        value = getattr(building, i)
        if value is not None:
            attributes[i] = value
    if attributes != {}:
        cityobject["attributes"] = attributes

    if not building.is_building_part and building.has_building_parts():
        cityobject["attributes"]["buildingParts"] = []
        for i in building.get_building_parts():
            cityobject["attributes"]["buildingParts"].append(i.gml_id)
    elif building.is_building_part:
        cityobject["attributes"]["parent"] = [building.parent_gml_id]

    if len(building.geometries) > 0:
        cityobject["geometry"] = []

        for geometry in building.geometries.values():
            cityobject["geometry"].append(
                __create_geometry_dict(
                    dataset, geometry, transformOld, transformNew, vertices
                )
            )

    if not building.address.address_is_empty():
        cityobject["address"] = [{}]
        for i in [
            "countryName",
            "locality_type",
            "localityName",
            "thoroughfare_type",
            "thoroughfareNumber",
            "thoroughfareName",
            "postalCodeNumber",
        ]:
            value = getattr(building.address, i)
            if value is not None:
                cityobject["address"][0][i] = value

    return cityobject, vertices


def __create_geometry_dict(
    dataset: Dataset,
    geometry: GeometryGML,
    transformOld: dict,
    transformNew: dict,
    vertices: list[list[float]],
) -> dict:
    """creates the geometry dict for the cityjson file

    Parameters
    ----------
    dataset : Dataset
        dataset to be written to a file
    geometry : GeometryGML
        geometry to be written to the file
    transformOld : dict
        old transformation dict
    transfromNew : dict
        export transformation dict
    vertices : list[list[float]]
        list of vertices

    Returns
    -------
    dict
        geometry dict
    """

    geometry_dict = {}

    # add the geometry
    geometry_dict["type"] = geometry.type

    # add the lod
    geometry_dict["lod"] = str(geometry.lod)

    # add the vertices
    boundaries = []

    surfaces = []
    values = []

    if geometry.type == "CompositeSolid" or geometry.type == "MultiSolid":
        for _, surfaceIDs in geometry.solids.items():
            solidList = []
            solidValList = []
            shellList = []
            shellValList = []
            for surfaceID in surfaceIDs:
                surface = geometry.get_surface(surfaceID)
                update_min_max(dataset, surface)
                surfaceVerts = __surface_to_vertices(
                    surface, transformOld, transformNew, vertices
                )
                shellList.append([surfaceVerts])
                semanticsIndex = __update_surfaces_dict(surface, surfaces)
                shellValList.append(semanticsIndex)
            solidList.append(shellList)
            solidValList.append(shellValList)
            values.append(solidValList)
            boundaries.append(solidList)
    elif geometry.type == "Solid":
        solidList = []
        solidValList = []
        for surface in geometry.surfaces:
            update_min_max(dataset, surface)
            surfaceVerts = __surface_to_vertices(
                surface, transformOld, transformNew, vertices
            )
            solidList.append([surfaceVerts])
            semanticsIndex = __update_surfaces_dict(surface, surfaces)
            solidValList.append(semanticsIndex)
        values.append(solidValList)
        boundaries.append(solidList)
    elif geometry.type == "MultiSurface" or geometry.type == "CompositeSurface":
        for surface in geometry.surfaces:
            update_min_max(dataset, surface)
            surfaceVerts = __surface_to_vertices(
                surface, transformOld, transformNew, vertices
            )
            boundaries.append([surfaceVerts])
            semanticsIndex = __update_surfaces_dict(surface, surfaces)
            values.append(semanticsIndex)

    geometry_dict["boundaries"] = boundaries
    semantics = {"surfaces": surfaces, "values": values}

    if geometry.lod > 1:
        geometry_dict["semantics"] = semantics

    return geometry_dict


def __surface_to_vertices(
    surface: SurfaceGML,
    transformOld: dict,
    transformNew: dict,
    vertices: list[list[float]],
) -> list[list[int]]:
    """updates the vertices list and returns the surface vertices index list

    Parameters
    ----------
    surface : SurfaceGML
        SurfaceGML object to be written to the file
    transformOld : dict
        old transformation dict
    transformNew : dict
        export transformation dict
    vertices : list[list[float]]
        list of vertices

    Returns
    -------
    list[list[int]]
        list of surface vertices indices
    """

    surfaceVerts = []
    for vertex in surface.gml_surface_2array[:-1]:
        vertex = vertex * transformOld["scale"] + transformOld["translate"]
        vertex = vertex - transformNew["translate"]
        vertex = vertex / transformNew["scale"]
        if vertex.tolist() not in vertices:
            vertices.append(vertex.tolist())
        surfaceVerts.append(vertices.index(vertex.tolist()))

    return surfaceVerts


def __update_surfaces_dict(surface: SurfaceGML, surfaces: list[dict]) -> int:
    """updates the surfaces dict and returns the surface index for semantics

    Parameters
    ----------
    surface : SurfaceGML
        SurfaceGML object to be written to the file
    surfaces : list[dict]
        list of surface semantics dicts

    Returns
    -------
    int
        surface index for semantics
    """
    surface_dict = {}

    surface_dict["type"] = surface.surface_type
    if not surface.surface_id.startswith("pyStadt_"):
        surface_dict["id"] = surface.surface_id

    for i, presentDict in enumerate(surfaces):
        if presentDict == surface_dict:
            return i

    surfaces.append(surface_dict)
    return len(surfaces) - 1
