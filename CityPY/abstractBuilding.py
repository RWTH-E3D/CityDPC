import numpy as np
import lxml.etree as ET
from scipy.spatial import ConvexHull
import matplotlib.path as mplP


import CityPY.gmlUtils as gmlUtils
from CityPY.surfacegml import SurfaceGML
from CityPY.cityATB import border_check


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
        self.lod = None

        self.address = {}

    def load_data_from_xml_element(self, element: ET.Element, nsmap: dict) -> None:
        """gathers information from a single abstract building from given lxml element

        Parameters
        ----------
        element : ET.Element
            either building or building part
        nsmap : dict
            namespace map of the root xml/gml file in form of a dicitionary 
        """
        self.walls, self.roofs, self.grounds, self.closure, self.lod = get_building_surfaces_from_xml_element(
            element, nsmap)

        if self.roofs != {}:
            self.roof_volume = 0
            for roof_surface in self.roofs.values():
                if np.all(roof_surface.gml_surface_2array == roof_surface.gml_surface_2array[0,:], axis = 0)[2]:
                    # roof surface is flat -> no volume to calculate
                    continue
                minimum_roof_height = np.min(roof_surface.gml_surface_2array, axis=0)[2]
                closing_points = np.array(roof_surface.gml_surface_2array, copy=True)
                closing_points[:, 2] = minimum_roof_height
                closed = np.concatenate([closing_points, roof_surface.gml_surface_2array])
                hull = ConvexHull(closed)
                self.roof_volume += round(hull.volume, 3)

        address_E = element.find('bldg:address', nsmap)
        for tag in address_E.iter():
            if tag.text != None:
                self.address[f"{tag.prefix}:{ET.QName(tag).localname}"] = tag.text
        

    def has_3Dgeometry(self) -> bool:
        """checks if abstractBuilding has geometry

        to return true the building needs to have at least one roof geometry
        one ground geometry and either a wall or closure geomety

        Returns
        -------
        bool
            
        """
        if self.roofs != {} and self.grounds != {} and (self.walls != {} or self.closure != {}):
            return True
        else:
            return False
        

    def _check_if_within_border(self, borderCoordinates: list, \
                                border: mplP.Path) -> bool | None:
        """checks if a AbstractBuilding is located within the borderCoordinates

        Parameters
        ----------
        borderCoordinates : list
            list of 2D border coordinates

        border : mplP.Path
            matplotlib.path Path of given coordinates

        Returns
        -------
        bool | None
            True:  building is located inside the border coordintes
            False: building is located outside the border coordinates
            None:  building has no ground reference
        """
        
        if self.grounds != {}:
            selected_surface = self.grounds
        elif self.roofs != {}:
            selected_surface = self.roofs
        else:
            return None
        
        for surface in selected_surface:
            surface_2d_coor = np.delete(surface.reshape(-1, 3), 2, 1)
            res = border_check(border, borderCoordinates, surface_2d_coor)
            if res:
                return True
        return False


    def _check_address(self, addressRestriciton: dict) -> bool:
        """checks if the address building matches the restrictions

        Parameters
        ----------
        addressRestriciton : dict
            list of address xml keys and their values
            e.g. xal:LocalityName = Aachen

        Returns
        -------
        bool
            True:  building address matches restrictions
            False: building address does not match restrictions
        """
        for key, value in addressRestriciton.items():
            if not key in self.address.keys():
                return False
            if self.address[key] != value:
                return False
            
        return True




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
    
    def get_building_parts(self) -> list[BuildingPart]:
        """return a list of building parts of building

        Returns
        -------
        list[BuildingPart]
            
        """
        return self.building_parts

    def get_building_part_ids(self) -> list:
        """returns list of building part ids of given building

        Returns
        -------
        list
            all building part ids of building
        """
        return [x.id for x in self.building_parts]


    def check_if_building_in_coordinates(self, borderCoordinates: list, 
                                         border: mplP.Path= None) -> bool:
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
        if border == None:
            border = mplP.Path(np.array(borderCoordinates))

        # check for the geometry of the building itself
        res = self._check_if_within_border(borderCoordinates, border)
        if res:
            return True
        
        for buildingPart in self.get_building_parts():
            res = buildingPart._check_if_within_border(borderCoordinates, border)
            if res:
                return True
            
        return False
    
    def check_building_for_address(self, addressRestriciton: dict) -> bool:

        res = self._check_address(addressRestriciton)
        if res:
            return True
        
        for buildingPart in self.get_building_parts():
            res = buildingPart._check_address(addressRestriciton)
            if res:
                return True
            
        return False
        
    


