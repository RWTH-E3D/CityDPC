from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from citydpc.core.obejct.geometry import GeometryGML

from citydpc.core.obejct.surfacegml import SurfaceGML
from citydpc.util import coordinateOperations as cO

import numpy as np


def add_flat_roof_and_walls(
    geometry: GeometryGML, id: int, gC2D: list[list[float]], gSH: float, bHAbs: float
):
    """create a flat roof and walls from a list of coordinates

    Parameters
    ----------
    geometry : GeometryGML
        geometry object to add the surfaces to
    id : int
        id of the building
    gC2D : list[list[float]]
        list of coordinates of ground surface in 2D, needs to be self closing
    gSH : float
        ground surface height
    bHAbs : float
        bulding height absolute (highest height of building in coordinate system)
    """
    # create wall surfaces
    for i, crd in enumerate(gC2D[:-1]):
        crd = list(crd)
        nCrd = list(gC2D[i + 1])
        wallSurface = SurfaceGML(
            np.array(
                [
                    crd + [gSH],
                    crd + [bHAbs],
                    nCrd + [bHAbs],
                    nCrd + [gSH],
                    crd + [gSH],
                ]
            ).flatten(),
            surface_type="WallSurface",
            surface_id=f"citydpc_wall_{id}_{i}",
        )
        geometry.add_surface(wallSurface)

    helper = [list(crd) + [bHAbs] for crd in gC2D]
    helper.reverse()
    # create roof surface
    roofSurface = SurfaceGML(
        np.array(helper).flatten(),
        surface_type="RoofSurface",
        surface_id=f"citydpc_roof_{id}",
    )
    geometry.add_surface(roofSurface)


def add_monopitch_roof_and_walls(
    geometry: GeometryGML,
    id: int,
    gC2D: list[list[float]],
    gSH: float,
    bHAbs: float,
    bWAbs: float,
    roofOrientation: int,
):
    """create a monopitch roof and walls from a list of coordinates

    Parameters
    ----------
    geometry : GeometryGML
        geometry object to add the surfaces to
    id : int
        id of the building
    gC2D : list[list[float]]
        list of coordinates of ground surface in 2D, needs to be self closing
    gSH : float
        ground surface height
    bHAbs : float
        bulding height absolute (highest height of building in coordinate system)
    bWAbs : float
        building wall height absolute (lowest height of the roof in coordinate system)
    roofOrientation : int
        orientation of roof, refers to the index of the groundCoordinates list between 0
        and 3 (inclusive)
    """

    roofCrds = []
    for i in range(4):
        crd = list(gC2D[i])
        nCrd = list(gC2D[i + 1])
        # create wall surfaces
        if i == roofOrientation:
            # both low
            coords = [
                crd + [gSH],
                crd + [bWAbs],
                nCrd + [bWAbs],
                nCrd + [gSH],
                crd + [gSH],
            ]
        elif i - roofOrientation == 2 or i - roofOrientation == -2:
            # both high
            coords = [
                crd + [gSH],
                crd + [bHAbs],
                nCrd + [bHAbs],
                nCrd + [gSH],
                crd + [gSH],
            ]
        elif (roofOrientation + 1) % 4 - (i + 1) == -1:
            # i low     i+1 high
            coords = [
                crd + [gSH],
                crd + [bWAbs],
                nCrd + [bHAbs],
                nCrd + [gSH],
                crd + [gSH],
            ]
        else:
            # i high    i+1 low
            coords = [
                crd + [gSH],
                crd + [bHAbs],
                nCrd + [bWAbs],
                nCrd + [gSH],
                crd + [gSH],
            ]
        wallSurface = SurfaceGML(
            np.array(coords).flatten(),
            surface_type="WallSurface",
            surface_id=f"citydpc_wall_{id}_{i}",
        )
        geometry.add_surface(wallSurface)
        roofCrds.append(coords[1])

    roofCrds.append(roofCrds[0])
    roofCrds.reverse()
    roofSurface = SurfaceGML(
        np.array(roofCrds).flatten(),
        surface_type="RoofSurface",
        surface_id=f"citydpc_roof_{id}_{i}",
    )
    geometry.add_surface(roofSurface)


