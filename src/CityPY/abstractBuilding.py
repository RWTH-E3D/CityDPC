import numpy as np
import lxml.etree as ET
from scipy.spatial import ConvexHull


import gmlUtils


class _AbstractBuilding():
    """contains all methods and properties that are use by buildings and building parts
    """

    def __init__(self, id: str) -> None:
        self.gml_id = id
        self.walls = {}
        self.roofs = {}
        self.grounds = {}
        self.closure = {}
        self.roof_volume = None

    def load_data_from_xml_element(self, element: ET.Element, nsmap: dict) -> None:
        """gathers information from a single abstract building from given lxml element

        Parameters
        ----------
        element : ET.Element
            either building or building part
        nsmap : dict
            namespace map of the root xml/gml file in form of a dicitionary 
        """
        self.walls, self.roofs, self.grounds, self.closure = get_building_surfaces_from_xml_element(
            element, nsmap)

        if self.roofs != {}:
            self.roof_volume = 0
            for points in self.roofs.values():
                if np.all(points == points[0,:], axis = 0)[2]:
                    # roof surface is flat -> no volume to calculate
                    continue
                minimum_roof_height = np.min(points, axis=0)[2]
                closing_points = np.array(points, copy=True)
                closing_points[:, 2] = minimum_roof_height
                closed = np.concatenate([closing_points, points])
                hull = ConvexHull(closed)
                self.roof_volume += round(hull.volume, 3)

    def has_geometry(self) -> bool:
        """checks if abstractBuilding has geometry

        to return true the building needs to at least one roof geometry
        one ground geometry and either a wall or closure geomety

        Returns
        -------
        bool
            
        """
        if self.roofs != {} and self.grounds != {} and (self.walls != {} or self.closure != {}):
            return True
        else:
            return False


class Building(_AbstractBuilding):
    """extends _AbstractBuilding class

    contains attributes and functions specific to Buildings

    Parameters
    ----------
    _AbstractBuilding : _type_

    """

    def __init__(self, id: str) -> None:
        super().__init__(id)
        self.building_parts = []
        self.is_building_part = False

    def has_building_parts(self) -> bool:
        """checks if the building has building parts

        Returns
        -------
        bool
            true if building has building parts
        """
        return self.building_parts != []

    def building_part_ids(self) -> list:
        """returns a list of gml:id's of the building parts within the building"""
        return [x.id for x in self.building_parts]


class BuildingPart(_AbstractBuilding):
    """extends _AbstractBuilding class

    contains attributes and functions specific to Buildings

    Parameters
    ----------
    _AbstractBuilding : _type_

    """

    def __init__(self, id: str, parent_id: str) -> None:
        super().__init__(id)
        self.parent_gml_id = parent_id
        self.is_building_part = True




