from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyStadt.dataset import Dataset
    from pyStadt.core.obejcts.building import Building


import lxml.etree as ET

import pyStadt.util.citygmlClasses as citygmlClasses
from pyStadt.util.envelope import update_min_max


def write_citygml_file(dataset: Dataset, filename: str, version: str = "2.0"):
    """writes Dataset to citygml file

    Parameters
    ----------
    dataset : Dataset
        dataset that should be saved
    filename : str
        new filename (including path if wanted)
    version : str
        CityGML version - either "1.0" or "2.0"
    """

    if dataset.srsName is None:
        print("unable to create file, set srsName frist")
        return

    if version == "1.0":
        nClass = citygmlClasses.CGML1
    elif version == "2.0":
        nClass = citygmlClasses.CGML2
    else:
        return

    # creating new namespacemap
    newNSmap = {
        None: nClass.core,
        "core": nClass.core,
        "gen": nClass.gen,
        "grp": nClass.grp,
        "app": nClass.app,
        "bldg": nClass.bldg,
        "gml": nClass.gml,
        "xal": nClass.xal,
        "xlink": nClass.xlink,
        "xsi": nClass.xsi,
    }

    # creating new root element
    nroot_E = ET.Element(ET.QName(nClass.core, "CityModel"), nsmap=newNSmap)

    # creating name element
    name_E = ET.SubElement(
        nroot_E, ET.QName(nClass.gml, "name"), nsmap={"gml": nClass.gml}
    )
    name_E.text = "created using the e3D pyStadt"

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

            if not buildingPart.address.address_is_empty():
                _add_address_to_xml_building(buildingPart, bp_E, nClass)

        if not building.address.address_is_empty():
            _add_address_to_xml_building(building, building_E, nClass)

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
    building: Building,
    parent_E: ET.Element,
    nClass: citygmlClasses.CGML0,
) -> ET.Element:
    """adds a building or buildingPart to a cityModel

    Parameters
    ----------
    dataset : Dataset
        Dataset for updating min max coordinates
    building : Building
        either Building or BuildingPart object
    parent_E : ET.Element
        direct parent element (either cityObjectMember or consistsOfBuildingPart)
    nClass : xmlClasses.CGML0
        namespace class


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

    if building.creationDate is not None:
        ET.SubElement(
            building_E, ET.QName(nClass.core, "creationDate")
        ).text = building.creationDate

    if (
        building.extRef_infromationsSystem is not None
        and building.extRef_objName is not None
    ):
        extRef_E = ET.SubElement(building_E, ET.QName(nClass.core, "externalReference"))
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
        ET.SubElement(newGenStr_E, ET.QName(nClass.gen, "value")).text = value

    if building.function is not None:
        ET.SubElement(
            building_E, ET.QName(nClass.bldg, "function")
        ).text = building.function

    if building.yearOfConstruction is not None:
        ET.SubElement(
            building_E, ET.QName(nClass.bldg, "yearOfConstruction")
        ).text = building.yearOfConstruction

    if building.roofType is not None:
        ET.SubElement(
            building_E, ET.QName(nClass.bldg, "roofType")
        ).text = building.roofType

    if building.measuredHeight is not None:
        ET.SubElement(
            building_E, ET.QName(nClass.bldg, "measuredHeight"), uom="urn:adv:uom:m"
        ).text = building.measuredHeight

    if building.storeysAboveGround is not None:
        ET.SubElement(
            building_E, ET.QName(nClass.bldg, "storeysAboveGround")
        ).text = building.storeysAboveGround

    if building.storeysBelowGround is not None:
        ET.SubElement(
            building_E, ET.QName(nClass.bldg, "storeysBelowGround")
        ).text = building.storeysBelowGround

    if building.lod == "2":
        lodnSolid_E = ET.SubElement(building_E, ET.QName(nClass.bldg, "lod2Solid"))
        solid_E = ET.SubElement(lodnSolid_E, ET.QName(nClass.gml, "Solid"))
        exterior_E = ET.SubElement(solid_E, ET.QName(nClass.gml, "exterior"))
        compositeSurface_E = ET.SubElement(
            exterior_E, ET.QName(nClass.gml, "CompositeSurface")
        )

        if building.terrainIntersections is not None:
            _add_terrainIntersection_to_xml_building(building, 2, building_E, nClass)

        for surface in (
            list(building.roofs.values())
            + list(building.walls.values())
            + list(building.closure.values())
            + list(building.grounds.values())
        ):
            href_id = f"#{surface.polygon_id}"
            ET.SubElement(
                compositeSurface_E,
                ET.QName(nClass.gml, "surfaceMember"),
                attrib={ET.QName(nClass.xlink, "href"): href_id},
            )

            boundedBy_E = ET.SubElement(building_E, ET.QName(nClass.bldg, "boundedBy"))
            wallRoofGround_E = ET.SubElement(
                boundedBy_E,
                ET.QName(nClass.bldg, surface.surface_type),
                attrib={ET.QName(nClass.gml, "id"): surface.surface_id},
            )
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
                attrib={ET.QName(nClass.gml, "id"): surface.polygon_id},
            )
            exterior_E = ET.SubElement(polygon_E, ET.QName(nClass.gml, "exterior"))

            linearRing_E = ET.SubElement(exterior_E, ET.QName(nClass.gml, "LinearRing"))
            posList_E = ET.SubElement(
                linearRing_E,
                ET.QName(nClass.gml, "posList"),
                attrib={"srsDimension": "3"},
            )
            posList_E.text = " ".join(map(str, surface.gml_surface))
            update_min_max(dataset, surface)

    elif building.lod == "1":
        lodnSolid_E = ET.SubElement(building_E, ET.QName(nClass.bldg, "lod1Solid"))
        solid_E = ET.SubElement(lodnSolid_E, ET.QName(nClass.gml, "Solid"))
        exterior_E = ET.SubElement(solid_E, ET.QName(nClass.gml, "exterior"))
        compositeSurface_E = ET.SubElement(
            exterior_E, ET.QName(nClass.gml, "CompositeSurface")
        )

        if building.terrainIntersections is not None:
            _add_terrainIntersection_to_xml_building(building, 1, building_E, nClass)

        for surface in (
            list(building.roofs.values())
            + list(building.walls.values())
            + list(building.closure.values())
            + list(building.grounds.values())
        ):
            surfaceMember_E = ET.SubElement(
                compositeSurface_E, ET.QName(nClass.gml, "surfaceMember")
            )
            polygon_E = ET.SubElement(surfaceMember_E, ET.QName(nClass.gml, "Polygon"))
            exterior_E2 = ET.SubElement(polygon_E, ET.QName(nClass.gml, "exterior"))
            linearRing_E = ET.SubElement(
                exterior_E2, ET.QName(nClass.gml, "LinearRing")
            )

            posList_E = ET.SubElement(
                linearRing_E,
                ET.QName(nClass.gml, "posList"),
                attrib={"srsDimension": "3"},
            )
            posList_E.text = " ".join(map(str, surface.gml_surface))
            update_min_max(dataset, surface)

    elif building.lod == "0":
        if len(building.roofs) > 0:
            lodnSolid_E = ET.SubElement(
                building_E, ET.QName(nClass.bldg, "lod0Footprint")
            )
            multiSurface_E = ET.SubElement(
                lodnSolid_E, ET.QName(nClass.gml, "MultiSurface")
            )
            surfaceMember_E = ET.SubElement(
                multiSurface_E, ET.QName(nClass.gml, "surfaceMember")
            )
            polygon_E = ET.SubElement(surfaceMember_E, ET.QName(nClass.gml, "Polygon"))
            exterior_E = ET.SubElement(polygon_E, ET.QName(nClass.gml, "exterior"))
            linearRing_E = ET.SubElement(exterior_E, ET.QName(nClass.gml, "LinearRing"))

            posList_E = ET.SubElement(
                linearRing_E,
                ET.QName(nClass.gml, "posList"),
                attrib={"srsDimension": "3"},
            )
            posList_E.text = " ".join(
                map(str, list(building.roofs.values())[0].gml_surface)
            )
            update_min_max(dataset, surface)

        if len(building.grounds) > 0:
            lodnSolid_E = ET.SubElement(
                building_E, ET.QName(nClass.bldg, "lod0RoofEdge")
            )
            multiSurface_E = ET.SubElement(
                lodnSolid_E, ET.QName(nClass.gml, "MultiSurface")
            )
            surfaceMember_E = ET.SubElement(
                multiSurface_E, ET.QName(nClass.gml, "surfaceMember")
            )
            polygon_E = ET.SubElement(surfaceMember_E, ET.QName(nClass.gml, "Polygon"))
            exterior_E = ET.SubElement(polygon_E, ET.QName(nClass.gml, "exterior"))
            linearRing_E = ET.SubElement(exterior_E, ET.QName(nClass.gml, "LinearRing"))

            posList_E = ET.SubElement(
                linearRing_E,
                ET.QName(nClass.gml, "posList"),
                attrib={"srsDimension": "3"},
            )
            posList_E.text = " ".join(
                map(str, list(building.roofs.values())[0].gml_surface)
            )
            update_min_max(dataset, surface)

    return building_E


def _add_terrainIntersection_to_xml_building(
    building: Building, lod: int, parent_E: ET.Element, nClass: citygmlClasses.CGML0
) -> None:
    """adds terrainIntersection to an xml element

    Parameters
    ----------
    building : Building
        Building object
    lod : int
        Level of Detail
    parent_E : ET.Element
        direct parent element (either cityObjectMember or consistsOfBuildingPart)
    nClass : xmlClasses.CGML0
        namespace class
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
        posList_E.text = " ".join(map(str, curve))