def add_dualpent_roof_and_walls(
    geometry: GeometryGML,
    id: int,
    gC2D: list[list[float]],
    gSH: float,
    bHAbs: float,
    bWAbs: float,
    roofOrientation: int,
    roofHeight: float,
):
    """create a dualpent roof and walls from a list of coordinates

    Parameters
    ----------
    geometry : GeometryGML
        geometry object to add the surfaces to
    id : int
        id of the building
    gC2D : list[list[float]]
        list of coordinates of ground surface in 2D, needs to be self closing
    gSH : float
        ground surface height
    bHAbs : float
        bulding height absolute (highest height of building in coordinate system)
    bWAbs : float
        building wall height absolute (lowest height of the roof in coordinate system)
    roofOrientation : int
        orientation of roof, refers to the index of the groundCoordinates list between 0
        and 3 (inclusive)
    roofHeight : float
        height of roof (relative height difference from lowest height of roof to highest
        height of roof)
    """
    # calculating wall surfaces
    # assuming the heading equals the side with the higher roof
    sH_pHalfRoof = bHAbs - (roofHeight / 3)
    highPoints = []
    lowPoints = []
    for i in range(4):
        crd = list(gC2D[i])
        nCrd = list(gC2D[i + 1])
        if i == roofOrientation:
            # wall on which the higher roof is ending
            coords = [
                crd + [gSH],
                crd + [bWAbs],
                nCrd + [bWAbs],
                nCrd + [gSH],
                crd + [gSH],
            ]
            highPoints = [crd, nCrd]
        elif i - roofOrientation == 2 or i - roofOrientation == -2:
            # wall on which the lower roof is ending
            coords = [
                crd + [gSH],
                crd + [bWAbs],
                nCrd + [bWAbs],
                nCrd + [gSH],
                crd + [gSH],
            ]
            lowPoints = [crd, nCrd]
        elif (roofOrientation + 1) % 4 - (i + 1) == -1:
            # first half height than full height
            center0 = cO.calc_center([crd, nCrd])
            coords = [
                crd + [gSH],
                crd + [bWAbs],
                center0 + [bHAbs],
                center0 + [sH_pHalfRoof],
                nCrd + [bWAbs],
                nCrd + [gSH],
                crd + [gSH],
            ]
        else:
            # first full height than half height
            center1 = cO.calc_center([crd, nCrd])
            coords = [
                crd + [gSH],
                crd + [bWAbs],
                center1 + [sH_pHalfRoof],
                center1 + [bHAbs],
                nCrd + [bWAbs],
                nCrd + [gSH],
                crd + [gSH],
            ]
        wallSurface = SurfaceGML(
            np.array(coords).flatten(),
            surface_type="WallSurface",
            surface_id=f"citydpc_wall_{id}_{i}",
        )
        geometry.add_surface(wallSurface)

    # for the wall between the two roof surfaces
    coords = [
        center0 + [sH_pHalfRoof],
        center0 + [bHAbs],
        center1 + [bHAbs],
        center1 + [sH_pHalfRoof],
        center0 + [sH_pHalfRoof],
    ]
    wallSurface = SurfaceGML(
        np.array(coords).flatten(),
        surface_type="WallSurface",
        surface_id=f"citydpc_wall_{id}_{i}_dp",
    )
    geometry.add_surface(wallSurface)
    # calculating roof surfaces
    # for roof with higher points
    roofCrds = [
        highPoints[0] + [bWAbs],
        center1 + [bHAbs],
        center0 + [bHAbs],
        highPoints[1] + [bWAbs],
        highPoints[0] + [bWAbs],
    ]
    roofSurface = SurfaceGML(
        np.array(roofCrds).flatten(),
        surface_type="RoofSurface",
        surface_id=f"citydpc_roof_{id}_1",
    )
    geometry.add_surface(roofSurface)
    # for roof with lower points
    roofCrds = [
        lowPoints[0] + [bWAbs],
        center0 + [sH_pHalfRoof],
        center1 + [sH_pHalfRoof],
        lowPoints[1] + [bWAbs],
        lowPoints[0] + [bWAbs],
    ]
    roofSurface = SurfaceGML(
        np.array(roofCrds).flatten(),
        surface_type="RoofSurface",
        surface_id=f"citydpc_roof_{id}_2",
    )
    geometry.add_surface(roofSurface)


