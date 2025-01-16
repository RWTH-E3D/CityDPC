from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from citydpc.logger import logger
from citydpc.core.object.geometry import GeometryGML
from citydpc.core.object.building import Building
from citydpc.util import cityBITutil as cBU


def create_LoD2_building(
    id: str,
    groundsCoordinates: list[list[float]],
    groundSurfaceHeight: float,
    geometryHeight: float,
    roofType: str,
    roofHeight: float = None,
    roofOrientation: int = None,
) -> Building:
    """create a LoD2 building from a list of coordinates

    Parameters
    ----------
    id : str
        gml:id of building
    groundsCoordinates : list[list[float]]
        list of coordinates of ground surface in 2D, should be self closing
    groundSurfaceHeight : float
        height of ground surface
    geometryHeight : float
        height of building geometry (from lowest point to highest point), has to be positive and
        greater than 0
    roofType : str
        type of roof, one of ["1000", "1010", "1020", "1030", "1040", "1070"]
    roofHeight : float, optional
        height of roof (relative height difference from lowest point of roof to highest
        point of roof), required for every roofType except "1000"
    roofOrientation : int, optional
        orientation of roof, required for every roofType except "1000" and "1070"
        refers to the index of the groundCoordinates list
        e.g. 0 for the roof to end on the first side of grounsSurface

    Returns
    -------
    Building
        LoD2 building
    """
    if not isinstance(id, str):
        raise ValueError("id must be a string")
    groundSurface = cBU.create_flat_surface(id, groundsCoordinates, groundSurfaceHeight)
    # make sure that same coordiantes are used as in groundSurface object
    # (regarding order, dropped coorindates)
    gC3D = groundSurface.gml_surface_2array
    gC2D = gC3D[:, :2]

    # ensure that buildingHeight is positive and greater than 0 (actual LoD2)
    if geometryHeight < 0:
        raise ValueError("buildingHeight must be positive and greater than 0")

    # ensure that all needed values are given
    if roofType == "1000":
        # flat roof checks
        if roofHeight is not None:
            logger.warning(
                f"roofHeight for building {id} is not needed for roofType 1000 and will"
                + " be ignored"
            )
        if roofOrientation is not None:
            logger.warning(
                f"roofOrientation for building {id} is not needed for roofType 1000 and"
                + " will be ignored"
            )
    elif roofType in ["1010", "1020", "1030", "1040", "1070"]:
        # sloped roof checks
        if roofHeight is None:
            raise ValueError("roofHeight must be specified for roofType 1070")
        elif roofHeight < 0:
            raise ValueError("roofHeight must be positive and greater than 0")
        elif roofHeight > geometryHeight:
            raise ValueError(
                "roofHeight must be smaller than buildingHeight (from lowest point to"
                + " highest point)"
            )
        if roofType == "1070":
            # pavilion roof
            if roofOrientation is not None:
                logger.warning(
                    f"roofOrientation for building {id} is not needed for roofType 1070"
                    + " and will be ignored"
                )
        else:
            # roofs with orientation
            if len(groundSurface.gml_surface_2array) != 5:
                raise ValueError(
                    f"groundSurface must be a rectangle for roofType {roofType}"
                )
            if roofType == "1040":
                pass
            elif roofOrientation is None:
                raise ValueError(
                    f"roofOrientation must be specified for roofType {roofType}"
                )
            elif roofOrientation < 0 or roofOrientation >= 4:
                raise ValueError(
                    "roofOrientation must be an integer between 0 and"
                    + " 3 (both included)"
                )
    else:
        raise ValueError(
            "roofType must be one of ['1000', '1010', '1020', '1030', '1040', '1070']"
        )

    # start building creation process
    building = Building(id)
    building.lod = 2
    building.is_building_part = False

    geometry = GeometryGML("Solid", f"geom_{id}", lod=2)

    building.add_geometry(geometry)
    geometry.add_surface(groundSurface)

    gSH = groundSurfaceHeight
    bHAbs = gSH + geometryHeight

    if roofType == "1000":
        cBU.add_flat_roof_and_walls(geometry, id, gC2D, gSH, bHAbs)
    elif roofType in ["1010", "1020", "1030", "1040", "1070"]:
        bWAbs = bHAbs - roofHeight
        if roofType == "1010":
            cBU.add_monopitch_roof_and_walls(
                geometry, id, gC2D, gSH, bHAbs, bWAbs, roofOrientation
            )

        elif roofType == "1020":
            cBU.add_dualpent_roof_and_walls(
                geometry, id, gC2D, gSH, bHAbs, bWAbs, roofOrientation, roofHeight
            )

        elif roofType == "1030":
            cBU.add_gabled_roof_and_walls(
                geometry, id, gC2D, gSH, bHAbs, bWAbs, roofOrientation
            )

        elif roofType == "1040":
            cBU.add_hipped_roof_and_walls(geometry, id, gC2D, gSH, bHAbs, bWAbs)

        elif roofType == "1070":
            cBU.add_pavilion_roof_and_walls(geometry, id, gC2D, gSH, bHAbs, bWAbs)

    building.measuredHeight = geometryHeight
    building.roofType = str(roofType)

    return building


def create_LoD1_building(
    id: str,
    groundsCoordinates: list[list[float]],
    groundSurfaceHeight: float,
    geometryHeight: float,
) -> Building:
    """create LoD1 building

    Parameters
    ----------
    id : str
        gml:id of building
    groundsCoordinates : list[list[float]]
        list of coordinates of ground surface in 2D, should be self closing
    groundSurfaceHeight : float
        height of ground surface
    geometryHeight : float
        height of building geometry (from lowest point to highest point), has to be positive and
        greater than 0
    """
    building = create_LoD2_building(
        id, groundsCoordinates, groundSurfaceHeight, geometryHeight, "1000"
    )
    building.roofType = None
    building.lod = 1
    building.get_geometries()[0].lod = 1
    return building


def create_LoD0_building(
    id: str,
    groundsCoordinates: list[list[float]],
    groundSurfaceHeight: float,
    isRoofEdge: bool = False,
) -> Building:
    """create LoD0 building

    Parameters
    ----------
    id : str
        gml:id of building
    groundsCoordinates : list[list[float]]
        list of coordinates of ground surface in 2D, should be self closing
    groundSurfaceHeight : float
        height of ground surface
    """
    if not isinstance(id, str):
        raise ValueError("id must be a string")
    mainSurface = cBU.create_flat_surface(
        id, groundsCoordinates, groundSurfaceHeight, isRoofEdge
    )
    building = Building(id)
    building.lod = 0
    building.is_building_part = False

    geometry = GeometryGML("MultiSurface", f"geom_{id}", lod=0)
    building.add_geometry(geometry)
    geometry.add_surface(mainSurface)
    return building
