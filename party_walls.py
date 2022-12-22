import lxml.etree as ET
import os
from shapely import geometry as slyGeom
import numpy as np


def get_3D_posList_from_str(text: str) -> list:
    """convert string to a 3D list of coordinates"""
    coor_list = [float(x) for x in text.split()]
    # creating 3D coordinate array from 1D array
    coor_list = [list(x) for x in zip(
        coor_list[0::3], coor_list[1::3], coor_list[2::3])]
    return np.array(coor_list)


def get_norm_vector_of_surface(coordinates: np.array) -> np.ndarray:
    """calculates norm vector based on first 3 coordinates of polygon"""
    crossed = np.cross(coordinates[0] - coordinates[1],
                       coordinates[0] - coordinates[2])
    norm = np.linalg.norm(crossed)
    # p is a measure of precission. while coding, i had a test vector pair
    # only differing by one digit at the 16th decimal place therefore roundig to 12 decimal places
    p = 12
    if np.array_equal(crossed, np.array([0, 0, 0])):
        return None
    return np.around((1 / norm) * crossed, p)


def rotation_matrix_from_vectors(vec1: np.array, vec2: np.array) -> (np.ndarray | None):
    """this function was adapted from https://stackoverflow.com/a/59204638"""
    """ Find the rotation matrix that aligns vec1 to vec2
    :param vec1: A 3d "source" vector
    :param vec2: A 3d "destination" vector
    :return mat: A transform matrix (3x3) which when applied to vec1, aligns it with vec2.
    """
    a, b = (vec1 / np.linalg.norm(vec1)), (vec2 / np.linalg.norm(vec2))
    v = np.cross(a, b)
    c = np.dot(a, b)
    s = np.linalg.norm(v)
    kmat = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])

    return np.eye(3) + kmat + kmat.dot(kmat) * ((1 - c) / (s ** 2))


def coor_dict_to_normvector_dict(surface_dict: dict) -> dict:
    """calculates the normvectors of a surface dict based on the first 3 coordinates"""
    results = {}
    for gml_id, coordinates in surface_dict.items():
        vector = get_norm_vector_of_surface(coordinates)
        if vector is None:
            # cross product of first 3 points is null vector -> points don't create a plane
            continue
        results[gml_id] = vector
    return results


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
    return get_3D_posList_from_str(polyStr)


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


def get_building_surfaces_from_element(element: ET.Element, nsmap: dict) -> tuple[list, list, list]:
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


def find_party_walls(buildingLike_0: object, buildingLike_1: object):
    """takes to buildings and searches for party walls"""
    party_walls = []
    b_0_normvectors = coor_dict_to_normvector_dict(buildingLike_0.walls)
    b_1_normvectors = coor_dict_to_normvector_dict(buildingLike_1.walls)
    for gml_id_0, vector_0 in b_0_normvectors.items():
        for gml_id_1, vector_1 in b_1_normvectors.items():
            if np.array_equal(vector_0, vector_1) or np.array_equal(vector_0, -vector_1):
                # create rotaion matrix, that 3rd axis can be ignored
                # check if rotation is needed
                if np.array_equal(vector_0, np.array([0, 1, 0])) or np.array_equal(vector_0, -np.array([0, 1, 0])):
                    # rotation not needed
                    poly_0_rotated = buildingLike_0.walls[gml_id_0]
                    poly_1_rotated = buildingLike_1.walls[gml_id_1]
                else:
                    # needs to be rotated
                    rotation_matrix = rotation_matrix_from_vectors(
                        vector_0, np.array([0, 1, 0]))
                    # rotate coordinates
                    poly_0_rotated = np.dot(
                        buildingLike_0.walls[gml_id_0], rotation_matrix)
                    poly_1_rotated = np.dot(
                        buildingLike_1.walls[gml_id_1], rotation_matrix)

                # check distance in rotated y direction (if distance is larger than 0.15 [uom] walls shouldn't be considered as party walls)
                if abs(np.mean(poly_0_rotated, axis=0)[1] - np.mean(poly_1_rotated, axis=0)[1]) > 0.15:
                    continue

                # delete 3rd axis
                poly_0_rotated_2D = np.delete(poly_0_rotated, 1, axis=1)
                poly_1_rotated_2D = np.delete(poly_1_rotated, 1, axis=1)
                # create shapely polygons
                p_0 = slyGeom.Polygon(poly_0_rotated_2D)
                p_1 = slyGeom.Polygon(poly_1_rotated_2D)
                # calculate intersection
                intersection = p_0.intersection(p_1)
                if not intersection.is_empty:
                    if intersection.area > 5:
                        id_0 = buildingLike_0.gml_id if not buildingLike_0.is_building_part else buildingLike_0.parent_gml_id + \
                            "/" + buildingLike_0.gml_id
                        id_1 = buildingLike_1.gml_id if not buildingLike_1.is_building_part else buildingLike_1.parent_gml_id + \
                            "/" + buildingLike_1.gml_id
                        party_walls.append(
                            [id_0, gml_id_0, id_1, gml_id_1, intersection.area])
                        # party_walls.append([gml_id_0, gml_id_1, intersection.area])
    return party_walls


