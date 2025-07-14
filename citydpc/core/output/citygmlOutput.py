from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from citydpc.dataset import Dataset
    from citydpc.core.object.abstractBuilding import AbstractBuilding
    from citydpc.core.object.surfacegml import SurfaceGML
    from citydpc.core.object.geometry import GeometryGML
    from citydpc.core.object.address import CoreAddress


import lxml.etree as ET

import citydpc.util.citygmlClasses as citygmlClasses
from citydpc.util.envelope import update_dataset_min_max_from_surface
from citydpc.logger import logger
import uuid


def write_citygml_file(dataset: Dataset, filename: str, version: str = "2.0") -> None:
    """writes Dataset to citygml file

    Parameters
    ----------
    dataset : Dataset
        dataset that should be saved
    filename : str
        new filename (including path if wanted)
    version : str
        CityGML version - either "1.0", "2.0" or "3.0"
    """

    if dataset.srsName is None:
        logger.error("Dataset has no srsName")
        return

    if version == "1.0":
        nClass = citygmlClasses.CGML1
    elif version == "2.0":
        nClass = citygmlClasses.CGML2
    elif version == "3.0":
        nClass = citygmlClasses.CGML3
    else:
        raise ValueError(f"CityGML version {version} is not supported")

    # creating new namespacemap
    newNSmap = {
        key: value
        for key, value in vars(nClass).items()
        if not key.startswith("_")
    }
    # creating new root element
    nroot_E = ET.Element(ET.QName(nClass.core, "CityModel"), nsmap=newNSmap)

    # creating name element
    name_E = ET.SubElement(
        nroot_E,
        ET.QName(nClass.gml, "name"),
    )
    name_E.text = "created using the e3D citydpc"

    # creating gml enevelope
    bound_E = ET.SubElement(nroot_E, ET.QName(nClass.gml, "boundedBy"))
    envelope = ET.SubElement(
        bound_E, ET.QName(nClass.gml, "Envelope"), srsName=dataset.srsName
    )
    lcorner = ET.SubElement(
        envelope, ET.QName(nClass.gml, "lowerCorner"), srsDimension="3"
    )
    ucorner = ET.SubElement(
        envelope, ET.QName(nClass.gml, "upperCorner"), srsDimension="3"
    )

    for building in dataset.get_building_list():
        cityObjectMember_E = ET.SubElement(
            nroot_E, ET.QName(nClass.core, "cityObjectMember")
        )
        building_E = _add_building_to_cityModel_xml(
            dataset, building, cityObjectMember_E, nClass
        )

        for buildingPart in building.building_parts:
            cOBP_E = ET.SubElement(
                building_E,
                ET.QName(nClass.bldg, "consistsOfBuildingPart"),
            )

            bp_E = _add_building_to_cityModel_xml(dataset, buildingPart, cOBP_E, nClass)
            for address in buildingPart.addressCollection.get_adresses():
                _add_address_to_xml_building(address, bp_E, nClass)

        for address in building.addressCollection.get_adresses():
            _add_address_to_xml_building(address, building_E, nClass)

    lcorner.text = " ".join(map(str, dataset._minimum))
    ucorner.text = " ".join(map(str, dataset._maximum))

    tree = ET.ElementTree(nroot_E)
    tree.write(
        filename,
        pretty_print=True,
        xml_declaration=True,
        encoding="utf-8",
        standalone="yes",
        method="xml",
    )


