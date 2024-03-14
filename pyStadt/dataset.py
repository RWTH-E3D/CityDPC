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

    def __init__(self, name: str = None, defaultScale=True) -> None:
        self.name = name
        self._files = []
        self.srsName = None
        self.buildings = {}
        self.otherCityObjectMembers = []
        self.party_walls = None

        self._minimum = [math.inf, math.inf, math.inf]
        self._maximum = [-math.inf, -math.inf, -math.inf]
        if defaultScale:
            self.transform = {
                "scale": [1, 1, 1],
                "translate": [0, 0, 0],
            }
        else:
            self.transform = {}

        logger.warning(
            "The dictionaries 'walls', 'roofs', 'grounds' and 'closures' "
            + "buildings and buildingParts will be deprecated. Use "
            + "'get_surfaces' instead. "
            + "(e.g. get_surfaces(surfaceTypes=['WallSurface']))"
        )

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


def join_datasets(
    left: Dataset,
    right: Dataset,
    operation: str,
) -> Dataset:
    """join two datasets

    Parameters
    ----------
    left : Dataset
        left dataset
    right : Dataset
        right dataset
    operation : str
        operation to be performed on the datasets
        one of "left", "leftExcludingInner", "inner", "outer", "outerExcludingInner"

    Returns
    -------
    Dataset
        joined dataset
    """
    possibleOperations = [
        "left",
        "leftExcludingInner",
        "inner",
        "outer",
        "outerExcludingInner",
    ]

    if operation not in possibleOperations:
        raise ValueError(f"operation must be one of {possibleOperations}")
    elif operation == "left":
        return left.copy()
    elif operation == "leftExcludingInner":
        leftCopy = left.copy()
        for building in right.get_building_list():
            if building.id in leftCopy.buildings:
                del leftCopy.buildings[building.id]
        return leftCopy
    elif operation in ["inner", "outer", "outerExcludingInner"]:
        # check that the datasets have the same srsName and transformation
        if left.srsName != right.srsName:
            raise ValueError("The datasets have different srsNames")
        elif left.transform != right.transform:
            # TODO: implement auto transformation
            raise ValueError("The datasets have different transformations")

        if operation == "inner":
            leftCopy = left.copy()
            for building in left.get_building_list():
                if building.id not in right.buildings:
                    del leftCopy.buildings[building.id]
            return leftCopy
        elif operation == "outer":
            leftCopy = left.copy()
            for building in right.get_building_list():
                if building.id not in leftCopy.buildings:
                    leftCopy.buildings[building.id] = building.copy()
                else:
                    logger.warning(
                        f"Building with id {building.id} already exists in left dataset"
                    )
            return leftCopy
        elif operation == "outerExcludingInner":
            leftCopy = left.copy()
            for building in right.get_building_list():
                if building.id not in leftCopy.buildings:
                    leftCopy.buildings[building.id] = building.copy()
                else:
                    del leftCopy.buildings[building.id]
            return leftCopy
