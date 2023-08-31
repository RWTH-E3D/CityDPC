import os
import lxml.etree as ET
import numpy as np
from shapely import geometry as slyGeom

from CityPY.abstractBuilding import Building, BuildingPart
from CityPY.buildingFunctions import find_party_walls
from CityPY.fileUtil import CityFile





class Dataset():
    """
    class to input a single or multiple files and gather basic information on them

    """

    def __init__(self, name: str = None) -> None:
        self.name = name
        self._files = []
        self.srsName = None
        self.buildings = []
        self.otherCityObjectMembers = []
        self.party_walls = None

    def size(self) -> int:
        """return the number of buildings within the dataset"""
        return len(self.buildings)

    def add_buildings_from_xml_file(self, filepath: str):
        """adds buildings from filepath to the dataset"""
        parser = ET.XMLParser(remove_blank_text=True)
        tree = ET.parse(filepath, parser)
        root = tree.getroot()
        nsmap = root.nsmap

        building_ids = []

        # get CityGML version
        cityGMLversion = nsmap['core'].rsplit('/', 1)[-1]

        # checking for ADEs
        ades = []
        if 'energy' in nsmap:
            if nsmap['energy'] == 'http://www.sig3d.org/citygml/2.0/energy/1.0':
                ades.append('energyADE')

        # find gml envelope and check for compatability
        envelope_E = root.find('gml:boundedBy/gml:Envelope', nsmap)
        if envelope_E != None:
            fileSRSName = envelope_E.attrib['srsName']
            if self.srsName == None:
                self.srsName = fileSRSName
            elif self.srsName == fileSRSName:
                pass
            else:
                print(f"Unable to load file! Given srsName ({fileSRSName}) does not match Dataset srsName ({self.srsName})")
                return

        # find all buildings within file
        cityObjectMembers_in_file = root.findall('core:cityObjectMember', nsmap)
        for cityObjectMember_E in cityObjectMembers_in_file:
            buildings_in_com = cityObjectMember_E.findall(
                'bldg:Building', nsmap)

            for building_E in buildings_in_com:
                building_id = building_E.attrib['{http://www.opengis.net/gml}id']
                new_building = Building(building_id)
                new_building.load_data_from_xml_element(building_E, nsmap)

                bps_in_bldg = building_E.findall(
                    'bldg:consistsOfBuildingPart/bldg:BuildingPart', nsmap)
                for bp_E in bps_in_bldg:
                    bp_id = bp_E.attrib['{http://www.opengis.net/gml}id']
                    new_building_part = BuildingPart(bp_id, building_id)
                    new_building_part.load_data_from_xml_element(bp_E, nsmap)
                    new_building.building_parts.append(new_building_part)

                self.buildings.append(new_building)
                building_ids.append(building_id)
            else:
                self.otherCityObjectMembers.append(cityObjectMember_E)
        
        # find gmlName
        gmlName = None
        gmlName_E = root.find('gml:name', nsmap)
        if gmlName_E != None:
            gmlName = gmlName_E.text

        # store file related information
        self._files.append(
            CityFile(filepath, cityGMLversion, building_ids, ades, gmlName))

    def get_buildings(self) -> list[Building]:
        """returns a list of all buildings within dataset"""
        return self.buildings

    def check_for_party_walls(self):
        """checks if buildings in dataset have """
        self.party_walls = []
        for i, building_0 in enumerate(self.buildings):
            polys_in_building_0 = []
            # get coordinates from all groundSurface of building geometry
            if building_0.has_3Dgeometry():
                for key, ground in building_0.grounds.items():
                    polys_in_building_0.append(
                        {"poly_id": key, "coor": ground.gml_surface_2array, "parent": building_0})

            # get coordinates from all groundSurface of buildingPart geometries
            if building_0.has_building_parts():
                for b_part in building_0.building_parts:
                    if b_part.has_3Dgeometry():
                        for key, ground in b_part.grounds.items():
                            polys_in_building_0.append(
                                {"poly_id": key, "coor": ground.gml_surface_2array, "parent": b_part})

            # self collision check
            # this includes all walls of the building (and building parts) geometry 
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
                if building_1.has_3Dgeometry():
                    for poly_0 in polys_in_building_0:
                        p_0 = self._create_buffered_polygon(poly_0["coor"])
                        for gml_id, poly_1 in building_1.grounds.items():
                            p_1 = slyGeom.Polygon(poly_1.gml_surface_2array)
                            if not p_0.intersection(p_1).is_empty:
                                party_walls = find_party_walls(
                                    poly_0["parent"], building_1)
                                if party_walls != []:
                                    self.party_walls.extend(party_walls)
                                break

                # collsion with a building part of the building
                if building_1.has_building_parts():
                    for b_part in building_1.building_parts:
                        if b_part.has_3Dgeometry():
                            for poly_0 in polys_in_building_0:
                                p_0 = self._create_buffered_polygon(poly_0["coor"])
                                for gml_id, poly_1 in b_part.grounds.items():
                                    p_1 = slyGeom.Polygon(poly_1.gml_surface_2array)
                                    if not p_0.intersection(p_1).is_empty:
                                        # To-Do: building (or bp) with other building part
                                        party_walls = find_party_walls(
                                            poly_0["parent"], b_part)
                                        if party_walls != []:
                                            self.party_walls.extend(
                                                party_walls)
                                        break
        return self.party_walls

    def _create_buffered_polygon(self, coordinates: np.ndarray, buffer: float = 0.15) -> slyGeom.Polygon:
        """creates a buffered shapely polygon"""
        poly = slyGeom.Polygon(coordinates)
        return poly.buffer(buffer)