def _add_building_to_cityModel_xml(
    dataset: Dataset,
    building: AbstractBuilding,
    parent_E: ET.Element,
    nClass: citygmlClasses.CGML0,
    version: str = "2.0",
) -> ET.Element:
    """adds a building or buildingPart to a cityModel

    Parameters
    ----------
    dataset : Dataset
        Dataset for updating min max coordinates
    building : AbstractBuilding
        either Building or BuildingPart object
    parent_E : ET.Element
        direct parent element (either cityObjectMember or consistsOfBuildingPart)
    nClass : xmlClasses.CGML0
        namespace class
    version : str
        CityGML version - either "1.0", "2.0" or "3.0"


    Returns
    -------
    ET.Element
        created element
    """

    if not building.is_building_part:
        building_E = ET.SubElement(
            parent_E,
            ET.QName(nClass.bldg, "Building"),
            attrib={ET.QName(nClass.gml, "id"): building.gml_id},
        )
    else:
        building_E = ET.SubElement(
            parent_E,
            ET.QName(nClass.bldg, "BuildingPart"),
            attrib={ET.QName(nClass.gml, "id"): building.gml_id},
        )

    if version in ["1.0", "2.0"]:
        if building.creationDate is not None:
            ET.SubElement(
                building_E, ET.QName(nClass.core, "creationDate")
            ).text = building.creationDate

        if (
            building.extRef_infromationsSystem is not None
            and building.extRef_objName is not None
        ):
            extRef_E = ET.SubElement(
                building_E, ET.QName(nClass.core, "externalReference")
            )
            ET.SubElement(
                extRef_E, ET.QName(nClass.core, "informationSystem")
            ).text = building.extRef_infromationsSystem
            extObj_E = ET.SubElement(extRef_E, ET.QName(nClass.core, "externalObject"))
            ET.SubElement(
                extObj_E, ET.QName(nClass.core, "name")
            ).text = building.extRef_objName

        for key, value in building.genericStrings.items():
            newGenStr_E = ET.SubElement(
                building_E, ET.QName(nClass.gen, "stringAttribute"), name=key
            )
            ET.SubElement(newGenStr_E, ET.QName(nClass.gen, "value")).text = str(value)

        for key, value in building.genericDoubles.items():
            newGenDbl_E = ET.SubElement(
                building_E, ET.QName(nClass.gen, "doubleAttribute"), name=key
            )
            ET.SubElement(newGenDbl_E, ET.QName(nClass.gen, "value")).text = str(value)

    elif version == "3.0":
        building_E = _add_building_to_cityModel_xml_3_0(
            dataset, building, building_E, nClass
        )

    if building.function is not None:
        ET.SubElement(
            building_E, ET.QName(nClass.bldg, "function")
        ).text = building.function

    if version in ["1.0", "2.0"]:
        if building.yearOfConstruction is not None:
            ET.SubElement(
                building_E, ET.QName(nClass.bldg, "yearOfConstruction")
            ).text = str(building.yearOfConstruction)

    if building.roofType is not None:
        ET.SubElement(
            building_E, ET.QName(nClass.bldg, "roofType")
        ).text = building.roofType

    if version in ["1.0", "2.0"]:
        if building.measuredHeight is not None:
            ET.SubElement(
                building_E, ET.QName(nClass.bldg, "measuredHeight"), uom="urn:adv:uom:m"
            ).text = str(building.measuredHeight)

    if building.storeysAboveGround is not None:
        ET.SubElement(
            building_E, ET.QName(nClass.bldg, "storeysAboveGround")
        ).text = str(building.storeysAboveGround)

    if building.storeysBelowGround is not None:
        ET.SubElement(
            building_E, ET.QName(nClass.bldg, "storeysBelowGround")
        ).text = str(building.storeysBelowGround)

    if building.storeyHeightsAboveGround is not None:
        ET.SubElement(
            building_E, ET.QName(nClass.bldg, "storeyHeightsAboveGround")
        ).text = str(building.storeyHeightsAboveGround)

    if building.storeyHeightsBelowGround is not None:
        ET.SubElement(
            building_E, ET.QName(nClass.bldg, "storeyHeightsBelowGround")
        ).text = str(building.storeyHeightsBelowGround)

    if version in ["1.0", "2.0"]:
        building_E = _add_building_to_cityModel_xml_1_2(
            dataset, building, building_E, nClass
        )

    return building_E


