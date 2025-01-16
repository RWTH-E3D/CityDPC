from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from citydpc.core.object.surfacegml import SurfaceGML

from citydpc.logger import logger


class GeometryGML:
    def __init__(self, type: str, parentID: str, lod: int = None) -> None:
        """representation of a CityGML geometry

        Parameters
        ----------
        type : str
            one of the following types:
            - MultiSurface
            - CompositeSurface
            - Solid
            - MultiSolid
            - CompositeSolid
        parentID : str
            id of the parent building(part)
        lod : int, optional
            Level of Detail of geometry, by default None
        """
        self.type = type
        self.parentID = parentID
        self.lod = lod
        self.surfaces = []
        self.solids = {}

    def add_surface(
        self,
        surface: SurfaceGML,
        solidID: str = None,
    ) -> None:
        """add a surface to the building

        Parameters
        ----------
        surface : SurfaceGML
            surface to be added
        """
        if (
            surface.surface_id is not None
            and surface.surface_id in self.get_all_surface_ids()
        ):
            logger.error(
                f"Surface with id {surface.surface_id} already present on "
                + f"{self.parentID}"
            )
            return

        self.surfaces.append(surface)

        if solidID is None:
            return
        elif (
            self.type == "Solid"
            or self.type == "CompositeSolid"
            or self.type == "MultiSolid"
        ):
            if solidID not in self.solids:
                self.solids[solidID] = []
            self.solids[solidID].append(surface)
        else:
            logger.error(f"surface type {self.type} does not support solid ids")

    def get_all_surface_ids(self) -> list[str]:
        """returns a list of all surface ids of the geometry

        Returns
        -------
        list[str]
            list of all surface ids of the geometry
        """
        return [surface.surface_id for surface in self.surfaces]

    def get_surfaces(
        self,
        surfaceTypes: list[str] = [],
    ) -> list[SurfaceGML]:
        """returns a list of all surfaces of the geometry matching the given constraints

        Parameters
        ----------
        surfaceTypes : list[str], optional
            list of surface type strings, by default None

        Returns
        -------
        list[SurfaceGML]
            list of surfaces matching the given constraints
        """
        surfaces = []
        for surface in self.surfaces:
            if surfaceTypes == [] or surface.surface_type in surfaceTypes:
                surfaces.append(surface)

        return surfaces

    def get_surface(self, surface_id: str) -> SurfaceGML | None:
        """returns a surface by its id

        Parameters
        ----------
        surface_id : str
            id of the surface to be returned

        Returns
        -------
        SurfaceGML
            surface with the given id
        """
        for surface in self.surfaces:
            if surface.surface_id == surface_id:
                return surface

        logger.error(
            f"surface with id {surface_id} not found on geometry of {self.parentID}"
        )
        return None