def get_building_surfaces_from_xml_element(element: ET.Element, nsmap: dict) -> tuple[dict, dict, dict, dict]:
    """gathers surfaces from element and categories them

    Parameters
    ----------
    element : ET.Element
        lxml element of an abstracBuilding
    nsmap : dict
       namespace map of the root xml/gml file in form of a dicitionary 

    Returns
    -------
    tuple[dict, dict, dict, dict]
        dictionaries are in the order: walls, roofs, grounds, closure
        the dicitionaries have a key value pairing of gml:id : coordinates (3 dimensional)
    """
    # check if building is LoD1
    lod1Solid_E = element.find('bldg:lod1Solid', nsmap)
    if lod1Solid_E != None:

        # get all polygons and extract their coordinates
        poly_Es = lod1Solid_E.findall('.//gml:Polygon', nsmap)
        all_poylgons = {}
        for i, poly_E in enumerate(poly_Es):
            poly_id = poly_E.attrib['{http://www.opengis.net/gml}id']
            coordinates = get_polygon_coordinates_from_element(poly_E, nsmap)
            all_poylgons[poly_id if poly_id else f"poly_{i}"] = coordinates

        # search for polygon with lowest and highest average height
        # lowest average height is ground surface
        # highest average height is roof surface
        # all other ar wall surfaces
        ground_id = None
        ground_average_height = None
        roof_id = None
        roof_average_height = None

        for poly_id, polygon in all_poylgons.itmes():
            polygon_average_height = sum(
                [i[2] for i in polygon]) / len(polygon)

            if ground_id == None:
                ground_id = poly_id
                ground_average_height = polygon_average_height
            elif polygon_average_height < ground_average_height:
                ground_id = poly_id
                ground_average_height = polygon_average_height

            if roof_id == None:
                roof_id = poly_id
                roof_average_height = polygon_average_height
            elif polygon_average_height > roof_average_height:
                roof_id = poly_id
                roof_average_height = polygon_average_height

        roof = {roof_id: all_poylgons[roof_id]}
        del all_poylgons[roof_id]
        ground = {ground_id: all_poylgons[ground_id]}
        del all_poylgons[ground_id]
        return all_poylgons, roof, ground, []

    # everything greater than LoD1
    walls = get_surface_dict_from_element(
        element, nsmap, "bldg:boundedBy/bldg:WallSurface")
    roofs = get_surface_dict_from_element(
        element, nsmap, "bldg:boundedBy/bldg:RoofSurface")
    grounds = get_surface_dict_from_element(
        element, nsmap, "bldg:boundedBy/bldg:GroundSurface")
    closure = get_surface_dict_from_element(
        element, nsmap, "bldg:boundedBy/bldg:ClosureSurface")

    return walls, roofs, grounds, closure


def get_polygon_coordinates_from_element(polygon_element: ET.Element, nsmap: dict) -> np.ndarray:
    """search the element for coordinates

    takes coordinates from both gml:posList and gml:pos elements
    returns an array of the 3D coordinates

    Parameters
    ----------
    polygon_element : ET.Element
        lxml element of a gml:polygon
    nsmap : dict
        namespace map of the root xml/gml file in form of a dicitionary 

    Returns
    -------
    np.ndarray
       numpy array of coordinates in 3D
    """
    polygon = []
    # searching for list of coordinates
    posList_E = polygon_element.find('.//gml:posList', nsmap)
    if posList_E != None:
        polyStr = posList_E.text
    else:
        # searching for individual coordinates in polygon
        pos_Es = polygon_element.findall('.//gml:pos', nsmap)
        for pos_E in pos_Es:
            polygon.append(pos_E.text)
        polyStr = ' '.join(polygon)
    return gmlUtils.get_3D_posList_from_str(polyStr)


def get_surface_dict_from_element(element: ET.Element, nsmap: dict, target_str: str, id_str: str = "") -> dict:
    """creates a dictionary from surfaces of lxml element
    

    Parameters
    ----------
    element : ET.Element
        lxml element of an abstracBuilding
    nsmap : dict
        namespace map of the root xml/gml file in form of a dicitionary 
    target_str : str
        element to take coordinates from e.g. 'bldg:boundedBy/bldg:RoofSurface'
    id_str : str, optional
        base string for dict index, by default ""

    Returns
    -------
    dict
        key-value pairing of gml:id of the surface and array of coordinates
    """
    result = {}
    if not id_str:
        id_str = element.attrib['{http://www.opengis.net/gml}id'] + \
            "_" + target_str.split(":")[-1]
    for i, surface_E in enumerate(element.findall(target_str, nsmap)):
        if '{http://www.opengis.net/gml}id' in surface_E.attrib:
            id = surface_E.attrib['{http://www.opengis.net/gml}id']
        else:
            id = None
        poly_E = surface_E.find('.//gml:Polygon', nsmap)
        coordinates = get_polygon_coordinates_from_element(poly_E, nsmap)
        result[id if id else f"{id_str}_{i}"] = coordinates
    return result