def _add_building_to_cityModel_xml_1_2(
    dataset: Dataset,
    building: AbstractBuilding,
    building_E: ET.Element,
    nClass: citygmlClasses.CGML0,
) -> ET.Element:
    """adds a building or buildingPart to a cityModel

    Parameters
    ----------
    dataset : Dataset
        Dataset for updating min max coordinates
    building : AbstractBuilding
        either Building or BuildingPart object
    building_E : ET.Element
        building xml element of building object
    nClass : xmlClasses.CGML0
        namespace class


    Returns
    -------
    ET.Element
        created element
    """

    for i, geometry in enumerate(building.get_geometries()):
        if geometry.lod == 0:
            _add_lod_0_geometry_to_xml_building(dataset, geometry, building_E, nClass)
        elif geometry.lod == 1:
            if building.terrainIntersections is not None and i == 0:
                _add_terrainIntersection_to_xml_building(
                    building, 1, building_E, nClass, dataset.transform
                )
            _add_lod_1_geometry_to_xml_building(dataset, geometry, building_E, nClass)
        elif geometry.lod == 2:
            if building.terrainIntersections is not None and i == 0:
                _add_terrainIntersection_to_xml_building(
                    building, 2, building_E, nClass, dataset.transform
                )
            _add_lod_2_geometry_to_xml_building(dataset, geometry, building_E, nClass)

    return building_E


def _add_building_to_cityModel_xml_3_0(
    dataset: Dataset,
    building: AbstractBuilding,
    building_E: ET.Element,
    nClass: citygmlClasses.CGML0,
) -> ET.Element:
    """adds a building or buildingPart to a cityModel

    Parameters
    ----------
    dataset : Dataset
        Dataset for updating min max coordinates
    building : AbstractBuilding
        either Building or BuildingPart object
    building_E : ET.Element
        building xml element of building object
    nClass : xmlClasses.CGML0
        namespace class


    Returns
    -------
    ET.Element
        created element
    """
    for i, geometry in enumerate(building.get_geometries()):
        if geometry.lod == 0:
            _add_lod_0_geometry_to_xml_building_3_0(
                dataset, geometry, building_E, nClass
            )
        elif geometry.lod == 1:
            if building.terrainIntersections is not None and i == 0:
                _add_terrainIntersection_to_xml_building(
                    building, 1, building_E, nClass, dataset.transform
                )
            _add_lod_1_geometry_to_xml_building(
                dataset, geometry, building_E, nClass, "3.0"
            )
        elif geometry.lod == 2:
            # TODO add terrainIntersection to lod2 for CityGML 3.0
            # if building.terrainIntersections is not None and i == 0:
            #     _add_terrainIntersection_to_xml_building(
            #         building, 2, building_E, nClass, dataset.transform
            #     )
            _add_lod_2_geometry_to_xml_building_3_0(
                dataset, geometry, building_E, nClass
            )
        if building.measuredHeight is not None:
            height_E = ET.SubElement(building_E, ET.QName(nClass.con, "height"))
            hEIGHT_E = ET.SubElement(height_E, ET.QName(nClass.con, "Height"))
            ET.SubElement(
                hEIGHT_E, ET.QName(nClass.con, "highReference")
            ).text = "highestRoofEdge"
            ET.SubElement(
                hEIGHT_E, ET.QName(nClass.con, "lowReference")
            ).text = "lowestGroundPoint"
            ET.SubElement(hEIGHT_E, ET.QName(nClass.con, "status")).text = "measured"
            ET.SubElement(
                hEIGHT_E, ET.QName(nClass.con, "value"), attrib={"uom": "m"}
            ).text = str(building.measuredHeight)

    return building_E


def _add_lod_0_geometry_to_xml_building(
    dataset: Dataset,
    geometry: GeometryGML,
    building_E: ET.Element,
    nClass: citygmlClasses.CGML0,
) -> None:
    """adds lod0 geometry to an xml element

    Parameters
    ----------
    dataset : Dataset
        CityDPC Dataset for updating min max coordinates
    geometry : GeometryGML
        geometry to be added
    building_E : ET.Element
        direct parent element (either cityObjectMember or consistsOfBuildingPart)
    nClass : citygmlClasses.CGML0
        namespace class
    """
    for groundSurface in geometry.get_surfaces(["GroundSurface"]):
        lodnSolid_E = ET.SubElement(building_E, ET.QName(nClass.bldg, "lod0FootPrint"))
        multiSurface_E = ET.SubElement(
            lodnSolid_E, ET.QName(nClass.gml, "MultiSurface")
        )
        _add_surfaceMember_to_element(dataset, groundSurface, multiSurface_E, nClass)

    for roofSurface in geometry.get_surfaces(["RoofSurface"]):
        lodnSolid_E = ET.SubElement(building_E, ET.QName(nClass.bldg, "lod0RoofEdge"))
        multiSurface_E = ET.SubElement(
            lodnSolid_E, ET.QName(nClass.gml, "MultiSurface")
        )
        _add_surfaceMember_to_element(dataset, roofSurface, multiSurface_E, nClass)


