from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from citydpc.dataset import Dataset
    from citydpc.core.obejct.abstractBuilding import AbstractBuilding
    from citydpc.core.obejct.building import Building

import numpy as np
import matplotlib.path as mplP
import copy


def analysis(dataset: Dataset) -> dict[dict]:
    """general file analysis based on CityATB

    Parameters
    ----------
    data : Dataset
        CityPY dataset object

    Returns
    -------
    dict
        contains dict of dicts where key is filename and value is dict with keys:
        - gml_version
        - gml_name
        - crs
        - gml_lod
        - ade
        - number_of_cityobject_members
        - number_of_buildings
        - number_of_buildingParts

    """
    fullResult = {}
    for singleFile in dataset._files:
        fileResult = {}

        fileResult["gml_version"] = singleFile.cityGMLversion
        if singleFile.gmlName is not None:
            fileResult["gml_name"] = singleFile.gmlName
        else:
            fileResult["gml_name"] = singleFile.identifier
        fileResult["crs"] = singleFile.srsName

        all_LoDs = []
        buildingPart_counter = 0
        for building_id in singleFile.building_ids:
            building = dataset.buildings[building_id]
            for geometry in building.get_geometries():
                if str(geometry.lod) not in all_LoDs:
                    all_LoDs.append(str(geometry.lod))
            if building.has_building_parts():
                for buildingPart in building.building_parts:
                    buildingPart_counter -= -1
                    for geometry in buildingPart.get_geometries():
                        if str(geometry.lod) not in all_LoDs:
                            all_LoDs.append(str(geometry.lod))
        all_LoDs.sort()
        fileResult["gml_lod"] = ", ".join(all_LoDs)

        fileResult["ade"] = ", ".join(singleFile.ades)
        numOfBuilding = len(singleFile.building_ids)
        fileResult["number_of_cityobject_members"] = (
            numOfBuilding + singleFile.num_notLoaded_CityObjectMembers
        )
        fileResult["number_of_buildings"] = numOfBuilding
        fileResult["number_of_buildingParts"] = buildingPart_counter
        fullResult[singleFile.filepath] = fileResult

    return fileResult


def search_dataset(
    dataset: Dataset,
    borderCoordinates: list = None,
    addressRestriciton: dict = None,
    inplace: bool = False,
) -> Dataset:
    """searches dataset for buildings within coordinates and matching address values

    Parameters
    ----------
    borderCoordinates : list, optional
        2D array of 2D coordinates
    addressRestriciton : dict, optional
        dict key:value tagName:tagValue pairing
    inplace : bool, optional
        default False, if True edits current dataset, if False creates deepcopy

    Returns
    -------
    object
        _description_
    """

    if inplace:
        newDataset = dataset
    else:
        newDataset = copy.deepcopy(dataset)

    if borderCoordinates is None and addressRestriciton is None:
        return newDataset

    if borderCoordinates is not None:
        if borderCoordinates[0] != borderCoordinates[-1]:
            borderCoordinates.append(borderCoordinates[0])
        border = mplP.Path(borderCoordinates)
    else:
        border = None

    toDelete = []
    uncheckedBIDs = list(newDataset.buildings.keys())
    for building_id in uncheckedBIDs:

        if border is not None:
            res = check_if_building_in_coordinates(
                newDataset.buildings[building_id], borderCoordinates, border
            )

            if not res:
                toDelete.append(building_id)
                continue

        if addressRestriciton is not None:
            res = check_building_for_address(
                newDataset.buildings[building_id], addressRestriciton
            )

            if not res:
                toDelete.append(building_id)
                continue

    for building_id in toDelete:
        del newDataset.buildings[building_id]

    return newDataset


