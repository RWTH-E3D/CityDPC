from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyStadt.dataset import Dataset

import numpy as np
import matplotlib.path as mplP
import copy


def analysis(dataset: Dataset) -> dict:
    """general file analysis based on CityATB

    Parameters
    ----------
    data : Dataset
        CityPY dataset

    Returns
    -------
    dict
        contains results with keys:
        - gml_version
        - gml_name
        - crs
        - gml_lod
        - ade
        - number_of_cityobject_members
        - number_of_buildings
        - number_of_buildingParts

    """

    result = {}

    result["gml_version"] = dataset._files[0].cityGMLversion
    result["gml_name"] = dataset._files[0].gmlName
    result["crs"] = dataset.srsName

    all_LoDs = []
    buildingPart_counter = 0
    for building in dataset.get_building_list():
        if building.lod not in all_LoDs:
            all_LoDs.append(building.lod)
        if building.has_building_parts():
            for buildingPart in building.building_parts:
                buildingPart_counter -=- 1
                if buildingPart.lod not in all_LoDs:
                    all_LoDs.append(buildingPart.lod)
    all_LoDs.sort()
    result["gml_lod"] = ', '.join(all_LoDs)
    
    result["ade"] = ', '.join(dataset._files[0].ades)
    numOfBuilding = dataset.size()
    result["number_of_cityobject_members"] = numOfBuilding + \
        len(dataset.otherCityObjectMembers)
    result["number_of_buildings"] = numOfBuilding
    result["number_of_buildingParts"] = buildingPart_counter

    return result


def search_dataset(dataset: Dataset, borderCoordinates: list= None, addressRestriciton: dict= None, 
                    inplace: bool= False) -> Dataset:
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

    if borderCoordinates == None and addressRestriciton == None:
        return newDataset
    
    if borderCoordinates != None:
        if borderCoordinates[0] != borderCoordinates[-1]:
            borderCoordinates.append(borderCoordinates[0])
        border = mplP.Path(borderCoordinates)
    else:
        border = None
    
    for file in newDataset._files:
        if border != None:
            [x0, y0] = file.lowerCorner
            [x1, y1] = file.upperCorner
            fileEnvelopeCoor = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

            # envelope is outside border
            if not _border_check(border, borderCoordinates, fileEnvelopeCoor):
                for building_id in file.building_ids:
                    del newDataset.buildings[building_id]
                newDataset._files.remove(file)
                continue
            
        toDelete = []
        for building_id in file.building_ids:
            
            if border != None:
                res = newDataset.buildings[building_id].check_if_building_in_coordinates(borderCoordinates, \
                                                                                    border)
                if not res:
                    toDelete.append(building_id)
                    continue

            if addressRestriciton != None:
                res = newDataset.buildings[building_id].check_building_for_address(addressRestriciton)

                if not res:
                    toDelete.append(building_id)
                    continue

        for building_id in toDelete:
            del newDataset.buildings[building_id]
            file.building_ids.remove(building_id)

    return newDataset



def _border_check(border: mplP.Path, list_of_border:list, list_of_coordinates:list) \
        -> bool:
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