def _add_lod_0_geometry_to_xml_building_3_0(
    dataset: Dataset,
    geometry: GeometryGML,
    building_E: ET.Element,
    nClass: citygmlClasses.CGML0,
) -> None:
    """adds lod0 geometry to an xml element

    Parameters
    ----------
    dataset : Dataset
        CityDPC Dataset for updating min max coordinates
    geometry : GeometryGML
        geometry to be added
    building_E : ET.Element
        direct parent element (either cityObjectMember or consistsOfBuildingPart)
    nClass : citygmlClasses.CGML0
        namespace class
    """
    if roofSurfaces := geometry.get_surfaces(["RoofSurface"]):
        for roofSurface in roofSurfaces:
            lod0multiSurface_E = ET.SubElement(
                building_E, ET.QName(nClass.core, "lod0MultiSurface")
            )
            _add_surfaceMember_to_element(
                dataset, roofSurface, lod0multiSurface_E, nClass
            )
        return
    else:
        for groundSurface in geometry.get_surfaces(["GroundSurface"]):
            lod0multiSurface_E = ET.SubElement(
                building_E, ET.QName(nClass.core, "lod0MultiSurface")
            )
            _add_surfaceMember_to_element(
                dataset, groundSurface, lod0multiSurface_E, nClass
            )


def _add_surfaceMember_to_element(
    dataset: Dataset,
    surface: SurfaceGML,
    parent_E: ET.Element,
    nClass: citygmlClasses.CGML0,
) -> None:
    """adds a surface to an xml element

    Parameters
    ----------
    dataset : Dataset
        CityDPC Dataset for updating min max coordinates
    surface : SurfaceGML
        surface to be added
    parent_E : ET.Element
        direct parent element (either cityObjectMember or consistsOfBuildingPart)
    nClass : citygmlClasses.CGML0
        namespace class
    """
    surfaceMember_E = ET.SubElement(parent_E, ET.QName(nClass.gml, "surfaceMember"))
    polygon_E = ET.SubElement(surfaceMember_E, ET.QName(nClass.gml, "Polygon"))
    exterior_E = ET.SubElement(polygon_E, ET.QName(nClass.gml, "exterior"))
    linearRing_E = ET.SubElement(exterior_E, ET.QName(nClass.gml, "LinearRing"))

    posList_E = ET.SubElement(
        linearRing_E,
        ET.QName(nClass.gml, "posList"),
        attrib={"srsDimension": "3"},
    )
    posList_E.text = __untransform_surface_to_str(surface, dataset.transform)
    update_dataset_min_max_from_surface(dataset, surface)


def _add_lod_1_geometry_to_xml_building(
    dataset: Dataset,
    geometry: GeometryGML,
    building_E: ET.Element,
    nClass: citygmlClasses.CGML0,
    version: str = "2.0",
) -> None:
    """adds lod1 geometry to an xml element

    Parameters
    ----------
    dataset : Dataset
        CityDPC Dataset for updating min max coordinates
    geometry : GeometryGML
        geometry to be added
    building_E : ET.Element
        direct parent element (either cityObjectMember or consistsOfBuildingPart)
    nClass : citygmlClasses.CGML0
        namespace class
    version: str
        CityGML version - either "1.0", "2.0" or "3.0"
    """
    lodnSolid_E = ET.SubElement(building_E, ET.QName(nClass.bldg, "lod1Solid"))
    solid_E = ET.SubElement(lodnSolid_E, ET.QName(nClass.gml, "Solid"))
    exterior_E = ET.SubElement(solid_E, ET.QName(nClass.gml, "exterior"))
    if version in ["1.0", "2.0"]:
        compositeSurface_E = ET.SubElement(
            exterior_E, ET.QName(nClass.gml, "CompositeSurface")
        )
    elif version == "3.0":
        compositeSurface_E = ET.SubElement(exterior_E, ET.QName(nClass.gml, "Shell"))

    for surface in geometry.get_surfaces():
        _add_surfaceMember_to_element(dataset, surface, compositeSurface_E, nClass)