def add_gabled_roof_and_walls(
    geometry: GeometryGML,
    id: int,
    gC2D: list[list[float]],
    gSH: float,
    bHAbs: float,
    bWAbs: float,
    roofOrientation: int,
):
    """create a gabled roof and walls from a list of coordinates

    Parameters
    ----------
    geometry : GeometryGML
        geometry object to add the surfaces to
    id : int
        id of the building
    gC2D : list[list[float]]
        list of coordinates of ground surface in 2D, needs to be self closing
    gSH : float
        ground surface height
    bHAbs : float
        bulding height absolute (highest height of building in coordinate system)
    bWAbs : float
        building wall height absolute (lowest height of the roof in coordinate system)
    roofOrientation : int
        orientation of roof, refers to the index of the groundCoordinates list between 0
        and 3 (inclusive)
    """
    # calculating wall surfaces
    # assuming the heading equals one of the 4 sided walls
    for i in range(4):
        crd = list(gC2D[i])
        nCrd = list(gC2D[i + 1])
        if (
            i == roofOrientation
            or i - roofOrientation == 2
            or i - roofOrientation == -2
        ):
            # square surfaces
            coords = [
                crd + [gSH],
                crd + [bWAbs],
                nCrd + [bWAbs],
                nCrd + [gSH],
                crd + [gSH],
            ]
        else:
            # surfaces with "5th", higher point
            coords = [
                crd + [gSH],
                crd + [bWAbs],
                cO.calc_center([crd, nCrd]) + [bHAbs],
                nCrd + [bWAbs],
                nCrd + [gSH],
                crd + [gSH],
            ]
        wallSurface = SurfaceGML(
            np.array(coords).flatten(),
            surface_type="WallSurface",
            surface_id=f"citydpc_wall_{id}_{i}",
        )
        geometry.add_surface(wallSurface)

    # calculating roof surfaces
    if roofOrientation % 2 == 0:
        # square first, 5th second
        c0 = cO.calc_center([list(gC2D[1]), list(gC2D[2])])
        c1 = cO.calc_center([list(gC2D[0]), list(gC2D[3])])
        roofCrds = [
            list(gC2D[0]) + [bWAbs],
            c1 + [bHAbs],
            c0 + [bHAbs],
            list(gC2D[1]) + [bWAbs],
            list(gC2D[0]) + [bWAbs],
        ]
        roofSurface0 = SurfaceGML(
            np.array(roofCrds).flatten(),
            surface_type="RoofSurface",
            surface_id=f"citydpc_roof_{id}_1",
        )
        roofCrds = [
            list(gC2D[2]) + [bWAbs],
            c0 + [bHAbs],
            c1 + [bHAbs],
            list(gC2D[3]) + [bWAbs],
            list(gC2D[2]) + [bWAbs],
        ]
        roofSurface1 = SurfaceGML(
            np.array(roofCrds).flatten(),
            surface_type="RoofSurface",
            surface_id=f"citydpc_roof_{id}_2",
        )
    else:
        # 5th first, square second
        c0 = cO.calc_center([list(gC2D[0]), list(gC2D[1])])
        c1 = cO.calc_center([list(gC2D[2]), list(gC2D[3])])
        roofCrds = [
            list(gC2D[1]) + [bWAbs],
            c0 + [bHAbs],
            c1 + [bHAbs],
            list(gC2D[2]) + [bWAbs],
            list(gC2D[1]) + [bWAbs],
        ]
        roofSurface0 = SurfaceGML(
            np.array(roofCrds).flatten(),
            surface_type="RoofSurface",
            surface_id=f"citydpc_roof_{id}_1",
        )
        roofCrds = [
            list(gC2D[3]) + [bWAbs],
            c1 + [bHAbs],
            c0 + [bHAbs],
            list(gC2D[0]) + [bWAbs],
            list(gC2D[3]) + [bWAbs],
        ]
        roofSurface1 = SurfaceGML(
            np.array(roofCrds).flatten(),
            surface_type="RoofSurface",
            surface_id=f"citydpc_roof_{id}_2",
        )
    geometry.add_surface(roofSurface0)
    geometry.add_surface(roofSurface1)