class _AbstractBuilding():
    """
    contains all methods and properties that are use by buildings and building parts
    """

    def __init__(self, id: str) -> None:
        self.gml_id = id
        self.walls = {}
        self.roofs = {}
        self.grounds = {}

    def load_data_from_element(self, element: ET.Element, nsmap: dict) -> None:
        """collects data from from lxml.etree element"""
        self.walls, self.roofs, self.grounds = get_building_surfaces_from_element(
            element, nsmap)

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


class Dataset():
    """
    class to input a single or multiple files and gather basic information on them

    """

    def __init__(self, name: str = None) -> None:
        self.name = name
        self._files = {}
        self.buildings = []
        self.party_walls = None

    def size(self) -> int:
        """return the number of buildings within the dataset"""
        return len(self.buildings)

    def add_buildings_from_file(self, filepath: str):
        """adds buildings from filepath to the dataset"""
        filename = os.path.basename(filepath)
        parser = ET.XMLParser(remove_blank_text=True)
        tree = ET.parse(filepath, parser)
        root = tree.getroot()
        nsmap = root.nsmap

        buildings = []

        # find all buildings within file
        buildings_in_file = root.findall(
            'core:cityObjectMember/bldg:Building', nsmap)
        for building_E in buildings_in_file:
            building_id = building_E.attrib['{http://www.opengis.net/gml}id']
            new_building = Building(building_id)
            new_building.load_data_from_element(building_E, nsmap)

            bps_in_bldg = building_E.findall(
                'bldg:consistsOfBuildingPart/bldg:BuildingPart', nsmap)
            for bp_E in bps_in_bldg:
                bp_id = bp_E.attrib['{http://www.opengis.net/gml}id']
                new_building_part = BuildingPart(bp_id, building_id)
                new_building_part.load_data_from_element(bp_E, nsmap)
                new_building.building_parts.append(new_building_part)

            self.buildings.append(new_building)
            buildings.append(building_id)
        self._files[filename] = buildings

    def get_buildings(self) -> list[Building]:
        """returns a list of all buildings within dataset"""
        return self.buildings

    def check_for_party_walls(self):
        """checks if buildings in dataset have """
        self.party_walls = []
        for i, building_0 in enumerate(self.buildings):
            polys_in_building_0 = []
            # get coordinates from all groundSurface of building geometry
            if building_0.has_geometry():
                for key, coordiantes in building_0.grounds.items():
                    polys_in_building_0.append(
                        {"poly_id": key, "coor": coordiantes, "parent": building_0})

            # get coordinates from all groundSurface of buildingPart geometries
            if building_0.has_building_parts():
                for b_part in building_0.building_parts:
                    if b_part.has_geometry():
                        for key, coordiantes in b_part.grounds.items():
                            polys_in_building_0.append(
                                {"poly_id": key, "coor": coordiantes, "parent": b_part})

            # self collision check
            for j, poly_0 in enumerate(polys_in_building_0):
                p_0 = self._create_buffered_polygon(poly_0["coor"])
                for poly_1 in polys_in_building_0[j+1:]:
                    p_1 = slyGeom.Polygon(poly_1["coor"])
                    if not p_0.intersection(p_1).is_empty:
                        party_walls = find_party_walls(
                            poly_0["parent"], poly_1["parent"])
                        if party_walls != []:
                            self.party_walls.extend(party_walls)

            # collision with other buildings
            for building_1 in self.buildings[i+1:]:
                # collision with the building itself
                if building_1.has_geometry():
                    for poly_0 in polys_in_building_0:
                        p_0 = self._create_buffered_polygon(poly_0["coor"])
                        for gml_id, poly_1 in building_1.grounds.items():
                            p_1 = slyGeom.Polygon(poly_1)
                            if not p_0.intersection(p_1).is_empty:
                                party_walls = find_party_walls(
                                    poly_0["parent"], building_1)
                                if party_walls != []:
                                    self.party_walls.extend(party_walls)
                                break

                # collsion with a building part of the building
                if building_1.has_building_parts():
                    for b_part in building_1.building_parts:
                        if b_part.has_geometry():
                            for poly_0 in polys_in_building_0:
                                p_0 = self._create_buffered_polygon(poly_0["coor"])
                                for gml_id, poly_1 in b_part.grounds.items():
                                    p_1 = slyGeom.Polygon(poly_1)
                                    if not p_0.intersection(p_1).is_empty:
                                        # To-Do: building (or bp) with other building part
                                        party_walls = find_party_walls(
                                            poly_0["parent"], b_part)
                                        if party_walls != []:
                                            self.party_walls.extend(
                                                party_walls)
                                        break

    def _create_buffered_polygon(self, coordinates: np.ndarray, buffer: float = 0.15) -> slyGeom.Polygon:
        """creates a buffered shapely polygon"""
        poly = slyGeom.Polygon(coordinates)
        return poly.buffer(buffer)