def _add_lod_2_geometry_to_xml_building(
    dataset: Dataset,
    geometry: GeometryGML,
    building_E: ET.Element,
    nClass: citygmlClasses.CGML0,
) -> None:
    """adds lod2 geometry to an xml element

    Parameters
    ----------
    dataset : Dataset
        CityDPC Dataset for updating min max coordinates
    geometry : GeometryGML
        geometry to be added
    building_E : ET.Element
        direct parent element (either cityObjectMember or consistsOfBuildingPart)
    nClass : citygmlClasses.CGML0
        namespace class
    """
    if geometry.type == "Solid":
        lodnSolid_E = ET.SubElement(building_E, ET.QName(nClass.bldg, "lod2Solid"))
        solid_E = ET.SubElement(lodnSolid_E, ET.QName(nClass.gml, "Solid"))
        exterior_E = ET.SubElement(solid_E, ET.QName(nClass.gml, "exterior"))
        compositeSurface_E = ET.SubElement(
            exterior_E, ET.QName(nClass.gml, "CompositeSurface")
        )

    for surface in geometry.get_surfaces():
        if surface.polygon_id is not None:
            polyID = surface.polygon_id
        else:
            polyID = str(uuid.uuid1())
        if geometry.type == "Solid":
            href_id = f"#{polyID}"
            ET.SubElement(
                compositeSurface_E,
                ET.QName(nClass.gml, "surfaceMember"),
                attrib={ET.QName(nClass.xlink, "href"): href_id},
            )

        boundedBy_E = ET.SubElement(building_E, ET.QName(nClass.bldg, "boundedBy"))
        wallRoofGround_E = ET.SubElement(
            boundedBy_E,
            ET.QName(nClass.bldg, surface.surface_type),
        )
        if surface.surface_id is not None and not surface.surface_id.startswith(
            "citydpc_"
        ):
            wallRoofGround_E.attrib[
                "{http://www.opengis.net/gml}id"
            ] = surface.surface_id
        # ET.SubElement(wallRoofGround_E, "creationDate").text = need to store data
        lodnMultisurface_E = ET.SubElement(
            wallRoofGround_E, ET.QName(nClass.bldg, "lod2MultiSurface")
        )
        multiSurface_E = ET.SubElement(
            lodnMultisurface_E, ET.QName(nClass.gml, "MultiSurface")
        )
        surfaceMember_E = ET.SubElement(
            multiSurface_E, ET.QName(nClass.gml, "surfaceMember")
        )

        polygon_E = ET.SubElement(
            surfaceMember_E,
            ET.QName(nClass.gml, "Polygon"),
        )
        if geometry.type == "Solid":
            polygon_E.attrib["{http://www.opengis.net/gml}id"] = polyID

        if surface.polygon_id is not None and not surface.polygon_id.startswith(
            "citydpc_"
        ):
            polygon_E.attrib["{http://www.opengis.net/gml}id"] = surface.polygon_id

        exterior_E = ET.SubElement(polygon_E, ET.QName(nClass.gml, "exterior"))

        linearRing_E = ET.SubElement(exterior_E, ET.QName(nClass.gml, "LinearRing"))
        posList_E = ET.SubElement(
            linearRing_E,
            ET.QName(nClass.gml, "posList"),
            attrib={"srsDimension": "3"},
        )
        posList_E.text = __untransform_surface_to_str(surface, dataset.transform)
        update_dataset_min_max_from_surface(dataset, surface)