def add_hipped_roof_and_walls(
    geometry: GeometryGML,
    id: int,
    gC2D: list[list[float]],
    gSH: float,
    bHAbs: float,
    bWAbs: float,
):
    """create a hipped roof and walls from a list of coordinates
    roof ridge will be created alongside the longer side of the roof

    Parameters
    ----------
    geometry : GeometryGML
        geometry object to add the surfaces to
    id : int
        id of the building
    gC2D : list[list[float]]
        list of coordinates of ground surface in 2D, needs to be self closing
    gSH : float
        ground surface height
    bHAbs : float
        bulding height absolute (highest height of building in coordinate system)
    bWAbs : float
        building wall height absolute (lowest height of the roof in coordinate system)
    """
    for i in range(4):
        crd = list(gC2D[i])
        nCrd = list(gC2D[i + 1])
        coords = [
            crd + [gSH],
            crd + [bWAbs],
            nCrd + [bWAbs],
            nCrd + [gSH],
            crd + [gSH],
        ]
        wallSurface = SurfaceGML(
            np.array(coords).flatten(),
            surface_type="WallSurface",
            surface_id=f"citydpc_wall_{id}_{i}",
        )
        geometry.add_surface(wallSurface)

    # calculating the roof surfaces based the assumption that the gabel is
    # colinear to the longer side of the roof
    help_array = []
    for i in range(2):
        help_array.append(cO.distance(gC2D[i], gC2D[i + 1]))

    gabel_length = abs(help_array[0] - help_array[1])
    center_to_gabel = (max(help_array) - gabel_length) / 2

    # list of groundSurface coordinates but with (surfaceHeight + wallHeight) as
    # 3d coordinate
    sH_pWall_list = [list(i) + [bWAbs] for i in gC2D]
    if help_array[0] > help_array[1]:
        # longside first
        # getting some info about the heading of the roof
        shortCenter = cO.calc_center([list(gC2D[1]), list(gC2D[2])])
        gabel_vector = cO.normedDirectionVector(gC2D[2], gC2D[3])
        # corners of roof
        c0 = [
            shortCenter[0] + center_to_gabel * gabel_vector[0],
            shortCenter[1] + center_to_gabel * gabel_vector[1],
            bHAbs,
        ]
        c1 = [
            shortCenter[0] + (center_to_gabel + gabel_length) * gabel_vector[0],
            shortCenter[1] + (center_to_gabel + gabel_length) * gabel_vector[1],
            bHAbs,
        ]
    else:
        # short side first
        # getting some info about the heading of the roof
        shortCenter = cO.calc_center([list(gC2D[0]), list(gC2D[1])])
        gabel_vector = cO.normedDirectionVector(gC2D[1], gC2D[2])
        # corners of roof
        c0 = [
            shortCenter[0] + center_to_gabel * gabel_vector[0],
            shortCenter[1] + center_to_gabel * gabel_vector[1],
            bHAbs,
        ]
        c1 = [
            shortCenter[0] + (center_to_gabel + gabel_length) * gabel_vector[0],
            shortCenter[1] + (center_to_gabel + gabel_length) * gabel_vector[1],
            bHAbs,
        ]
    # roof surfaces
    for i in range(4):
        if help_array[0] > help_array[1]:
            if i == 0:
                standIn = [c1, c0]
            elif i == 1:
                standIn = [c0]
            elif i == 2:
                standIn = [c0, c1]
            else:
                standIn = [c1]
        else:
            if i == 0:
                standIn = [c0]
            elif i == 1:
                standIn = [c0, c1]
            elif i == 2:
                standIn = [c1]
            else:
                standIn = [c1, c0]
        roofCrds = [
            sH_pWall_list[i],
            *standIn,
            sH_pWall_list[i + 1],
            sH_pWall_list[i],
        ]
        roofSurface = SurfaceGML(
            np.array(roofCrds).flatten(),
            surface_type="RoofSurface",
            surface_id=f"citydpc_roof_{id}_{i}",
        )
        geometry.add_surface(roofSurface)


def add_pavilion_roof_and_walls(
    geometry: GeometryGML,
    id: int,
    gC2D: list[list[float]],
    gSH: float,
    bHAbs: float,
    bWAbs: float,
):
    """create a pavilion roof and walls from a list of coordinates

    Parameters
    ----------
    geometry : GeometryGML
        geometry object to add the surfaces to
    id : int
        id of the building
    gC2D : list[list[float]]
        list of coordinates of ground surface in 2D, needs to be self closing
    gSH : float
        ground surface height
    bHAbs : float
        bulding height absolute (highest height of building in coordinate system)
    bWAbs : float
        building wall height absolute (lowest height of the roof in coordinate system)
    """
    # calculating wall surfaces
    for i in range(len(gC2D) - 1):
        crd = list(gC2D[i])
        nCrd = list(gC2D[i + 1])
        coords = [
            crd + [gSH],
            crd + [bWAbs],
            nCrd + [bWAbs],
            nCrd + [gSH],
            crd + [gSH],
        ]
        wallSurface = SurfaceGML(
            np.array(coords).flatten(),
            surface_type="WallSurface",
            surface_id=f"citydpc_wall_{id}_{i}",
        )
        geometry.add_surface(wallSurface)

    # calculating roof surface
    roofCenter = cO.calc_center([list(i) for i in gC2D[:-1]])

    for i in range(4):
        roofCrds = [
            list(gC2D[i]) + [bWAbs],
            roofCenter + [bHAbs],
            list(gC2D[i + 1]) + [bWAbs],
            list(gC2D[i]) + [bWAbs],
        ]
        roofSurface = SurfaceGML(
            np.array(roofCrds).flatten(),
            surface_type="RoofSurface",
            surface_id=f"citydpc_roof_{id}_{i}",
        )
        geometry.add_surface(roofSurface)
