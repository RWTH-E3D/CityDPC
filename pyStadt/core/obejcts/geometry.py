from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyStadt.core.obejcts.surfacegml import SurfaceGML

from pyStadt.logger import logger


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
        self.pseudoSolids = []

    def add_surface(
        self, surface: SurfaceGML, pseudoSolidId: str = None, pseudoShellId: str = None
    ) -> None:
        """add a surface to the building

        Parameters
        ----------
        surface : SurfaceGML
            surface to be added
        pseudoSolidId : str, optional
            id of the pseudo solid to which the surface should be added, by default None
        pseudoShellId : str, optional
            id of the pseudo shell to which the surface should be added, by default None
        """
        if surface.surface_id in self.get_all_surface_ids():
            logger.error(
                f"Surface with id {surface.surface_id} already present on "
                + f"{self.parentID}"
            )
            return

        if pseudoSolidId is None:
            if (
                self.type == "MultiSurface"
                or self.type == "CompositeSurface"
                or self.type == "Solid"
            ):
                self.pseudoSolids[0].add_surface(surface, pseudoShellId)
                return
            else:
                for pseudoSolid in self.pseudoSolids:
                    if pseudoSolid.id == pseudoSolidId:
                        pseudoSolid.add_surface(surface, pseudoShellId)
                        return
        logger.error(
            f"unable to add surface {surface.surface_id} to geometry of{self.parentID}"
        )

    def add_surface_with_depthInfo(
        self, surface: SurfaceGML, depthInfo: list[int]
    ) -> None:
        """add a surface to the building

        Parameters
        ----------
        surface : SurfaceGML
            surface to be added
        depthInfo : list[int]
            list of depth information for the surface
        """
        if surface.surface_id in self.get_all_surface_ids():
            logger.error(
                f"Surface with id {surface.surface_id} already present on "
                + f"{self.parentID}"
            )
            return

        if self.type == "MultiSurface" or self.type == "CompositeSurface":
            pSolidIndex = 0
            pShellIndex = 0
        elif self.type == "Solid":
            pSolidIndex = 0
            pShellIndex = depthInfo[0]
        elif self.type == "MultiSolid" or self.type == "CompositeSolid":
            pSolidIndex = depthInfo[0]
            pShellIndex = depthInfo[1]
        else:
            logger.error(
                f"unable to add surface {surface.surface_id} to geometry of type "
                + f"{self.type} of {self.parentID}"
            )
            return

        self.pseudoSolids[pSolidIndex].pseudoShells[pShellIndex].add_surface(surface)

    def get_all_surface_ids(self) -> list[str]:
        """returns a list of all surface ids of the geometry

        Returns
        -------
        list[str]
            list of all surface ids of the geometry
        """
        return [
            j.surface_id
            for pseudoSolid in self.pseudoSolids
            for pseudoShells in pseudoSolid.pseudoShells
            for j in pseudoShells.surfaces
        ]

    def get_surfaces(
        self,
        surfaceTypes: list[str] = [],
        pseudoSolidIds: list[str] = [],
        pseudoShellIds: list[str] = [],
    ) -> list[SurfaceGML]:
        """returns a list of all surfaces of the geometry matching the given constraints

        Parameters
        ----------
        surfaceTypes : list[str], optional
            list of surface type strings, by default None
        pseudoSolidIds : list[str], optional
            list of pseudo solid ids, by default []
        pseudoShellIds : list[str], optional
            list of pseudo shell ids, by default []

        Returns
        -------
        list[SurfaceGML]
            list of surfaces matching the given constraints
        """
        surfaces = []
        for pseudoSolid in self.pseudoSolids:
            if pseudoSolidIds != [] and pseudoSolid.id not in pseudoSolidIds:
                continue
            for pseudoShell in pseudoSolid.pseudoShells:
                if pseudoShellIds != [] and pseudoShell.id not in pseudoShellIds:
                    continue
                for surface in pseudoShell.surfaces:
                    if surfaceTypes == [] or surface.surface_type in surfaceTypes:
                        surfaces.append(surface)

        return surfaces

    def get_surfaces_with_indices(
        self, pSolidIndex: int, pShellIndex: int, surfaceTypes: list[str] = []
    ) -> list[SurfaceGML]:
        """returns a list of all surfaces of the geometry matching the given constraints

        Parameters
        ----------
        pSolidIndex : int
            index of the pseudo solid
        pShellIndex : int
            index of the pseudo shell
        surfaceTypes : list[str], optional
            list of surface type strings, by default None

        Returns
        -------
        list[SurfaceGML]
            list of surfaces matching the given constraints
        """
        surfaces = []
        if pSolidIndex >= len(self.pseudoSolids):
            logger.warning(
                f"pseudo solid index {pSolidIndex} out of range for geometry of "
                + f"{self.parentID}"
            )
            return surfaces
        elif pShellIndex >= len(self.pseudoSolids[pSolidIndex].pseudoShells):
            logger.warning(
                f"pseudo shell index {pShellIndex} out of range for pseudo solid "
                + f"index {pSolidIndex} of geometry of {self.parentID}"
            )
            return surfaces
        for surface in (
            self.pseudoSolids[pSolidIndex].pseudoShells[pShellIndex].surfaces
        ):
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
        for pseudoSolid in self.pseudoSolids:
            for pseudoShell in pseudoSolid.pseudoShells:
                for surface in pseudoShell.surfaces:
                    if surface.surface_id == surface_id:
                        return surface

        logger.error(
            f"surface with id {surface_id} not found on geometry of {self.parentID}"
        )
        return None

    def create_pseudoSolid(self, id: str) -> int:
        """adds a pseudo solid to the geometry

        Parameters
        ----------
        id : str
            id of the pseudo solid

        Returns
        -------
        int
            returns the index of the pseudo solid
        """
        if id in [i.id for i in self.pseudoSolids]:
            logger.error(
                f"pseudo solid with id {id} already present on geometry of "
                + f"{self.parentID}"
            )
            return
        self.pseudoSolids.append(_PseudoSolid(id))
        return len(self.pseudoSolids) - 1