def _add_lod_2_geometry_to_xml_building_3_0(
    dataset: Dataset,
    geometry: GeometryGML,
    building_E: ET.Element,
    nClass: citygmlClasses.CGML0,
) -> None:
    """adds lod2 geometry to an xml element

    Parameters
    ----------
    dataset : Dataset
        CityDPC Dataset for updating min max coordinates
    geometry : GeometryGML
        geometry to be added
    building_E : ET.Element
        direct parent element (either cityObjectMember or consistsOfBuildingPart)
    nClass : citygmlClasses.CGML0
        namespace class
    """
    usedHrefs = []
    for surface in geometry.get_surfaces():
        if surface.polygon_id is not None:
            polyID = surface.polygon_id
        else:
            polyID = str(uuid.uuid1())
        if geometry.type == "Solid":
            usedHrefs.append(f"#{polyID}")
        boundary_E = ET.SubElement(building_E, ET.QName(nClass.core, "boundary"))
        wallRoofGround_E = ET.SubElement(
            boundary_E,
            ET.QName(nClass.core, surface.surface_type),
        )
        if surface.surface_id is not None and not surface.surface_id.startswith(
            "citydpc_"
        ):
            wallRoofGround_E.attrib[
                "{http://www.opengis.net/gml}id"
            ] = surface.surface_id
        lodnMultisurface_E = ET.SubElement(
            wallRoofGround_E, ET.QName(nClass.bldg, "lod2MultiSurface")
        )
        multiSurface_E = ET.SubElement(
            lodnMultisurface_E, ET.QName(nClass.gml, "MultiSurface")
        )
        surfaceMember_E = ET.SubElement(
            multiSurface_E, ET.QName(nClass.gml, "surfaceMember")
        )

        polygon_E = ET.SubElement(
            surfaceMember_E,
            ET.QName(nClass.gml, "Polygon"),
        )
        if geometry.type == "Solid":
            polygon_E.attrib["{http://www.opengis.net/gml}id"] = polyID

        if surface.polygon_id is not None and not surface.polygon_id.startswith(
            "citydpc_"
        ):
            polygon_E.attrib["{http://www.opengis.net/gml}id"] = surface.polygon_id

        exterior_E = ET.SubElement(polygon_E, ET.QName(nClass.gml, "exterior"))

        linearRing_E = ET.SubElement(exterior_E, ET.QName(nClass.gml, "LinearRing"))
        posList_E = ET.SubElement(
            linearRing_E,
            ET.QName(nClass.gml, "posList"),
            attrib={"srsDimension": "3"},
        )
        posList_E.text = __untransform_surface_to_str(surface, dataset.transform)
        update_dataset_min_max_from_surface(dataset, surface)

    if usedHrefs:
        lodnSolid_E = ET.SubElement(building_E, ET.QName(nClass.core, "lod2Solid"))
        solid_E = ET.SubElement(lodnSolid_E, ET.QName(nClass.gml, "Solid"))
        exterior_E = ET.SubElement(solid_E, ET.QName(nClass.gml, "exterior"))
        for href in usedHrefs:
            ET.SubElement(
                exterior_E,
                ET.QName(nClass.gml, "surfaceMember"),
                attrib={ET.QName(nClass.xlink, "href"): href},
            )


def _add_terrainIntersection_to_xml_building(
    building: AbstractBuilding,
    lod: int,
    parent_E: ET.Element,
    nClass: citygmlClasses.CGML0,
    transformDict: dict,
) -> None:
    """adds terrainIntersection to an xml element

    Parameters
    ----------
    building : AbstractBuilding
        Building object
    lod : int
        Level of Detail
    parent_E : ET.Element
        direct parent element (either cityObjectMember or consistsOfBuildingPart)
    nClass : xmlClasses.CGML0
        namespace class
    transformDict : dict
        transformation dict (in case coordinates have not been transformed yet)
    """

    lodNTI_E = ET.SubElement(
        parent_E, ET.QName(nClass.bldg, f"lod{lod}TerrainIntersection")
    )
    multiCurve_E = ET.SubElement(lodNTI_E, ET.QName(nClass.gml, "MultiCurve"))
    for curve in building.terrainIntersections:
        curveMember_E = ET.SubElement(multiCurve_E, ET.QName(nClass.gml, "curveMember"))
        lineString_E = ET.SubElement(curveMember_E, ET.QName(nClass.gml, "LineString"))
        posList_E = ET.SubElement(
            lineString_E, ET.QName(nClass.gml, "posList"), attrib={"srsDimension": "3"}
        )
        posList_E.text = __untransform_curve_to_str(curve, transformDict)


