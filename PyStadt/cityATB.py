import numpy as np
import matplotlib.path as mplP


def analysis(dataset:object) -> dict:
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



def border_check(border: mplP.Path, list_of_border:list, list_of_coordinates:list) \
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
    n_border = mplP(np.array(list_of_coordinates))
    for point in list_of_border:
        if n_border.contains_point(point):
            return True
    return False