class _PseudoSolid:
    def __init__(self, id: str) -> None:
        """pseudo solid class for storing pseudo shells

        Parameters
        ----------
        id : str
            id of the pseudo solid
        """
        self.id = id
        self.pseudoShells = []

    def create_pseudoShell(self, shellId: str) -> int:
        """adds a pseudo shell to the pseudo solid

        Parameters
        ----------
        shellId : str
            id of the pseudo shell

        Returns
        -------
        int
            returns the index of the pseudo shell
        """
        if shellId in [i.id for i in self.pseudoShells]:
            logger.error(
                f"pseudo shell with id {shellId} already present on pseudo solid "
                + f"{self.id}"
            )
            return
        self.pseudoShells.append(_PseudoShell(shellId))
        return len(self.pseudoShells) - 1

    def add_surface(self, surface: SurfaceGML, pseudoShellId: str = None) -> None:
        """adds a surface to the pseudo solid

        Parameters
        ----------
        surface : SurfaceGML
            surface to be added
        pseudoShellId : str, optional
            id of the pseudo shell, by default None
        """
        if pseudoShellId is None:
            self.pseudoShells[0].add_surface(surface)
            return
        for shell in self.pseudoShells:
            if shell.id == pseudoShellId:
                shell.add_surface(surface)
                return
        logger.error(
            f"pseudo shell with id {pseudoShellId} not found on pseudo solid {self.id}"
        )


class _PseudoShell:
    def __init__(self, id: str) -> None:
        """pseudo shell class for storing surfaces

        Parameters
        ----------
        id : str
            id of the pseudo shell
        """
        self.id = id
        self.surfaces = []

    def add_surface(self, surface: SurfaceGML) -> None:
        """adds a surface to the pseudo shell"""
        self.surfaces.append(surface)
