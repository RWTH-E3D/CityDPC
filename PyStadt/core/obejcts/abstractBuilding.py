import lxml.etree as ET
import numpy as np
import matplotlib.path as mplP

from PyStadt.tools.cityATB import _border_check
from PyStadt.core.obejcts.address import CoreAddress

class AbstractBuilding():
    """contains all methods and properties that are use by buildings and building parts
    """

    def __init__(self, id: str) -> None:
        self.gml_id = id
        self.walls = {}
        self.roofs = {}
        self.grounds = {}
        self.closure = {}
        self.roof_volume = None
        self.lod = None

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
        self.storeysBelowGround = None

        self.terrainIntersections = None

        self.address = CoreAddress()
        

    def has_3Dgeometry(self) -> bool:
        """checks if abstractBuilding has geometry

        to return true the building needs to have at least one roof geometry
        one ground geometry and either a wall or closure geomety

        Returns
        -------
        bool
            
        """
        if self.roofs != {} and self.grounds != {} and (self.walls != {} or self.closure != {}):
            return True
        else:
            return False
        


    def _check_if_within_border(self, borderCoordinates: list, \
                                border: mplP.Path) -> bool | None:
        """checks if a AbstractBuilding is located within the borderCoordinates

        Parameters
        ----------
        borderCoordinates : list
            list of 2D border coordinates

        border : mplP.Path
            matplotlib.path Path of given coordinates

        Returns
        -------
        bool | None
            True:  building is located inside the border coordintes
            False: building is located outside the border coordinates
            None:  building has no ground reference
        """
        
        if self.grounds != {}:
            selected_surface = list(self.grounds.values())
        elif self.roofs != {}:
            selected_surface = list(self.roofs.values())
        else:
            return None
        
        for surface in selected_surface:
            two_2array = np.delete(surface.gml_surface_2array, -1, 1)
            res = _border_check(border, borderCoordinates, two_2array)
            if res:
                return True
        return False