def get_building_surfaces_from_xml_element(element: ET.Element, nsmap: dict) \
                                          -> tuple[dict, dict, dict, dict, str]:
    """gathers surfaces from element and categories them

    Parameters
    ----------
    element : ET.Element
        lxml element of an abstracBuilding
    nsmap : dict
       namespace map of the root xml/gml file in form of a dicitionary 

    Returns
    -------
    tuple[dict, dict, dict, dict, str]
        dictionaries : are in the order walls, roofs, grounds, closure
            the dicitionaries have a key value pairing of gml:id : coordinates (3 dimensional)
        str: str of found building LoD
        
    """
    lod = None

    # check if building is LoD0
    lod0FootPrint_E = element.find('bldg:lod0FootPrint', nsmap)
    lod0RoofEdge_E = element.find('bldg:lod0RoofEdge', nsmap)
    if lod0FootPrint_E != None or lod0RoofEdge_E != None:
        
        grounds = {}
        if lod0FootPrint_E != None:
            poly_E = lod0FootPrint_E.findall('.//gml:Polygon', nsmap)
            poly_id = poly_E.attrib['{http://www.opengis.net/gml}id']
            coordinates = get_polygon_coordinates_from_element(poly_E, nsmap)
            grounds_id = poly_id if poly_id else f"poly_{i}"
            grounds = {grounds_id: SurfaceGML(coordinates.ravel(), grounds_id, "LoD0_footPrint")}

        roofs = {}
        if lod0RoofEdge_E != None:
            poly_E = lod0RoofEdge_E.findall('.//gml:Polygon', nsmap)
            poly_id = poly_E.attrib['{http://www.opengis.net/gml}id']
            coordinates = get_polygon_coordinates_from_element(poly_E, nsmap)
            roof_id = poly_id if poly_id else f"poly_{i}"
            roof = {roof_id: SurfaceGML(coordinates.ravel(), roof_id, "LoD0_roofEdge")}

        return walls, roof, ground, {}, "0"


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

        roof = {roof_id: SurfaceGML(all_poylgons[roof_id].ravel(), roof_id, "LoD1_roof")}
        del all_poylgons[roof_id]
        ground = {ground_id: SurfaceGML(all_poylgons[ground_id].ravel(), ground_id, "LoD1_ground")}
        del all_poylgons[ground_id]
        
        walls = {}
        for wall_id, coordinates in all_poylgons.items():
            walls[wall_id] = SurfaceGML(coordinates.ravel(), wall_id, "LoD1_wall")
    
        return walls, roof, ground, {}, "1"

    # everything greater than LoD1
    walls = get_surface_dict_from_element(
        element, nsmap, "bldg:boundedBy/bldg:WallSurface")
    roofs = get_surface_dict_from_element(
        element, nsmap, "bldg:boundedBy/bldg:RoofSurface")
    grounds = get_surface_dict_from_element(
        element, nsmap, "bldg:boundedBy/bldg:GroundSurface")
    closure = get_surface_dict_from_element(
        element, nsmap, "bldg:boundedBy/bldg:ClosureSurface")
    
    # searching for LoD
    for elem in element.iter():
        if elem.tag.split("}")[1].startswith('lod'):
            lod = elem.tag.split('}')[1][3]

    return walls, roofs, grounds, closure, lod


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
        used_id = id if id else f"{id_str}_{i}"
        result[used_id] = SurfaceGML(coordinates.ravel(), used_id, target_str.rsplit(":")[-1])
    return result


