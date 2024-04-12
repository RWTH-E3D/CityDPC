from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyStadt.dataset import Dataset
    from pyStadt.core.obejcts.address import CoreAddress
    from pyStadt.core.obejcts.abstractBuilding import AbstractBuilding


import lxml.etree as ET
import numpy as np
import matplotlib.path as mplP

from pyStadt.logger import logger
from pyStadt.tools.cityATB import _border_check, check_building_for_border_and_address
from pyStadt.core.obejcts.building import Building
from pyStadt.core.obejcts.buildingPart import BuildingPart
from pyStadt.core.obejcts.surfacegml import SurfaceGML
from pyStadt.core.obejcts.fileUtil import CityFile
from pyStadt.core.obejcts.geometry import GeometryGML


def load_buildings_from_xml_file(
    dataset: Dataset,
    filepath: str,
    borderCoordinates: list = None,
    addressRestriciton: dict = None,
    ignoreRefSystem: bool = False,
    ignoreExistingTransform: bool = False,
):
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
    ignoreRefSystem : bool, optional
        flag to ignore comparission between reference system name in new file and
        dataset, by default False
    ignoreExistingTransform : bool, optional
        flag to ignore comparission between transform object in new file and dataset,
        by default False
    """
    logger.info(f"loading buildings from CityGML file {filepath}")
    supportedCityGMLversions = ["1.0", "2.0", "3.0"]
    parser = ET.XMLParser(remove_blank_text=True)
    tree = ET.parse(filepath, parser)
    root = tree.getroot()
    nsmap = root.nsmap

    if "core" not in nsmap.keys() and None in nsmap.keys():
        nsmap["core"] = nsmap[None]

    building_ids = []

    # get CityGML version
    cityGMLversion = nsmap["core"].rsplit("/", 1)[-1]
    if cityGMLversion not in supportedCityGMLversions:
        raise ValueError(f"CityGML version {cityGMLversion} not supported")

    # checking for ADEs
    ades = []
    if "energy" in nsmap:
        if nsmap["energy"] == "http://www.sig3d.org/citygml/2.0/energy/1.0":
            ades.append("energyADE")

    # find gml envelope and check for compatability
    envelope_E = root.find("gml:boundedBy/gml:Envelope", nsmap)
    if envelope_E is not None:
        fileSRSName = envelope_E.attrib["srsName"]
        lowerCorner = envelope_E.find("gml:lowerCorner", nsmap).text.split(" ")
        upperCorner = envelope_E.find("gml:upperCorner", nsmap).text.split(" ")
        if dataset.srsName is None:
            dataset.srsName = fileSRSName
        elif dataset.srsName == fileSRSName:
            pass
        elif ignoreRefSystem:
            logger.info(
                f"ReferenceSystem missmatch ({dataset.srsName} - {fileSRSName}), but "
                + "ignoring."
            )
        else:
            logger.error(
                f"Unable to load file! Given srsName ({fileSRSName}) does not match "
                + f"Dataset srsName ({dataset.srsName})"
            )
        if dataset.transform != {} and dataset.transform != {
            "scale": [1, 1, 1],
            "translate": [0, 0, 0],
        }:
            if not ignoreExistingTransform:
                logger.error(
                    "Trying to add file with differenet transform object than "
                    + "dataset. Either transform or forceIgnore the transformation"
                )
    elif ignoreRefSystem:
        logger.info("No gml:Envelope found, but ignoring.")
    else:
        logger.error(
            "Unable to load file! Can't find gml:Envelope for srsName defenition"
        )
        return

    # creating border for coordinate restriction
    if borderCoordinates is not None:
        if len(borderCoordinates) > 2:
            border = mplP.Path(np.array(borderCoordinates))
            x1 = float(lowerCorner[0])
            y1 = float(lowerCorner[1])
            x2 = float(upperCorner[0])
            y2 = float(upperCorner[1])
            fileEnvelopeCoor = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
            if not _border_check(border, borderCoordinates, fileEnvelopeCoor):
                # file envelope is outside of the border coordinates
                return
        elif len(borderCoordinates) < 3:
            logger.error(
                f"Only given {len(borderCoordinates)} borderCoordinates, can't continue"
            )
            return
    else:
        border = None

    # find all buildings within file
    cityObjectMembers_in_file = root.findall("core:cityObjectMember", nsmap)
    for cityObjectMember_E in cityObjectMembers_in_file:
        buildings_in_com = cityObjectMember_E.findall("bldg:Building", nsmap)

        for building_E in buildings_in_com:
            building_id = building_E.attrib["{http://www.opengis.net/gml}id"]
            new_building = Building(building_id)
            _load_building_information_from_xml(
                building_E, nsmap, new_building, cityGMLversion
            )

            bps_in_bldg = building_E.findall(
                "bldg:consistsOfBuildingPart/bldg:BuildingPart", nsmap
            )
            for bp_E in bps_in_bldg:
                bp_id = bp_E.attrib["{http://www.opengis.net/gml}id"]
                new_building_part = BuildingPart(bp_id, building_id)
                _load_building_information_from_xml(bp_E, nsmap, new_building_part)
                new_building.building_parts.append(new_building_part)

            if building_id in dataset.buildings.keys():
                logger.warning(
                    f"Doubling of building id {building_id} "
                    + "Only first mention will be considered"
                )
                continue

            if not check_building_for_border_and_address(
                new_building, borderCoordinates, addressRestriciton, border
            ):
                continue

            dataset.buildings[building_id] = new_building
            building_ids.append(building_id)
        else:
            dataset.otherCityObjectMembers.append(cityObjectMember_E)

    # find gmlName
    gmlName = None
    gmlName_E = root.find("gml:name", nsmap)
    if gmlName_E is not None:
        gmlName = gmlName_E.text

    notLoadedCityObjectMembers = len(cityObjectMembers_in_file) - len(building_ids)

    # store file related information
    newCFile = CityFile(
        filepath,
        f"CityGMLv{cityGMLversion}",
        building_ids,
        notLoadedCityObjectMembers,
        ades,
        srsName=fileSRSName,
        gmlName=gmlName,
    )
    if lowerCorner:
        newCFile.lowerCorner = (float(lowerCorner[0]), float(lowerCorner[1]))
    if upperCorner:
        newCFile.upperCorner = (float(upperCorner[0]), float(upperCorner[1]))
    dataset._files.append(newCFile)
    if dataset.transform == {}:
        dataset.transform = {"scale": [1, 1, 1], "translate": [0, 0, 0]}
    logger.info(f"finished loading buildings from CityGML file {filepath}")


def _load_address_info_from_xml(
    address: CoreAddress, addressElement: ET.Element, nsmap: dict
) -> None:
    """loads address info from an <core:Address> element and adds it to the
    address object

    Parameters
    ----------
    address : CoreAddress
        CoreAddress object to add data to
    addressElement : ET.Element
        <core:Address> lxml.etree element
    nsmap : dict
        namespace map of the root xml/gml file in form of a dicitionary
    """
    if "xal" in nsmap.keys():
        xal = "xal"
    elif "xAL" in nsmap.keys():
        xal = "xAL"
    else:
        logger.error("Namespace xal/xAL issue")

    if "{http://www.opengis.net/gml}id" in addressElement.attrib.keys():
        address.gml_id = addressElement.attrib["{http://www.opengis.net/gml}id"]

    address.countryName = _get_text_of_xml_element(
        addressElement, nsmap, f".//{xal}:CountryName"
    )
    address.locality_type = _get_attrib_of_xml_element(
        addressElement, nsmap, f".//{xal}:Locality", "Type"
    )
    address.localityName = _get_text_of_xml_element(
        addressElement, nsmap, f".//{xal}:LocalityName"
    )
    address.thoroughfare_type = _get_attrib_of_xml_element(
        addressElement, nsmap, f".//{xal}:Thoroughfare", "Type"
    )
    address.thoroughfareNumber = _get_text_of_xml_element(
        addressElement, nsmap, f".//{xal}:ThoroughfareNumber"
    )
    address.thoroughfareName = _get_text_of_xml_element(
        addressElement, nsmap, f".//{xal}:ThoroughfareName"
    )
    address.postalCodeNumber = _get_text_of_xml_element(
        addressElement, nsmap, f".//{xal}:PostalCodeNumber"
    )


def _load_address_info_From_xml_3_0(
    address: CoreAddress, addressElement: ET.Element, nsmap: dict
) -> None:
    """loads address info from an <core:Address> element and adds it to the
    address object for CityGML version 3.0

    Parameters
    ----------
    address : CoreAddress
        address object to add data to
    addressElement : ET.Element
        <core:Address> lxml.etree element
    nsmap : dict
        namespace map of the root xml/gml file in form of a dicitionary
    """

    address.localityName = _get_text_of_xml_element(
        addressElement, nsmap, ".//xAL:Locality/xAL:NameElement"
    )

    address.thoroughfareName = _get_text_of_xml_element(
        addressElement, nsmap, ".//xAL:Thoroughfare/xAL:NameElement"
    )

    address.thoroughfareNumber = _get_text_of_xml_element(
        addressElement, nsmap, ".//xAL:Thoroughfare/xAL:Number"
    )

    address.postalCodeNumber = _get_text_of_xml_element(
        addressElement, nsmap, ".//xAL:PostCode/xAL:Identifier"
    )


def _load_building_information_from_xml(
    buildingElement: ET.Element,
    nsmap: dict,
    building: AbstractBuilding,
    cityGMLversion: str,
):
    """loads building information from xml element

    Parameters
    ----------
    buildingElement : ET.Element
        either <bldg:Building> or <bldg:BuildingPart> lxml.etree element
    nsmap : dict
        namespace map of the root xml/gml file in form of a dicitionary
    building : AbstractBuilding
        either Building or BuildingPart object to add info to
    cityGMLversion : str
        version of the CityGML file
    """
    _get_building_surfaces_from_xml_element(
        building, buildingElement, nsmap, cityGMLversion
    )

    _get_building_attributes_from_xml_element(
        building, buildingElement, nsmap, cityGMLversion
    )

    if cityGMLversion in ["1.0", "2.0"]:
        lodNTI_E = buildingElement.find("bldg:lod2TerrainIntersection", nsmap)
        if lodNTI_E is None:
            lodNTI_E = buildingElement.find("bldg:lod1TerrainIntersection", nsmap)
        if lodNTI_E is not None:
            building.terrainIntersections = []
            curveMember_Es = lodNTI_E.findall(".//gml:curveMember", nsmap)
            for curve_E in curveMember_Es:
                building.terrainIntersections.append(
                    _get_polygon_coordinates_from_element(curve_E, nsmap)
                )

        extRef_E = buildingElement.find("core:externalReference", nsmap)
        if extRef_E is not None:
            building.extRef_infromationsSystem = _get_text_of_xml_element(
                extRef_E, nsmap, "core:informationSystem"
            )
            extObj_E = extRef_E.find("core:externalObject", nsmap)
            if extObj_E is not None:
                building.extRef_objName = _get_text_of_xml_element(
                    extObj_E, nsmap, "core:name"
                )

    building._calc_roof_volume()
    building.create_legacy_surface_dicts()

    address_E = buildingElement.find("bldg:address/core:Address", nsmap)
    if cityGMLversion in ["1.0", "2.0"]:
        if address_E is not None:
            _load_address_info_from_xml(building.address, address_E, nsmap)
    elif cityGMLversion in ["3.0"]:
        if address_E is not None:
            _load_address_info_From_xml_3_0(building.address, address_E, nsmap)


def _get_building_attributes_from_xml_element(
    building: AbstractBuilding,
    buildingElement: ET.Element,
    nsmap: dict,
    cityGMLversion: str,
) -> None:
    """loads building attributes from xml Element

    Parameters
    ----------
    building : AbstractBuilding
        either Building or BuildingPart object to add info to
    element : ET.Element
        either <bldg:Building> or <bldg:BuildingPart> lxml.etree element
    nsmap : dict
        namespace map of the root xml/gml file in form of a dicitionary
    cityGMLversion : str
        version of the CityGML file
    """

    building.usage = _get_text_of_xml_element(buildingElement, nsmap, "bldg:usage")

    building.function = _get_text_of_xml_element(
        buildingElement, nsmap, "bldg:function"
    )
    building.roofType = _get_text_of_xml_element(
        buildingElement, nsmap, "bldg:roofType"
    )
    building.storeysAboveGround = _get_int_of_xml_element(
        buildingElement, nsmap, "bldg:storeysAboveGround"
    )
    building.storeyHeightsAboveGround = _get_float_of_xml_element(
        buildingElement, nsmap, "bldg:storeyHeightsAboveGround"
    )
    building.storeysBelowGround = _get_int_of_xml_element(
        buildingElement, nsmap, "bldg:storeysBelowGround"
    )
    building.storeyHeightsBelowGround = _get_float_of_xml_element(
        buildingElement, nsmap, "bldg:storeyHeightsBelowGround"
    )

    if cityGMLversion in ["1.0", "2.0"]:
        building.creationDate = _get_text_of_xml_element(
            buildingElement, nsmap, "core:creationDate"
        )

        genStrings = buildingElement.findall("gen:stringAttribute", nsmap)
        for i in genStrings:
            key = i.attrib["name"]
            building.genericStrings[key] = _get_text_of_xml_element(
                i, nsmap, "gen:value"
            )

        building.yearOfConstruction = _get_int_of_xml_element(
            buildingElement, nsmap, "bldg:yearOfConstruction"
        )
        building.measuredHeight = _get_float_of_xml_element(
            buildingElement, nsmap, "bldg:measuredHeight"
        )
    elif cityGMLversion in ["3.0"]:
        if height_E := buildingElement.find("con:height", nsmap):
            if height2_E := height_E.find("con:Height", nsmap):
                if (
                    _get_text_of_xml_element(height2_E, nsmap, "con:highReference")
                    == "highestRoofEdge"
                    and _get_text_of_xml_element(
                        height2_E, nsmap, "con:heightReference"
                    )
                    == "lowestRoofEdge"
                ):
                    building.measuredHeight = _get_float_of_xml_element(
                        height2_E, nsmap, "con:value"
                    )

    else:
        logger.error(f"CityGML version {cityGMLversion} not supported")


def _get_building_surfaces_from_xml_element(
    building: AbstractBuilding,
    element: ET.Element,
    nsmap: dict,
    cityGMLversion: str,
) -> None:
    """gathers surfaces from element and categories them

    Parameters
    ----------
    building : AbstractBuilding
        either Building or BuildingPart object to add info to
    element : ET.Element
        either <bldg:Building> or <bldg:BuildingPart> lxml.etree element
    nsmap : dict
       namespace map of the root xml/gml file in form of a dicitionary
    cityGMLversion : str
        version of the CityGML file
    """

    if cityGMLversion in ["1.0", "2.0"]:
        # check if building is LoD0
        lod0FootPrint_E = element.find("bldg:lod0FootPrint", nsmap)
        lod0RoofEdge_E = element.find("bldg:lod0RoofEdge", nsmap)
        if lod0FootPrint_E is not None or lod0RoofEdge_E is not None:
            building.lod = "0"
            if lod0FootPrint_E is not None:
                geometry = GeometryGML("MultiSurface", building.gml_id, 0)
                geomKey = building.add_geometry(geometry)
                poly_E = lod0FootPrint_E.findall(".//gml:Polygon", nsmap)
                poly_id = _get_attrib_of_xml_element(
                    poly_E, nsmap, ".", "{http://www.opengis.net/gml}id"
                )
                coordinates = _get_polygon_coordinates_from_element(poly_E, nsmap)
                ground_id = poly_id if poly_id else "pyStadt_poly_0"
                newSurface = SurfaceGML(coordinates, ground_id, "GroundSurface", None)
                if newSurface.isSurface:
                    geometry.add_surface(newSurface)
                else:
                    building.remove_geometry(geomKey)
                    building._warn_invalid_surface(ground_id)

            if lod0RoofEdge_E is not None:
                geometry = GeometryGML("MultiSurface", building.gml_id, 0)
                geomKey = building.add_geometry(geometry)
                poly_E = lod0RoofEdge_E.findall(".//gml:Polygon", nsmap)
                poly_id = _get_attrib_of_xml_element(
                    poly_E, nsmap, ".", "{http://www.opengis.net/gml}id"
                )
                coordinates = _get_polygon_coordinates_from_element(poly_E, nsmap)
                roof_id = poly_id if poly_id else "pyStadt_poly_0"
                newSurface = SurfaceGML(coordinates, roof_id, "RoofSurface", None)
                if newSurface.isSurface:
                    building.remove_geometry(geomKey)
                    building._warn_invalid_surface(roof_id)

            return

        # check if building is LoD1
        lod1Solid_E = element.find("bldg:lod1Solid", nsmap)
        if lod1Solid_E is not None:
            building.lod = "1"
            # get all polygons and extract their coordinates
            geometry = GeometryGML("Solid", building.gml_id, 1)
            geomKey = building.add_geometry(geometry)

            poly_Es = lod1Solid_E.findall(".//gml:Polygon", nsmap)
            for i, poly_E in enumerate(poly_Es):
                poly_id = _get_attrib_of_xml_element(
                    poly_E, nsmap, ".", "{http://www.opengis.net/gml}id"
                )
                coordinates = _get_polygon_coordinates_from_element(poly_E, nsmap)
                poly_id = poly_id if poly_id else f"pyStadt_poly_{i}"
                newSurface = SurfaceGML(coordinates, poly_id)
                if newSurface.isSurface:
                    geometry.add_surface(newSurface)
                else:
                    building._warn_invalid_surface(poly_id)

        # everything greater than LoD1
        solid_E = element.find("bldg:lod2Solid", nsmap)
        listOfSurfaceMembers = []
        if solid_E is not None:
            geometry = GeometryGML("Solid", building.gml_id, 2)
            geomKey = building.add_geometry(geometry)
            for sM in solid_E.findall(".//gml:surfaceMember", nsmap):
                listOfSurfaceMembers.append(
                    sM.attrib["{http://www.w3.org/1999/xlink}href"]
                )
            # do something with this list of solid memebers
        else:
            geometry = GeometryGML("MultiSurface", building.gml_id, 2)
            geomKey = building.add_geometry(geometry)

        building.lod = "2"

        _add_surface_from_element(
            building,
            element,
            nsmap,
            "bldg:boundedBy/bldg:WallSurface",
            geometry,
        )
        _add_surface_from_element(
            building,
            element,
            nsmap,
            "bldg:boundedBy/bldg:RoofSurface",
            geometry,
        )
        _add_surface_from_element(
            building,
            element,
            nsmap,
            "bldg:boundedBy/bldg:GroundSurface",
            geometry,
        )
        _add_surface_from_element(
            building,
            element,
            nsmap,
            "bldg:boundedBy/bldg:ClosureSurface",
            geometry,
        )

        return

    elif cityGMLversion in ["3.0"]:
        # check if building is LoD0
        lod0MultiSurface = element.find("lod0MultiSurface", nsmap)
        if lod0MultiSurface is not None:
            building.lod = "0"
            geometry = GeometryGML("MultiSurface", building.gml_id, 0)
            geomKey = building.add_geometry(geometry)
            poly_Es = lod0MultiSurface.findall(".//gml:Polygon", nsmap)
            for i, poly_E in enumerate(poly_Es):
                poly_id = _get_attrib_of_xml_element(
                    poly_E, nsmap, ".", "{http://www.opengis.net/gml}id"
                )
                coordinates = _get_polygon_coordinates_from_element(poly_E, nsmap)
                poly_id = poly_id if poly_id else f"pyStadt_poly_{i}"
                newSurface = SurfaceGML(coordinates, poly_id)
                if newSurface.isSurface:
                    geometry.add_surface(newSurface)
                else:
                    building._warn_invalid_surface(poly_id)
            return

        # check if building is LoD1
        lod1Solid_E = element.find("lod1Solid", nsmap)
        if lod1Solid_E is not None:
            building.lod = "1"
            # get all polygons and extract their coordinates
            geometry = GeometryGML("Solid", building.gml_id, 1)
            geomKey = building.add_geometry(geometry)

            poly_Es = lod1Solid_E.findall(".//gml:Polygon", nsmap)
            for i, poly_E in enumerate(poly_Es):
                poly_id = _get_attrib_of_xml_element(
                    poly_E, nsmap, ".", "{http://www.opengis.net/gml}id"
                )
                coordinates = _get_polygon_coordinates_from_element(poly_E, nsmap)
                poly_id = poly_id if poly_id else f"pyStadt_poly_{i}"
                newSurface = SurfaceGML(coordinates, poly_id)
                if newSurface.isSurface:
                    geometry.add_surface(newSurface)
                else:
                    building._warn_invalid_surface(poly_id)
            return

        # everything greater than LoD1
        solid_E = element.find("lod2Solid", nsmap)
        if solid_E is not None:
            geometry = GeometryGML("Solid", building.gml_id, 2)
            geomKey = building.add_geometry(geometry)
            for sM in solid_E.findall(".//gml:surfaceMember", nsmap):
                listOfSurfaceMembers.append(
                    sM.attrib["{http://www.w3.org/1999/xlink}href"]
                )
            # do something with this list of solid memebers
        else:
            geometry = GeometryGML("MultiSurface", building.gml_id, 2)
            geomKey = building.add_geometry(geometry)

        building.lod = "2"

        _add_surface_from_element(
            building,
            element,
            nsmap,
            "boundary/con:WallSurface",
            geometry,
        )
        _add_surface_from_element(
            building,
            element,
            nsmap,
            "boundary/con:RoofSurface",
            geometry,
        )
        _add_surface_from_element(
            building,
            element,
            nsmap,
            "boundary/con:GroundSurface",
            geometry,
        )
        _add_surface_from_element(
            building,
            element,
            nsmap,
            "boundary/con:ClosureSurface",
            geometry,
        )
        return
    else:
        logger.error(f"CityGML version {cityGMLversion} not supported")


def _get_polygon_coordinates_from_element(
    polygon_element: ET.Element, nsmap: dict
) -> np.array:
    """search the element for coordinates

    takes coordinates from both gml:posList and gml:pos elements
    returns an numpy array of the coordinates

    Parameters
    ----------
    polygon_element : ET.Element
        <gml:polygon> lxml.etree element
    nsmap : dict
        namespace map of the root xml/gml file in form of a dicitionary

    Returns
    -------
    np.array
       1D numpy array of coordinates
    """
    polyStr = []
    # searching for list of coordinates
    posList_E = polygon_element.find(".//gml:posList", nsmap)
    if posList_E is not None:
        polyStr = posList_E.text.strip().split(" ")
    else:
        # searching for individual coordinates in polygon
        pos_Es = polygon_element.findall(".//gml:pos", nsmap)
        for pos_E in pos_Es:
            polyStr.extend(pos_E.text.strip().split(" "))
    return np.array([float(x) for x in polyStr])


def _add_surface_from_element(
    building: AbstractBuilding,
    element: ET.Element,
    nsmap: dict,
    target_str: str,
    geometry: GeometryGML,
    id_str: str = "",
) -> None:
    """creates a dictionary from surfaces of lxml element


    Parameters
    ----------
    element : ET.Element
        either <bldg:Building> or <bldg:BuildingPart> lxml.etree element
    nsmap : dict
        namespace map of the root xml/gml file in form of a dicitionary
    target_str : str
        element to take coordinates from e.g. 'bldg:boundedBy/bldg:RoofSurface'
    geometry : GeometryGML
        geometry to add surface to
    id_str : str, optional
        base string for dict index, by default ""
    """
    if not id_str:
        id_str = building.gml_id + "_" + target_str.split(":")[-1]
    for i, surface_E in enumerate(element.findall(target_str, nsmap)):
        id = _get_attrib_of_xml_element(
            surface_E, nsmap, ".", "{http://www.opengis.net/gml}id"
        )
        poly_E = surface_E.find(".//gml:Polygon", nsmap)
        poly_id = _get_attrib_of_xml_element(
            poly_E, nsmap, ".", "{http://www.opengis.net/gml}id"
        )
        coordinates = _get_polygon_coordinates_from_element(poly_E, nsmap)
        used_id = id if id else f"pyStadt_{id_str}_{i}"
        newSurface = SurfaceGML(
            coordinates, used_id, target_str.rsplit(":")[-1], poly_id
        )
        if newSurface.isSurface:
            geometry.add_surface(newSurface)
        else:
            building._warn_invalid_surface(used_id)


def _get_text_of_xml_element(
    element: ET.Element, nsmap: dict, target: str
) -> str | None:
    """gets the text content of a target element

    Parameters
    ----------
    element : ET.Element
        parent lxml.etree element of target element
    nsmap : dict
        namespace map of the root xml/gml file in form of a dicitionary
    target : str
        prefixed target element name

    Returns
    -------
    str | None
        returns either the value as a string or None
    """
    try:
        res_E = element.find(target, nsmap)
    except:
        logger.error(f"Unable to find {target} in {element}")
        return None
    if res_E is not None:
        return res_E.text
    return None


def _get_float_of_xml_element(
    element: ET.Element, nsmap: dict, target: str
) -> float | None:
    """gets the float value of a target element

    Parameters
    ----------
    element : ET.Element
        parent lxml.etree element of target element
    nsmap : dict
        namespace map of the root xml/gml file in form of a dicitionary
    target : str
        prefixed target element name

    Returns
    -------
    float | None
        returns either the value as a float or None
    """
    res = _get_text_of_xml_element(element, nsmap, target)
    if res is not None:
        try:
            return float(res)
        except:
            logger.error(f"Unable to convert {res} to float")
    return None


def _get_int_of_xml_element(
    element: ET.Element, nsmap: dict, target: str
) -> int | None:
    """gets the int value of a target element

    Parameters
    ----------
    element : ET.Element
        parent lxml.etree element of target element
    nsmap : dict
        namespace map of the root xml/gml file in form of a dicitionary
    target : str
        prefixed target element name

    Returns
    -------
    int | None
        returns either the value as a int or None
    """
    res = _get_text_of_xml_element(element, nsmap, target)
    if res is not None:
        try:
            return int(res)
        except:
            logger.error(f"Unable to convert {res} to int")
    return None


def _get_attrib_of_xml_element(
    element: ET.Element, nsmap: dict, target: str, attrib: str
) -> str | None:
    """gets the attribute of a target element

    Parameters
    ----------
    element : ET.Element
        parent lxml.etree element of target element
    nsmap : dict
        namespace map of the root xml/gml file in form of a dicitionary
    target : str
        prefixed target element name
    attrib : str
        attribute name

    Returns
    -------
    str | None
        returns either the attribute value as a string or None
    """
    try:
        res_E = element.find(target, nsmap)
    except:
        logger.error(f"Unable to find {target} in {element}")
        return None
    if res_E is not None:
        if attrib in res_E.attrib.keys():
            return res_E.attrib[attrib]
    return None