def check_if_building_in_coordinates(
    building: AbstractBuilding, borderCoordinates: list, border: mplP.Path = None
) -> bool:
    """checks if a building or any of the building parts of a building
    are located inside the given borderCoordiantes

    Parameters
    ----------
    borderCoordinates : list
        a 2D array of 2D coordinates
    border : mplP.Path, optional
        borderCoordinates as a matplotlib.path.Path, by default None

    Returns
    -------
    bool
        True if building of any building part is within borderCoordinates
    """
    if border is None:
        border = mplP.Path(np.array(borderCoordinates))

    # check for the geometry of the building itself
    res = _check_if_within_border(building, borderCoordinates, border)
    if res:
        return True

    for buildingPart in building.get_building_parts():
        res = _check_if_within_border(buildingPart, borderCoordinates, border)
        if res:
            return True

    return False


def check_building_for_address(
    building: AbstractBuilding, addressRestriciton: dict
) -> bool:
    """checks if the address of the building matches the restriction

    Parameters
    ----------
    addressRestriciton : dict
        key: value pair of CoreAddress attribute and wanted value

    Returns
    -------
    bool
        returns True if all conditions are met for the building or
        at least one buildingPart
    """
    if not building.address.address_is_empty():
        res = building.address.check_address(addressRestriciton)
        if res:
            return True

    for buildingPart in building.get_building_parts():
        if not buildingPart.address.address_is_empty():
            res = buildingPart.address.check_address(addressRestriciton)
            if res:
                return True

    return False


def _check_if_within_border(
    building: AbstractBuilding, borderCoordinates: list, border: mplP.Path
) -> bool | None:
    """checks if a AbstractBuilding is located within the borderCoordinates

    Parameters
    ----------
    borderCoordinates : list
        2D list of 2D border coordinates

    border : mplP.Path
        matplotlib.path Path of given coordinates

    Returns
    -------
    bool | None
        True:  building is located inside the border coordintes
        False: building is located outside the border coordinates
        None:  building has no ground reference
    """

    grounds = building.get_surfaces(["GroundSurface"])
    if len(grounds) != 0:
        selected_surface = grounds
    elif building.get_geometries(["RoofSurface"]) != []:
        selected_surface = building.get_geometries(["RoofSurface"])
    else:
        return None

    for surface in selected_surface:
        two_2array = np.delete(surface.gml_surface_2array, -1, 1)
        res = _border_check(border, borderCoordinates, two_2array)
        if res:
            return True
    return False


def _border_check(
    border: mplP.Path, list_of_border: list, list_of_coordinates: list
) -> bool:
    """any of the coordinates in each list lies within the area of the other list

    Parameters
    ----------
    border : mplP.Path
        first area as a mpl.path.Path (for performance reasons)
    list_of_border : list
        list of the coordinates of the first area
    list_of_coordinates : list
        list of the coordinates of the second area

    Returns
    -------
    bool
        returns True if both areas have an overlap
    """
    for point in list_of_coordinates:
        if border.contains_point(point):
            return True
    n_border = mplP.Path(np.array(list_of_coordinates))
    for point in list_of_border:
        if n_border.contains_point(point):
            return True
    return False


def check_building_for_border_and_address(
    building: Building,
    borderCoordinates: list[list[float]] | None,
    addressRestriciton: dict | None,
    border: mplP.Path | None,
) -> bool:
    """checks if a building is located within the border and has the given address

    Parameters
    ----------
    building : Building
        building to check
    borderCordinates : list[list[float]], optional
        2D array of 2D coordinates
    addressRestriciton : dict, optional
        key: value pair of CoreAddress attribute and wanted value
    border : mplP.Path, optional
        borderCoordinates as a matplotlib.path.Path

    Returns
    -------
    bool
        True if building is located within border and has the given address
    """
    if borderCoordinates is None and addressRestriciton is None:
        return True

    if borderCoordinates is not None and border is None:
        border = mplP.Path(np.array(borderCoordinates))

    if border is not None:
        res_coor = check_if_building_in_coordinates(building, borderCoordinates, border)

    if not building.address.address_is_empty():
        res_addr = building.address.check_address(addressRestriciton)

    if border is not None and addressRestriciton is None:
        return res_coor
    elif border is None and addressRestriciton is not None:
        return res_addr
    return res_coor and res_addr
