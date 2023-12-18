from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyStadt.core.obejcts.building import Building

from pyStadt.logger import logger

import math


class Dataset:
    """
    class to input single or multiple files and gather basic information on them

    """

    def __init__(self, name: str = None) -> None:
        self.name = name
        self._files = []
        self.srsName = None
        self.buildings = {}
        self.otherCityObjectMembers = []
        self.party_walls = None

        self._minimum = [math.inf, math.inf, math.inf]
        self._maximum = [-math.inf, -math.inf, -math.inf]
        self.transform = {}

        logger.warning("The dictionaries 'walls', 'roofs', 'grounds' and 'closures' "
                       + "buildings and buildingParts will be deprecated. Use "
                       + "'get_surfaces' instead. "
                       + "(e.g. get_surfaces(surfaceTypes=['WallSurface']))")

    def size(self) -> int:
        """return the number of buildings within the dataset

        Returns
        -------
        int
            number of buildings within the dataset
        """
        return len(self.buildings)

    def get_building_list(self) -> list[Building]:
        """returns a list of all buildings in dataset

        Returns
        -------
        list
            list of all buildings in dataset
        """
        return list(self.buildings.values())
