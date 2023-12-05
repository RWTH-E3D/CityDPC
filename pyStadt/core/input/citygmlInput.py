from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyStadt.dataset import Dataset
    from pyStadt.core.obejcts.address import CoreAddress
    from pyStadt.core.obejcts.abstractBuilding import AbstractBuilding


import lxml.etree as ET
import numpy as np
from scipy.spatial import ConvexHull
import matplotlib.path as mplP

from pyStadt.logger import logger
from pyStadt.tools.cityATB import (
    _border_check,
    check_building_for_address,
    check_if_building_in_coordinates,
)
from pyStadt.core.obejcts.building import Building
from pyStadt.core.obejcts.buildingPart import BuildingPart
from pyStadt.core.obejcts.surfacegml import SurfaceGML
from pyStadt.core.obejcts.fileUtil import CityFile


def load_buildings_from_xml_file(
    dataset: Dataset,
    filepath: str,
    borderCoordinates: list = None,
    addressRestriciton: dict = None,
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
    """
    logger.info(f"loading buildings from CityGML file {filepath}")
    parser = ET.XMLParser(remove_blank_text=True)
    tree = ET.parse(filepath, parser)
    root = tree.getroot()
    nsmap = root.nsmap

    building_ids = []

    # get CityGML version
    cityGMLversion = nsmap["core"].rsplit("/", 1)[-1]

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
        else:
            logger.error(
                f"Unable to load file! Given srsName ({fileSRSName}) does not match "
                + f"Dataset srsName ({dataset.srsName})"
            )
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
            _load_building_information_from_xml(building_E, nsmap, new_building)

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

            if border is not None:
                res_coor = check_if_building_in_coordinates(
                    new_building, borderCoordinates, border
                )

            if addressRestriciton is not None:
                res_addr = check_building_for_address(new_building, addressRestriciton)

            if border is None and addressRestriciton is None:
                pass
            elif border is not None and addressRestriciton is None:
                if not res_coor:
                    continue
            elif border is None and addressRestriciton is not None:
                if not res_addr:
                    continue
            else:
                if not (res_coor and res_addr):
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

    notLoadedCityObjectMembers = cityObjectMembers_in_file - len(building_ids)

    # store file related information
    newCFile = CityFile(
        filepath,
        cityGMLversion,
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
    if "{http://www.opengis.net/gml}id" in addressElement.attrib.keys():
        address.gml_id = addressElement.attrib["{http://www.opengis.net/gml}id"]

    address.countryName = _get_text_of_xml_element(
        addressElement, nsmap, ".//xal:CountryName"
    )
    address.locality_type = _get_attrib_of_xml_element(
        addressElement, nsmap, ".//xal:Locality", "Type"
    )
    address.localityName = _get_text_of_xml_element(
        addressElement, nsmap, ".//xal:LocalityName"
    )
    address.thoroughfare_type = _get_attrib_of_xml_element(
        addressElement, nsmap, ".//xal:Thoroughfare", "Type"
    )
    address.thoroughfareNumber = _get_text_of_xml_element(
        addressElement, nsmap, ".//xal:ThoroughfareNumber"
    )
    address.thoroughfareName = _get_text_of_xml_element(
        addressElement, nsmap, ".//xal:ThoroughfareName"
    )
    address.postalCodeNumber = _get_text_of_xml_element(
        addressElement, nsmap, ".//xal:PostalCodeNumber"
    )


def _load_building_information_from_xml(
    buildingElement: ET.Element, nsmap: dict, building: AbstractBuilding
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
    """
    _get_building_surfaces_from_xml_element(building, buildingElement, nsmap)

    _get_building_attributes_from_xml_element(building, buildingElement, nsmap)

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

    if building.roofs != {}:
        building.roof_volume = 0
        for roof_surface in building.roofs.values():
            if np.all(
                roof_surface.gml_surface_2array
                == roof_surface.gml_surface_2array[0, :],
                axis=0,
            )[2]:
                # roof surface is flat -> no volume to calculate
                continue
            minimum_roof_height = np.min(roof_surface.gml_surface_2array, axis=0)[2]
            closing_points = np.array(roof_surface.gml_surface_2array, copy=True)
            closing_points[:, 2] = minimum_roof_height
            closed = np.concatenate([closing_points, roof_surface.gml_surface_2array])
            hull = ConvexHull(closed)
            building.roof_volume += round(hull.volume, 3)

    address_E = buildingElement.find("bldg:address/core:Address", nsmap)
    if address_E is not None:
        _load_address_info_from_xml(building.address, address_E, nsmap)


def _get_building_attributes_from_xml_element(
    building: AbstractBuilding, buildingElement: ET.Element, nsmap: dict
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
    """

    building.creationDate = _get_text_of_xml_element(
        buildingElement, nsmap, "core:creationDate"
    )

    genStrings = buildingElement.findall("gen:stringAttribute", nsmap)
    for i in genStrings:
        key = i.attrib["name"]
        building.genericStrings[key] = _get_text_of_xml_element(i, nsmap, "gen:value")

    building.function = _get_text_of_xml_element(
        buildingElement, nsmap, "bldg:function"
    )
    building.usage = _get_text_of_xml_element(buildingElement, nsmap, "bldg:usage")
    building.yearOfConstruction = _get_text_of_xml_element(
        buildingElement, nsmap, "bldg:yearOfConstruction"
    )
    building.roofType = _get_text_of_xml_element(
        buildingElement, nsmap, "bldg:roofType"
    )
    building.measuredHeight = _get_text_of_xml_element(
        buildingElement, nsmap, "bldg:measuredHeight"
    )
    building.storeysAboveGround = _get_text_of_xml_element(
        buildingElement, nsmap, "bldg:storeysAboveGround"
    )
    building.storeysBelowGround = _get_text_of_xml_element(
        buildingElement, nsmap, "bldg:storeysBelowGround"
    )


def _get_building_surfaces_from_xml_element(
    building: AbstractBuilding, element: ET.Element, nsmap: dict
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
       namespace map of the root xml/gml file in form of a dicitionary

    Returns
    -------
    tuple[dict, dict, dict, dict, str]
        dictionaries : are in the order walls, roofs, grounds, closure
            the dicitionaries have a key value pairing of
            gml:id : coordinates (3 dimensional)
        str: str of found building LoD

        namespace map of the root xml/gml file in form of a dicitionary

    Returns
    -------
    tuple[dict, dict, dict, dict, str]
        dictionaries : are in the order walls, roofs, grounds, closure
            the dicitionaries have a key value pairing of
            gml:id : coordinates (3 dimensional)
        str: str of found building LoD

    """

    lod = None

    # check if building is LoD0
    lod0FootPrint_E = element.find("bldg:lod0FootPrint", nsmap)
    lod0RoofEdge_E = element.find("bldg:lod0RoofEdge", nsmap)
    if lod0FootPrint_E is not None or lod0RoofEdge_E is not None:
        grounds = {}
        if lod0FootPrint_E is not None:
            poly_E = lod0FootPrint_E.findall(".//gml:Polygon", nsmap)
            if "{http://www.opengis.net/gml}id" in lod0FootPrint_E.attrib.keys():
                ground_id = lod0FootPrint_E.attrib["{http://www.opengis.net/gml}id"]
            else:
                ground_id = "poly_0"
            coordinates = _get_polygon_coordinates_from_element(poly_E, nsmap)
            newSurface = SurfaceGML(coordinates, ground_id, "LoD0_footPrint", None)
            if newSurface.isSurface:
                grounds = {ground_id: newSurface}
            else:
                _warn_invalid_surface(building, ground_id)

        roofs = {}
        if lod0RoofEdge_E is not None:
            poly_E = lod0RoofEdge_E.findall(".//gml:Polygon", nsmap)
            if "{http://www.opengis.net/gml}id" in lod0RoofEdge_E.attrib.keys():
                roof_id = lod0RoofEdge_E.attrib["{http://www.opengis.net/gml}id"]
            else:
                roof_id = "poly_0"
            coordinates = _get_polygon_coordinates_from_element(poly_E, nsmap)
            newSurface = SurfaceGML(coordinates, roof_id, "LoD0_roofEdge", None)
            if newSurface.isSurface:
                roofs = {roof_id: newSurface}
            else:
                _warn_invalid_surface(building, roof_id)

        building.walls = {}
        building.roofs = roofs
        building.grounds = grounds
        building.closure = {}
        building.lod = "0"
        return

    # check if building is LoD1
    lod1Solid_E = element.find("bldg:lod1Solid", nsmap)
    if lod1Solid_E is not None:
        # get all polygons and extract their coordinates
        poly_Es = lod1Solid_E.findall(".//gml:Polygon", nsmap)
        all_poylgons = {}
        for i, poly_E in enumerate(poly_Es):
            if "{http://www.opengis.net/gml}id" in poly_E.attrib.keys():
                poly_id = poly_E.attrib["{http://www.opengis.net/gml}id"]
            else:
                poly_id = f"poly_{i}"
            coordinates = _get_polygon_coordinates_from_element(poly_E, nsmap)
            all_poylgons[poly_id] = coordinates

        # search for polygon with lowest and highest average height
        # lowest average height is ground surface
        # highest average height is roof surface
        # all other ar wall surfaces
        ground_id = None
        ground_average_height = None
        roof_id = None
        roof_average_height = None

        for poly_id, polygon in all_poylgons.itmes():
            polygon_average_height = sum([i[2] for i in polygon]) / len(polygon)

            if ground_id is None:
                ground_id = poly_id
                ground_average_height = polygon_average_height
            elif polygon_average_height < ground_average_height:
                ground_id = poly_id
                ground_average_height = polygon_average_height

            if roof_id is None:
                roof_id = poly_id
                roof_average_height = polygon_average_height
            elif polygon_average_height > roof_average_height:
                roof_id = poly_id
                roof_average_height = polygon_average_height
        newSurface = SurfaceGML(all_poylgons[roof_id], roof_id, "LoD1_roof", None)
        if newSurface.isSurface:
            roofs = {roof_id: newSurface}
        else:
            _warn_invalid_surface(building, roof_id)
        del all_poylgons[roof_id]
        newSurface = SurfaceGML(all_poylgons[ground_id], ground_id, "LoD1_ground", None)
        if newSurface.isSurface:
            grounds = {ground_id: newSurface}
        else:
            _warn_invalid_surface(building, ground_id)
        del all_poylgons[ground_id]

        walls = {}
        for wall_id, coordinates in all_poylgons.items():
            newSurface = SurfaceGML(coordinates, wall_id, "LoD1_wall", None)
            if newSurface.isSurface:
                walls[wall_id] = newSurface
            else:
                _warn_invalid_surface(building, wall_id)

        building.walls = walls
        building.roofs = roofs
        building.grounds = grounds
        building.closure = {}
        building.lod = "1"
        return

    # everything greater than LoD1
    walls = _get_surface_dict_from_element(
        building, element, nsmap, "bldg:boundedBy/bldg:WallSurface"
    )
    roofs = _get_surface_dict_from_element(
        building, element, nsmap, "bldg:boundedBy/bldg:RoofSurface"
    )
    grounds = _get_surface_dict_from_element(
        building, element, nsmap, "bldg:boundedBy/bldg:GroundSurface"
    )
    closure = _get_surface_dict_from_element(
        building, element, nsmap, "bldg:boundedBy/bldg:ClosureSurface"
    )

    # searching for LoD
    for elem in element.iter():
        if elem.tag.split("}")[1].startswith("lod"):
            lod = elem.tag.split("}")[1][3]

    building.walls = walls
    building.roofs = roofs
    building.grounds = grounds
    building.closure = closure
    building.lod = lod
    return


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


def _get_surface_dict_from_element(
    building: AbstractBuilding,
    element: ET.Element,
    nsmap: dict,
    target_str: str,
    id_str: str = "",
) -> dict:
    """creates a dictionary from surfaces of lxml element


    Parameters
    ----------
    element : ET.Element
        either <bldg:Building> or <bldg:BuildingPart> lxml.etree element
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
        id_str = (
            building.gml_id
            + "_"
            + target_str.split(":")[-1]
        )
    for i, surface_E in enumerate(element.findall(target_str, nsmap)):
        if "{http://www.opengis.net/gml}id" in surface_E.attrib:
            id = surface_E.attrib["{http://www.opengis.net/gml}id"]
        else:
            id = None
        poly_E = surface_E.find(".//gml:Polygon", nsmap)
        if "{http://www.opengis.net/gml}id" in poly_E.attrib:
            poly_id = poly_E.attrib["{http://www.opengis.net/gml}id"]
        else:
            poly_id = None
        coordinates = _get_polygon_coordinates_from_element(poly_E, nsmap)
        used_id = id if id else f"{id_str}_{i}"
        newSurface = SurfaceGML(
            coordinates, used_id, target_str.rsplit(":")[-1], poly_id
        )
        if newSurface.isSurface:
            result[used_id] = newSurface
        else:
            _warn_invalid_surface(building, used_id)
    return result


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
    res_E = element.find(target, nsmap)
    if res_E is not None:
        return res_E.text
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
    res_E = element.find(target, nsmap)
    if res_E is not None:
        if attrib in res_E.attrib.keys():
            return res_E.attrib[attrib]
    return None


def _warn_invalid_surface(building: AbstractBuilding, surfaceID: str) -> None:
    """logs warning about invalid surface

    Parameters
    ----------
    building : AbstractBuilding
        either Building or BuildingPart parent object of Surface
    surfaceID : str
        gml:id of incorrect Surface
    """
    if building.is_building_part:
        logger.warning(
            f"Surface {surfaceID} of BuildingPart {building.gml_id} of Building "
            + f"{building.parent_gml_id} is not a valid surface"
        )
    else:
        logger.warning(
            f"Surface {surfaceID} of Building {building.parent_gml_id} is not a "
            + "valid surface"
        )