def _add_address_to_xml_building(
    address: CoreAddress, parent_E: ET.Element, nClass: citygmlClasses.CGML0
) -> None:
    """add address to an xml element (parent_E)

    Parameters
    ----------
    address : CoreAddress
        address object
    parent_E : ET.Element
        direct parent element (either cityObjectMember or consistsOfBuildingPart)
    nClass : xmlClasses.CGML0
        namespace class
    """

    bldgAddress_E = ET.SubElement(parent_E, ET.QName(nClass.bldg, "address"))
    address_E = ET.SubElement(bldgAddress_E, "Address")
    if address.gml_id is not None:
        address_E.attrib["{http://www.opengis.net/gml}id"] = address.gml_id
    xalAddress_E = ET.SubElement(address_E, "xalAddress")
    addressDetails_E = ET.SubElement(
        xalAddress_E, ET.QName(nClass.xal, "AddressDetails")
    )
    country_E = ET.SubElement(addressDetails_E, ET.QName(nClass.xal, "Country"))

    if address.countryName is not None:
        ET.SubElement(
            country_E, ET.QName(nClass.xal, "CountryName")
        ).text = address.countryName

    if address.locality_type is not None:
        locality_E = ET.SubElement(
            country_E,
            ET.QName(nClass.xal, "Locality"),
            attrib={"Type": address.locality_type},
        )
    else:
        locality_E = ET.SubElement(
            country_E,
            ET.QName(nClass.xal, "Locality"),
        )

    if address.localityName is not None:
        ET.SubElement(
            locality_E, ET.QName(nClass.xal, "LocalityName")
        ).text = address.localityName

    if (
        address.thoroughfare_type is not None
        or address.thoroughfareName is not None
        or address.thoroughfareNumber is not None
    ):
        thoroughfare_E = ET.SubElement(
            locality_E, ET.QName(nClass.xal, "Thoroughfare")
        )

        if address.thoroughfare_type is not None:
            thoroughfare_E.attrib["Type"] = address.thoroughfare_type

        if address.thoroughfareNumber is not None:
            ET.SubElement(
                thoroughfare_E, ET.QName(nClass.xal, "ThoroughfareNumber")
            ).text = address.thoroughfareNumber

        if address.thoroughfareName is not None:
            ET.SubElement(
                thoroughfare_E, ET.QName(nClass.xal, "ThoroughfareName")
            ).text = address.thoroughfareName

    if address.postalCodeNumber is not None:
        postalCode_E = ET.SubElement(locality_E, ET.QName(nClass.xal, "PostalCode"))
        ET.SubElement(
            postalCode_E, ET.QName(nClass.xal, "PostalCodeNumber")
        ).text = address.postalCodeNumber


def __untransform_surface_to_str(surface: SurfaceGML, transform: dict) -> str:
    """transforms coordinates back to their original values

    Parameters
    ----------
    surface : SurfaceGML
        surface to be transformed
    transform : dict
        transformation dict

    Returns
    -------
    str
        transformed coordinates
    """
    if transform == {"scale": [1, 1, 1], "translate": [0, 0, 0]}:
        return " ".join(map(str, surface.gml_surface))

    new_coords = []
    for coord in surface.gml_surface_2array:
        new_coords.extend(
            [
                coord[0] * transform["scale"][0] + transform["translate"][0],
                coord[1] * transform["scale"][1] + transform["translate"][1],
                coord[2] * transform["scale"][2] + transform["translate"][2],
            ]
        )

    return " ".join(map(str, new_coords))


def __untransform_curve_to_str(curve: list[list[float]], transform: dict) -> str:
    """transforms coordinates back to their original values

    Parameters
    ----------
    curve : list[list[float]]
        curve to be transformed
    transform : dict
        transformation dict

    Returns
    -------
    str
        transformed coordinates
    """
    if transform == {"scale": [1, 1, 1], "translate": [0, 0, 0]}:
        return " ".join(map(str, curve))

    new_coords = []
    for coord in curve:
        new_coords.extend(
            [
                coord[0] * transform["scale"][0] + transform["translate"][0],
                coord[1] * transform["scale"][1] + transform["translate"][1],
                coord[2] * transform["scale"][2] + transform["translate"][2],
            ]
        )

    return " ".join(map(str, new_coords))
