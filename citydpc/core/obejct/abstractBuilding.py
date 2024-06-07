from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from citydpc.core.obejct.surfacegml import SurfaceGML
    from citydpc.core.obejct.geometry import GeometryGML

from citydpc.core.obejct.address import CoreAddress
from citydpc.logger import logger

import numpy as np
from scipy.spatial import ConvexHull


class AbstractBuilding:
    """contains all methods and properties that are use by
    buildings and building parts"""

    def __init__(self, id: str) -> None:
        """initialize new AbstractBuilding

        Parameters
        ----------
        id : str
            gml:id of AbstractBuilding
        """
        self.gml_id = id
        self.geometries = {}
        self.walls = {}
        self.roofs = {}
        self.grounds = {}
        self.closures = {}
        self.roof_volume = None
        self.roof_height = None
        self.lod = None
        self.is_building_part = None
        self.allWalls = None
        self.freeWalls = None

        self.creationDate = None
        self.extRef_infromationsSystem = None
        self.extRef_objName = None

        self.genericStrings = {}

        self.function = None
        self.usage = None
        self.yearOfConstruction = None
        self.roofType = None
        self.measuredHeight = None
        self.storeysAboveGround = None
        self.storeyHeightsAboveGround = None
        self.storeysBelowGround = None
        self.storeyHeightsBelowGround = None

        self.terrainIntersections = None

        self.address = CoreAddress()

    def has_3Dgeometry(self) -> bool:
        """checks if abstractBuilding has geometry

        to return true the building needs to have at least one roof geometry
        one ground geometry and either a wall or closure geomety

        Returns
        -------
        bool
            True:  building has atleast 3D geometry
            False: building does not have any 3D geometry
        """
        for geometry in self.get_geometries():
            if (
                geometry is not None
                and geometry.get_surfaces(["RoofSurface"]) != []
                and geometry.get_surfaces(["GroundSurface"]) != []
                and (
                    geometry.get_surfaces(["WallSurface"]) != []
                    or geometry.get_surfaces(["ClosureSurface"]) != []
                )
            ):
                return True
        return False

    def add_geometry(self, geometry: GeometryGML, geomKey: str = None) -> str:
        """add a geometry to the building

        Parameters
        ----------
        geometry : GeometryGML
            geometry to be added
        geomKey : str, optional
            key to use for the geometry, by default None

        Returns
        -------
        str
            key of the added geometry
        """
        if geomKey is None:
            geomKey = str(len(self.geometries))
        elif geomKey in self.geometries.keys():
            logger.error(
                f"Building {self.gml_id} already has a geometry with key {geomKey}, "
                + "cannot add geometry"
            )
            return None
        self.geometries[geomKey] = geometry
        return geomKey

    def get_geometry(self, geomKey: str) -> GeometryGML:
        """returns the geometry with the given key

        Parameters
        ----------
        geomKey : str
            key of the geometry to return

        Returns
        -------
        GeometryGML
            geometry with the given key
        """
        if geomKey in self.geometries.keys():
            return self.geometries[geomKey]
        else:
            logger.error(
                f"Building {self.gml_id} has no geometry '{geomKey}, "
                + "cannot return geometry"
            )
            return None

    def remove_geometry(self, geomKey: str) -> None:
        """removes a geometry from the building

        Parameters
        ----------
        geomKey : str
            key of the geometry to remove
        """
        if geomKey in self.geometries.keys():
            del self.geometries[geomKey]

    def get_surfaces(
        self,
        surfaceTypes: list[str] = [],
        geometryKeys: list[str] = [],
    ) -> list[SurfaceGML]:
        """returns a list of all surfaces of the geometry matching the given constraints

        Parameters
        ----------
        surfaceTypes : list[str], optional
            list of surface type strings, by default []
        geometryKeys : list[str], optional
            list of geometry keys, by default []

        Returns
        -------
        list[SurfaceGML]
            list of surfaces matching the given constraints
        """
        surfaces = []
        for key, geometry in self.geometries.items():
            if geometryKeys != [] and key not in geometryKeys:
                continue
            for surface in geometry.surfaces:
                if surfaceTypes == [] or surface.surface_type in surfaceTypes:
                    surfaces.append(surface)

        return surfaces

    def get_geometries(self, geometryKeys: list[str] = []) -> list[GeometryGML]:
        """returns a list of all geometries matching the given constraints

        Parameters
        ----------
        geometryKeys : list[str], optional
            list of geometry keys, by default []

        Returns
        -------
        list[GeometryGML]
        list of geometries matching the given constraints
        """
        geometries = []
        for key, geometry in self.geometries.items():
            if geometryKeys != [] and key not in geometryKeys:
                continue
            geometries.append(geometry)

        return geometries

    def _calc_roof_volume(self) -> None:
        """calculates the roof volume of the building"""
        roofSurfaces = self.get_surfaces(["RoofSurface"])
        if roofSurfaces != []:
            self.roof_volume = 0
            for roof_surface in roofSurfaces:
                if np.all(
                    roof_surface.gml_surface_2array
                    == roof_surface.gml_surface_2array[0, :],
                    axis=0,
                )[2]:
                    # roof surface is flat -> no volume to calculate
                    continue
                minimum_roof_height = np.min(roof_surface.gml_surface_2array, axis=0)[2]
                maximum_roof_height = np.max(roof_surface.gml_surface_2array, axis=0)[2]
                closing_points = np.array(roof_surface.gml_surface_2array, copy=True)
                closing_points[:, 2] = minimum_roof_height
                closed = np.concatenate(
                    [closing_points, roof_surface.gml_surface_2array]
                )
                hull = ConvexHull(closed)
                self.roof_volume += round(hull.volume, 3)
                if (
                    self.roof_height is None
                    or maximum_roof_height - minimum_roof_height > self.roof_height
                ):
                    self.roof_height = maximum_roof_height - minimum_roof_height

    def _warn_invalid_surface(self, surfaceID: str) -> None:
        """logs warning about invalid surface

        Parameters
        ----------
        surfaceID : str
            gml:id of incorrect Surface
        """
        if self.is_building_part:
            logger.warning(
                f"Surface {surfaceID} of BuildingPart {self.gml_id} of Building "
                + f"{self.parent_gml_id} is not a valid surface"
            )
        else:
            logger.warning(
                f"Surface {surfaceID} of Building {self.gml_id} is not a valid surface"
            )

    def create_legacy_surface_dicts(self) -> None:
        """creates the legacy surface dictionaries"""
        dictNames = {
            "walls": "WallSurface",
            "roofs": "RoofSurface",
            "grounds": "GroundSurface",
            "closures": "ClosureSurface",
        }
        for dictName, surfaceType in dictNames.items():
            surfaces = self.get_surfaces([surfaceType])
            if surfaces != []:
                setattr(self, dictName, {})
                for surface in surfaces:
                    getattr(self, dictName)[surface.surface_id] = surface
