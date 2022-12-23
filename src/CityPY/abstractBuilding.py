import numpy as np
import lxml.etree as ET
from scipy.spatial import ConvexHull


import gmlUtils


class _AbstractBuilding():
    """
    contains all methods and properties that are use by buildings and building parts
    """

    def __init__(self, id: str) -> None:
        self.gml_id = id
        self.walls = {}
        self.roofs = {}
        self.grounds = {}
        self.roof_volume = None

    def load_data_from_xml_element(self, element: ET.Element, nsmap: dict) -> None:
        """collects data from from lxml.etree element"""
        self.walls, self.roofs, self.grounds = get_building_surfaces_from_xml_element(
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
        """checks if walls, roofs and grounds are in building"""
        if self.walls != {} and self.roofs != {} and self.grounds != {}:
            return True
        elif self.walls == {} and self.roofs == {} and self.grounds == {}:
            return False
        else:
            return False


class Building(_AbstractBuilding):
    """
    class to store basic information of a CityGML building
    """

    def __init__(self, id: str) -> None:
        super().__init__(id)
        self.building_parts = []
        self.is_building_part = False

    def has_building_parts(self) -> bool:
        """returns True if the building has building parts and False if not"""
        return self.building_parts != []

    def building_part_ids(self) -> list:
        """returns a list of gml:id's of the building parts within the building"""
        return [x.id for x in self.building_parts]


class BuildingPart(_AbstractBuilding):
    """
    class to store basic information of a CityGML building part
    """

    def __init__(self, id: str, parent_id: str) -> None:
        super().__init__(id)
        self.parent_gml_id = parent_id
        self.is_building_part = True




def get_building_surfaces_from_xml_element(element: ET.Element, nsmap: dict) -> tuple[list, list, list]:
    """gathers surfaces from element and categories them"""
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
        return all_poylgons, roof, ground

    # everything greater than LoD1
    walls = get_surface_dict_from_element(
        element, nsmap, "bldg:boundedBy/bldg:WallSurface")
    roofs = get_surface_dict_from_element(
        element, nsmap, "bldg:boundedBy/bldg:RoofSurface")
    grounds = get_surface_dict_from_element(
        element, nsmap, "bldg:boundedBy/bldg:GroundSurface")

    return walls, roofs, grounds


def get_polygon_coordinates_from_element(element: ET.Element, nsmap: dict) -> list:
    """
    searched the given element for gml:posList and gml:pos elements and
    returns poylgon id and a 2D array of the given coordinates
    """
    polygon = []
    # searching for list of coordinates
    posList_E = element.find('.//gml:posList', nsmap)
    if posList_E != None:
        polyStr = posList_E.text
    else:
        # searching for individual coordinates in polygon
        pos_Es = element.findall('.//gml:pos', nsmap)
        for pos_E in pos_Es:
            polygon.append(pos_E.text)
        polyStr = ' '.join(polygon)
    return gmlUtils.get_3D_posList_from_str(polyStr)


def get_surface_dict_from_element(element: ET.Element, nsmap: dict, target_str: str, id_str: str = None) -> dict:
    """
    creates a dictionary from surfaces  with target_str (e.g. 'bldg:boundedBy/bldg:RoofSurface')
    element should point to a _AbstractBuiling like element
    where the gml:id of the surface is the index and the value is a 2D array of coordinates
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


