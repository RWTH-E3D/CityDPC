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
    parser = ET.XMLParser(remove_blank_text=True)
    tree = ET.parse(filepath, parser)
    root = tree.getroot()
    nsmap = root.nsmap

    if None in nsmap.keys():
        nsmap["core"] = nsmap[None]

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

    building._calc_roof_volume()

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
    """

    # check if building is LoD0
    lod0FootPrint_E = element.find("bldg:lod0FootPrint", nsmap)
    lod0RoofEdge_E = element.find("bldg:lod0RoofEdge", nsmap)
    if lod0FootPrint_E is not None or lod0RoofEdge_E is not None:
        if lod0FootPrint_E is not None:
            geomKey = building.add_geoemtry(
                GeometryGML("MultiSurface", building.gml_id, 0)
            )
            poly_E = lod0FootPrint_E.findall(".//gml:Polygon", nsmap)
            poly_id = _get_attrib_of_xml_element(
                poly_E, nsmap, ".", "{http://www.opengis.net/gml}id"
            )
            coordinates = _get_polygon_coordinates_from_element(poly_E, nsmap)
            ground_id = poly_id if poly_id else "pyStadt_poly_0"
            newSurface = SurfaceGML(coordinates, ground_id, "GroundSurface", None)
            if newSurface.isSurface:
                geom = building.get_geometry(geomKey)
                pSolidId = geom.create_pseudoSolid("pyStadt_0")
                geom.pseudoSolids[pSolidId].create_pseudoShell("pyStadt_0")
                building.add_surface_with_depthInfo(newSurface, geomKey, [0, 0])
            else:
                building.remove_geometry(geomKey)
                _warn_invalid_surface(building, ground_id)

        if lod0RoofEdge_E is not None:
            geomKey = building.add_geoemtry(
                GeometryGML("MultiSurface", building.gml_id, 0)
            )
            poly_E = lod0RoofEdge_E.findall(".//gml:Polygon", nsmap)
            poly_id = _get_attrib_of_xml_element(
                poly_E, nsmap, ".", "{http://www.opengis.net/gml}id"
            )
            coordinates = _get_polygon_coordinates_from_element(poly_E, nsmap)
            roof_id = poly_id if poly_id else "pyStadt_poly_0"
            newSurface = SurfaceGML(coordinates, roof_id, "RoofSurface", None)
            if newSurface.isSurface:
                geom = building.get_geometry(geomKey)
                pSolidId = geom.create_pseudoSolid("pyStadt_0")
                geom.pseudoSolids[pSolidId].create_pseudoShell("pyStadt_0")
                building.add_surface_with_depthInfo(newSurface, geomKey, [0, 0])
            else:
                building.remove_geometry(geomKey)
                _warn_invalid_surface(building, roof_id)

        return

    # check if building is LoD1
    lod1Solid_E = element.find("bldg:lod1Solid", nsmap)
    if lod1Solid_E is not None:
        # get all polygons and extract their coordinates
        geomKey = building.add_geoemtry(GeometryGML("Solid", building.gml_id, 1))
        geom = building.get_geometry(geomKey)
        pSolidId = geom.create_pseudoSolid("pyStadt_0")
        geom.pseudoSolids[pSolidId].create_pseudoShell("pyStadt_0")

        building.lod = "1"
        poly_Es = lod1Solid_E.findall(".//gml:Polygon", nsmap)
        all_poylgons = {}
        for i, poly_E in enumerate(poly_Es):
            poly_id = _get_attrib_of_xml_element(
                poly_E, nsmap, ".", "{http://www.opengis.net/gml}id"
            )
            coordinates = _get_polygon_coordinates_from_element(poly_E, nsmap)
            all_poylgons[poly_id if poly_id else f"pyStadt_poly_{i}"] = coordinates

        # search for polygon with lowest and highest average height
        # lowest average height is ground surface
        # highest average height is roof surface
        # all other ar wall surfaces
        ground_id = None
        ground_average_height = None
        roof_id = None
        roof_average_height = None

        for poly_id, polygon in all_poylgons.items():
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
        newSurface = SurfaceGML(all_poylgons[roof_id], roof_id, "RoofSurface", None)
        if newSurface.isSurface:
            building.add_surface_with_depthInfo(newSurface, geomKey, [0, 0])
        else:
            _warn_invalid_surface(building, roof_id)
        del all_poylgons[roof_id]
        newSurface = SurfaceGML(
            all_poylgons[ground_id], ground_id, "GroundSurface", None
        )
        if newSurface.isSurface:
            building.add_surface_with_depthInfo(newSurface, geomKey, [0, 0])
        else:
            _warn_invalid_surface(building, ground_id)
        del all_poylgons[ground_id]

        for wall_id, coordinates in all_poylgons.items():
            newSurface = SurfaceGML(coordinates, wall_id, "LoD1_wall", None)
            if newSurface.isSurface:
                building.add_surface_with_depthInfo(newSurface, geomKey, [0, 0])
            else:
                _warn_invalid_surface(building, wall_id)

        return

    # everything greater than LoD1
    solid_E = element.find("bldg:lod2Solid", nsmap)
    if solid_E is not None:
        geomKey = building.add_geoemtry(GeometryGML("Solid", building.gml_id, 2))
        listOfSurfaceMembers = []
        for sM in solid_E.findall(".//gml:surfaceMember", nsmap):
            listOfSurfaceMembers.append(sM.attrib["{http://www.w3.org/1999/xlink}href"])
        # do something with this list of solid memebers
    else:
        geomKey = building.add_geoemtry(GeometryGML("MultiSurface", building.gml_id, 2))

    geom = building.get_geometry(geomKey)
    pSolidId = geom.create_pseudoSolid("pyStadt_0")
    geom.pseudoSolids[pSolidId].create_pseudoShell("pyStadt_0")

    _add_surface_from_element(
        building,
        element,
        nsmap,
        "bldg:boundedBy/bldg:WallSurface",
        geomKey,
    )
    _add_surface_from_element(
        building,
        element,
        nsmap,
        "bldg:boundedBy/bldg:RoofSurface",
        geomKey,
    )
    _add_surface_from_element(
        building,
        element,
        nsmap,
        "bldg:boundedBy/bldg:GroundSurface",
        geomKey,
    )
    _add_surface_from_element(
        building,
        element,
        nsmap,
        "bldg:boundedBy/bldg:ClosureSurface",
        geomKey,
    )

    building.lod = 2
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


def _add_surface_from_element(
    building: AbstractBuilding,
    element: ET.Element,
    nsmap: dict,
    target_str: str,
    geomKey: str,
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
    geomKey : str
        geometry key to add surface to
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
            building.add_surface_with_depthInfo(newSurface, geomKey, [0, 0])
        else:
            _warn_invalid_surface(building, used_id)


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
            f"Surface {surfaceID} of Building {building} is not a "
            + "valid surface"
        )
