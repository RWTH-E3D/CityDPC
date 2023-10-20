import os
import lxml.etree as ET
import numpy as np
from shapely import geometry as slyGeom
import matplotlib.path as mplP
import copy
import math

import PyStadt.xmlClasses as xmlClasses
from PyStadt.abstractBuilding import Building, BuildingPart
from PyStadt.buildingFunctions import find_party_walls
from PyStadt.fileUtil import CityFile
import PyStadt.cityATB as atb





class Dataset():
    """
    class to input a single or multiple files and gather basic information on them

    """

    def __init__(self, name: str = None) -> None:
        self.name = name
        self._files = []
        self.srsName = None
        self.buildings = {}
        self.otherCityObjectMembers = []
        self.party_walls = None

        self._minimum = [math.inf, math.inf, math.inf]
        self._maximum = [-math.inf, -math.inf, -math.inf]

    def size(self) -> int:
        """return the number of buildings within the dataset

        Returns
        -------
        int
            number of buildings within the dataset
        """
        return len(self.buildings)
    
    def add_buildings_from_xml_file(self, filepath: str, borderCoordinates: list= None,
                                    addressRestriciton: dict= None):
        """adds buildings from filepath to the dataset

        Parameters
        ----------
        filepath : str
            path to .gml or .xml CityGML file
        borderCoordinates : list, optional
            list of coordinates ([x0, y0], [x1, y1], ..) in fileCRS to restrict the dataset,
            by default None
        addressRestriciton : dict, optional
            dictionary of address values to restrict the dataset, by default None
        """
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
            lowerCorner = envelope_E.find('gml:lowerCorner', nsmap).text.split(' ')
            upperCorner = envelope_E.find('gml:upperCorner', nsmap).text.split(' ')
            if self.srsName == None:
                self.srsName = fileSRSName
            elif self.srsName == fileSRSName:
                pass
            else:
                print(f"Unable to load file! Given srsName ({fileSRSName}) does not match Dataset srsName ({self.srsName})")
                return
        else:
            print(f"Unable to load file! Can't find gml:Envelope for srsName defenition")
            return
        
        #creating border for coordinate restriction
        if borderCoordinates != None:
            if len(borderCoordinates) > 2:
                border = mplP.Path(np.array(borderCoordinates))
                x1 = float(lowerCorner[0])
                y1 = float(lowerCorner[1])
                x2 = float(upperCorner[0])
                y2 = float(upperCorner[1])
                fileEnvelopeCoor = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
                if not atb.border_check(border, borderCoordinates, fileEnvelopeCoor):
                    # file envelope is outside of the border coordinates
                    return
            elif len(borderCoordinates) < 3:
                print(f"Only given {len(borderCoordinates)} borderCoordinates, can't continue")
                return
        else:
            border = None

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

                if building_id in self.buildings.keys():
                    print(f"WARNING! Doubling of building id {building_id} " + \
                          f"Only first mention will be considered")
                    continue

                if border != None:
                    res_coor = new_building.check_if_building_in_coordinates(borderCoordinates, \
                                                                        border)

                if addressRestriciton != None:
                    res_addr = new_building.check_building_for_address(addressRestriciton)

                if border == None and addressRestriciton == None:
                    pass
                elif border != None and addressRestriciton == None:
                    if not res_coor:
                        continue
                elif border == None and addressRestriciton != None:
                    if not res_addr:
                        continue
                else:
                    if not (res_coor and res_addr):
                        continue
                
                self.buildings[building_id] = new_building
                building_ids.append(building_id)
            else:
                self.otherCityObjectMembers.append(cityObjectMember_E)
        
        # find gmlName
        gmlName = None
        gmlName_E = root.find('gml:name', nsmap)
        if gmlName_E != None:
            gmlName = gmlName_E.text

        # store file related information
        newCFile = CityFile(filepath, cityGMLversion, building_ids, ades, gmlName)
        if lowerCorner:
            newCFile.lowerCorner = (float(lowerCorner[0]), float(lowerCorner[1]))
        if upperCorner:
            newCFile.upperCorner = (float(upperCorner[0]), float(upperCorner[1]))
        self._files.append(newCFile)

    def get_building_list(self) -> list[Building]:
        """returns a list of all buildings in dataset

        Returns
        -------
        list
            list of all buildings in dataset
        """
        return list(self.buildings.values())
    
    def search_dataset(self, borderCoordinates: list= None, addressRestriciton: dict= None, 
                       inplace: bool= False) -> object:
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
            newDataset = self
        else:
            newDataset = copy.deepcopy(self)

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
                if not atb.border_check(border, borderCoordinates, fileEnvelopeCoor):
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

    def check_for_party_walls(self):
        """checks if buildings in dataset have """
        self.party_walls = []
        for i, building_0 in enumerate(self.get_building_list()):
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
                p_0 = _create_buffered_polygon(poly_0["coor"])
                for poly_1 in polys_in_building_0[j+1:]:
                    p_1 = slyGeom.Polygon(poly_1["coor"])
                    if not p_0.intersection(p_1).is_empty:
                        party_walls = find_party_walls(
                            poly_0["parent"], poly_1["parent"])
                        if party_walls != []:
                            self.party_walls.extend(party_walls)

            # collision with other buildings
            for building_1 in self.get_building_list()[i+1:]:
                # collision with the building itself
                if building_1.has_3Dgeometry():
                    for poly_0 in polys_in_building_0:
                        p_0 = _create_buffered_polygon(poly_0["coor"])
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
                                p_0 = _create_buffered_polygon(poly_0["coor"])
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
    

    def write_citygml_file(self, filename: str):
        """writes Dataset to citygml file

        Parameters
        ----------
        filename : str
            new filename (including path if wanted)
        """


        if self.srsName == None:
            print("unable to create file, set srsName frist")
            return
        
        nClass = xmlClasses.CGML2

        nClass.core = 'http://www.opengis.net/citygml/2.0'
        nClass.gen = 'http://www.opengis.net/citygml/generics/2.0'
        nClass.grp = 'http://www.opengis.net/citygml/cityobjectgroup/2.0'
        nClass.app = 'http://www.opengis.net/citygml/appearance/2.0'
        nClass.bldg = 'http://www.opengis.net/citygml/building/2.0'
        nClass.gml = 'http://www.opengis.net/gml'
        nClass.xal = 'urn:oasis:names:tc:ciq:xsdschema:xAL:2.0'
        nClass.xlink = 'http://www.w3.org/1999/xlink'
        nClass.xsi = 'http://www.w3.org/2001/XMLSchema-instance'

        # creating new namespacemap
        newNSmap = {None: nClass.core, 'core': nClass.core, 'gen' : nClass.gen, 'grp' : nClass.grp, 'app': nClass.app, 'bldg' : nClass.bldg, 'gml': nClass.gml,
                    'xal' : nClass.xal, 'xlink' : nClass.xlink, 'xsi' : nClass.xsi}
        
        
        
        # creating new root element
        nroot_E = ET.Element(ET.QName(nClass.core, 'CityModel'), nsmap= newNSmap)

        # creating name element
        name_E = ET.SubElement(nroot_E, ET.QName(nClass.gml, 'name'), nsmap={'gml': nClass.gml})
        name_E.text = 'created using the e3D PyStadt'

        # creating gml enevelope
        bound_E = ET.SubElement(nroot_E, ET.QName(nClass.gml, 'boundedBy'))
        envelope = ET.SubElement(bound_E, ET.QName(nClass.gml, 'Envelope'), srsName= self.srsName)
        lcorner = ET.SubElement(envelope, ET.QName(nClass.gml, 'lowerCorner'), srsDimension= "3")
        ucorner = ET.SubElement(envelope, ET.QName(nClass.gml, 'upperCorner'), srsDimension= "3")

        for building in self.get_building_list():
            cityObjectMember_E = ET.SubElement(nroot_E, ET.QName(nClass.core, 'cityObjectMember'))
            building_E = self._add_building_to_cityModel_xml(cityObjectMember_E, nClass, building)

            for buildingPart in building.building_parts:

                cOBP_E = ET.SubElement(building_E, ET.QName(nClass.bldg, 'Building'), attrib={ET.QName(nClass.gml, 'id'): building.gml_id})

                bp_E = self._add_building_to_cityModel_xml(cOBP_E, nClass, buildingPart, True)

                if building.address != None:
                    self._add_address_to_xml_building(bp_E, nClass, buildingPart)
            
            if building.address != None:
                self._add_address_to_xml_building(building_E, nClass, building)

        lcorner.text = ' '.join(map(str, self._minimum))
        ucorner.text = ' '.join(map(str, self._maximum))

        tree = ET.ElementTree(nroot_E)    
        tree.write(filename, pretty_print = True, xml_declaration=True, 
                    encoding='utf-8', standalone='yes', method="xml")



    def _add_building_to_cityModel_xml(self, parent_E: ET.Element, nClass: xmlClasses.CGML0, building: Building, is_buildingPart: bool= False) -> ET.Element:
        """adds a building or buildingPart to a cityModel

        Parameters
        ----------
        parent_E : ET.Element
            direct parent element (either cityObjectMember or consistsOfBuildingPart)
        nClass : xmlClasses.CGML0
            namespace class
        building : Building
            Building object
        is_buildingPart : bool, optional
            flag if building or buildingPart, by default False

        Returns
        -------
        ET.Element
            created element
        """

        if not is_buildingPart:
            building_E = ET.SubElement(parent_E, ET.QName(nClass.bldg, 'Building'), attrib={ET.QName(nClass.gml, 'id'): building.gml_id})
        else:
            building_E = ET.SubElement(parent_E, ET.QName(nClass.bldg, 'BuildingPart'), attrib={ET.QName(nClass.gml, 'id'): building.gml_id})

        if building.creationDate != None:
            ET.SubElement(building_E, ET.QName(nClass.core, 'creationDate')).text = building.creationDate

        if building.extRef_infromationsSystem != None and building.extRef_objName != None:
            extRef_E = ET.SubElement(building_E, ET.QName(nClass.core, 'externalReference'))
            ET.SubElement(extRef_E, ET.QName(nClass.core, 'informationSystem')).text = building.extRef_infromationsSystem
            extObj_E = ET.SubElement(extRef_E, ET.QName(nClass.core, 'externalObject'))
            ET.SubElement(extObj_E, ET.QName(nClass.core, 'name')).text = building.extRef_objName

        for key, value in building.genericStrings.items():
            newGenStr_E = ET.SubElement(building_E, ET.QName(nClass.core, 'creationDate'), name= key)
            ET.SubElement(newGenStr_E, ET.QName(nClass.gen, 'value')).text = value

        if building.function != None:
            ET.SubElement(building_E, ET.QName(nClass.bldg, 'function')).text = building.function

        if building.yearOfConstruction != None:
            ET.SubElement(building_E, ET.QName(nClass.bldg, 'yearOfConstruction')).text = building.yearOfConstruction

        if building.roofType != None:
            ET.SubElement(building_E, ET.QName(nClass.bldg, 'roofType')).text = building.roofType

        if building.measuredHeight != None:
            ET.SubElement(building_E, ET.QName(nClass.bldg, 'measuredHeight'), uom= "urn:adv:uom:m").text = building.measuredHeight

        if building.storeysAboveGround != None:
            ET.SubElement(building_E, ET.QName(nClass.bldg, 'storeysAboveGround')).text = building.storeysAboveGround

        if building.storeysBelowGround != None:
            ET.SubElement(building_E, ET.QName(nClass.bldg, 'storeysBelowGround')).text = building.storeysBelowGround

        if building.lod == "2":          
            lodnSolid_E = ET.SubElement(building_E, ET.QName(nClass.bldg, 'lod2Solid'))
            solid_E = ET.SubElement(lodnSolid_E, ET.QName(nClass.gml, 'Solid'))
            exterior_E = ET.SubElement(solid_E, ET.QName(nClass.gml, 'exterior'))
            compositeSurface_E = ET.SubElement(exterior_E, ET.QName(nClass.gml, 'CompositeSurface'))
            
            if building.terrainIntersections != None:
                self._add_terrainIntersection_to_xml_building(building_E, nClass, building, 2)


            for surface in list(building.roofs.values()) + list(building.walls.values()) + list(building.closure.values())+ list(building.grounds.values()):
                href_id = f"#{surface.polygon_id}"
                ET.SubElement(compositeSurface_E, ET.QName(nClass.gml, 'surfaceMember'), attrib={ET.QName(nClass.xlink, 'href'): href_id})

                boundedBy_E = ET.SubElement(building_E, ET.QName(nClass.bldg, 'boundedBy'))
                wallRoofGround_E = ET.SubElement(boundedBy_E, ET.QName(nClass.bldg, surface.surface_type), attrib={ET.QName(nClass.gml, 'id'): surface.surface_id})
                # ET.SubElement(wallRoofGround_E, "creationDate").text = need to store data
                lodnMultisurface_E = ET.SubElement(wallRoofGround_E, ET.QName(nClass.bldg, 'lod2MultiSurface'))
                multiSurface_E = ET.SubElement(lodnMultisurface_E, ET.QName(nClass.gml, 'MultiSurface'))
                surfaceMember_E = ET.SubElement(multiSurface_E, ET.QName(nClass.gml, 'surfaceMember'))

                polygon_E = ET.SubElement(surfaceMember_E, ET.QName(nClass.gml, 'Polygon'), attrib={ET.QName(nClass.gml, 'id'): surface.polygon_id})
                exterior_E = ET.SubElement(polygon_E, ET.QName(nClass.gml, 'exterior'))

                linearRing_E = ET.SubElement(exterior_E, ET.QName(nClass.gml, 'LinearRing'))
                posList_E = ET.SubElement(linearRing_E, ET.QName(nClass.gml, 'posList'), attrib={"srsDimension": "3"})
                posList_E.text = ' '.join(map(str, surface.gml_surface))
                self._update_min_max(surface)
                
        elif building.lod == "1":
            lodnSolid_E = ET.SubElement(building_E, ET.QName(nClass.bldg, 'lod1Solid'))
            solid_E = ET.SubElement(lodnSolid_E, ET.QName(nClass.gml, "Solid"))
            exterior_E = ET.SubElement(solid_E, ET.QName(nClass.gml, "exterior"))
            compositeSurface_E = ET.SubElement(exterior_E, ET.QName(nClass.gml, "CompositeSurface"))

            if building.terrainIntersections != None:
                self._add_terrainIntersection_to_xml_building(building_E, nClass, building, 1)
            

            for surface in list(building.roofs.values()) + list(building.walls.values()) + list(building.closure.values()) + list(building.grounds.values()):
                surfaceMember_E = ET.SubElement(compositeSurface_E, ET.QName(nClass.gml, "surfaceMember"))
                polygon_E = ET.SubElement(surfaceMember_E, ET.QName(nClass.gml, "Polygon"))
                exterior_E2 = ET.SubElement(polygon_E, ET.QName(nClass.gml, "exterior"))
                linearRing_E = ET.SubElement(exterior_E2, ET.QName(nClass.gml, 'LinearRing'))

                posList_E = ET.SubElement(linearRing_E, ET.QName(nClass.gml, 'posList'), attrib={"srsDimension": "3"})
                posList_E.text = ' '.join(map(str, surface.gml_surface))
                self._update_min_max(surface)

        elif building.lod == "0":
            if len(building.roofs) > 0:
                lodnSolid_E = ET.SubElement(building_E, ET.QName(nClass.bldg, 'lod0Footprint'))
                multiSurface_E = ET.SubElement(lodnSolid_E, ET.QName(nClass.gml, 'MultiSurface'))
                surfaceMember_E = ET.SubElement(multiSurface_E, ET.QName(nClass.gml, "surfaceMember"))
                polygon_E = ET.SubElement(surfaceMember_E, ET.QName(nClass.gml, "Polygon"))
                exterior_E = ET.SubElement(polygon_E, ET.QName(nClass.gml, "exterior"))
                linearRing_E = ET.SubElement(exterior_E, ET.QName(nClass.gml, 'LinearRing'))
                
                posList_E = ET.SubElement(linearRing_E, ET.QName(nClass.gml, 'posList'), attrib={"srsDimension": "3"})
                posList_E.text = ' '.join(map(str, list(building.roofs.values())[0].gml_surface))
                self._update_min_max(surface)

            if len(building.grounds) > 0:
                lodnSolid_E = ET.SubElement(building_E, ET.QName(nClass.bldg, 'lod0RoofEdge'))
                multiSurface_E = ET.SubElement(lodnSolid_E, ET.QName(nClass.gml, 'MultiSurface'))
                surfaceMember_E = ET.SubElement(multiSurface_E, ET.QName(nClass.gml, "surfaceMember"))
                polygon_E = ET.SubElement(surfaceMember_E, ET.QName(nClass.gml, "Polygon"))
                exterior_E = ET.SubElement(polygon_E, ET.QName(nClass.gml, "exterior"))
                linearRing_E = ET.SubElement(exterior_E, ET.QName(nClass.gml, 'LinearRing'))
                
                posList_E = ET.SubElement(linearRing_E, ET.QName(nClass.gml, 'posList'), attrib={"srsDimension": "3"})
                posList_E.text = ' '.join(map(str, list(building.roofs.values())[0].gml_surface))
                self._update_min_max(surface)
        
        return building_E
    

    def _update_min_max(self, surface: object):
        """updates the min and max values for the dataset based on the new surface

        Parameters
        ----------
        surface : object
            SurfaceGML object
        """
        for point in surface.gml_surface_2array:
            for i ,coordinate in enumerate(point):
                if coordinate < self._minimum[i]:
                    self._minimum[i] = coordinate
                elif coordinate > self._maximum[i]:
                    self._maximum[i] = coordinate
    
    def _add_terrainIntersection_to_xml_building(self, parent_E: ET.Element, nClass: xmlClasses.CGML0, building: Building, lod: int) -> None:
        """adds terrainIntersection to an xml element

        Parameters
        ----------
        parent_E : ET.Element
            direct parent element (either cityObjectMember or consistsOfBuildingPart)
        nClass : xmlClasses.CGML0
            namespace class
        building : Building
            Building object
        lod : int
            Level of Detail
        """

        lodNTI_E = ET.SubElement(parent_E, ET.QName(nClass.bldg, f"lod{lod}TerrainIntersection"))
        multiCurve_E = ET.SubElement(lodNTI_E, ET.QName(nClass.gml, "MultiCurve"))
        for curve in building.terrainIntersections:
            curveMember_E = ET.SubElement(multiCurve_E, ET.QName(nClass.gml, "curveMember"))
            lineString_E = ET.SubElement(curveMember_E, ET.QName(nClass.gml, "LineString"))
            posList_E = ET.SubElement(lineString_E, ET.QName(nClass.gml, 'posList'), attrib={"srsDimension": "3"})
            posList_E.text = ' '.join(map(str, curve))

    
    def _add_address_to_xml_building(self, parent_E: ET.Element, nClass: xmlClasses.CGML0, building: Building) -> None:
        """_summary_

        Parameters
        ----------
        parent_E : ET.Element
            direct parent element (either cityObjectMember or consistsOfBuildingPart)
        nClass : xmlClasses.CGML0
            namespace class
        building : Building
            Building Object
        """

        if building.address != None:
            bldgAddress_E = ET.SubElement(parent_E, ET.QName(nClass.bldg, 'address'))
            address_E = ET.SubElement(bldgAddress_E, "Address")
            if building.address.gml_id != None:
                address_E.attrib['{http://www.opengis.net/gml}id'] = building.address.gml_id
            xalAddress_E = ET.SubElement(address_E, "xalAddress")
            addressDetails_E = ET.SubElement(xalAddress_E, ET.QName(nClass.xal, "AddressDetails"))
            country_E = ET.SubElement(addressDetails_E, ET.QName(nClass.xal, "Country"))
            
            if building.address.countryName != None:
                ET.SubElement(country_E, ET.QName(nClass.xal, "CountryName")).text = building.address.countryName

            locality_E = ET.SubElement(country_E, ET.QName(nClass.xal, "Locality"), attrib={"Type": building.address.locality_type})
            
            if building.address.localityName != None:
                ET.SubElement(locality_E, ET.QName(nClass.xal, "LocalityName")).text = building.address.localityName

            if building.address.thoroughfare_type != None or building.address.thoroughfareName != None or building.address.thoroughfareNumber != None:
                thoroughfare_E = ET.SubElement(locality_E, ET.QName(nClass.xal, "Thoroughfare"))

                if building.address.thoroughfare_type != None:
                    thoroughfare_E.attrib["Type"] = building.address.thoroughfare_type

                if building.address.thoroughfareNumber != None:
                    ET.SubElement(thoroughfare_E, ET.QName(nClass.xal, "ThoroughfareNumber")).text = building.address.thoroughfareNumber
                
                if building.address.thoroughfareName != None:
                    ET.SubElement(thoroughfare_E, ET.QName(nClass.xal, "ThoroughfareName")).text = building.address.thoroughfareName

            if building.address.postalCodeNumber != None:
                postalCode_E = ET.SubElement(locality_E, ET.QName(nClass.xal, "PostalCode"))
                ET.SubElement(postalCode_E, ET.QName(nClass.xal, "PostalCodeNumber")).text = building.address.postalCodeNumber



def _create_buffered_polygon(coordinates: np.ndarray, buffer: float = 0.15) -> slyGeom.Polygon:
    """creates a buffered shapely polygon"""
    poly = slyGeom.Polygon(coordinates)
    return poly.buffer(buffer)