def _add_address_to_xml_building(
    building: Building, parent_E: ET.Element, nClass: citygmlClasses.CGML0
) -> None:
    """add address to an xml element (parent_E)

    Parameters
    ----------
    building : Building
        either Building or BuildingPart object
    parent_E : ET.Element
        direct parent element (either cityObjectMember or consistsOfBuildingPart)
    nClass : xmlClasses.CGML0
        namespace class
    """

    if not building.address.address_is_empty():
        bldgAddress_E = ET.SubElement(parent_E, ET.QName(nClass.bldg, "address"))
        address_E = ET.SubElement(bldgAddress_E, "Address")
        if building.address.gml_id is not None:
            address_E.attrib["{http://www.opengis.net/gml}id"] = building.address.gml_id
        xalAddress_E = ET.SubElement(address_E, "xalAddress")
        addressDetails_E = ET.SubElement(
            xalAddress_E, ET.QName(nClass.xal, "AddressDetails")
        )
        country_E = ET.SubElement(addressDetails_E, ET.QName(nClass.xal, "Country"))

        if building.address.countryName is not None:
            ET.SubElement(
                country_E, ET.QName(nClass.xal, "CountryName")
            ).text = building.address.countryName

        if building.address.locality_type is not None:
            locality_E = ET.SubElement(
                country_E,
                ET.QName(nClass.xal, "Locality"),
                attrib={"Type": building.address.locality_type},
            )
        else:
            locality_E = ET.SubElement(
                country_E,
                ET.QName(nClass.xal, "Locality"),
            )

        if building.address.localityName is not None:
            ET.SubElement(
                locality_E, ET.QName(nClass.xal, "LocalityName")
            ).text = building.address.localityName

        if (
            building.address.thoroughfare_type is not None
            or building.address.thoroughfareName is not None
            or building.address.thoroughfareNumber is not None
        ):
            thoroughfare_E = ET.SubElement(
                locality_E, ET.QName(nClass.xal, "Thoroughfare")
            )

            if building.address.thoroughfare_type is not None:
                thoroughfare_E.attrib["Type"] = building.address.thoroughfare_type

            if building.address.thoroughfareNumber is not None:
                ET.SubElement(
                    thoroughfare_E, ET.QName(nClass.xal, "ThoroughfareNumber")
                ).text = building.address.thoroughfareNumber

            if building.address.thoroughfareName is not None:
                ET.SubElement(
                    thoroughfare_E, ET.QName(nClass.xal, "ThoroughfareName")
                ).text = building.address.thoroughfareName

        if building.address.postalCodeNumber is not None:
            postalCode_E = ET.SubElement(locality_E, ET.QName(nClass.xal, "PostalCode"))
            ET.SubElement(
                postalCode_E, ET.QName(nClass.xal, "PostalCodeNumber")
            ).text = building.address.postalCodeNumber
