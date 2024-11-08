from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from citydpc.dataset import Dataset
    from citydpc.core.obejct.surfacegml import SurfaceGML


def update_min_max_from_surface(
    minList: list[float], maxList: list[float], surface: SurfaceGML
):
    """updates the lists of minimums and maximums based for surface object

    Parameters
    ----------
    minList : list[float]
        list of minimums
    maxList : list[float]
        list of maximums
    surface : object
        SurfaceGML object

    Returns
    -------
    set
        set of updated miniums and maximums
    """
    for point in surface.gml_surface_2array:
        for i, coordinate in enumerate(point):
            if coordinate < minList[i]:
                minList[i] = float(coordinate)
            elif coordinate > maxList[i]:
                maxList[i] = float(coordinate)
    return (minList, maxList)


def update_dataset_min_max_from_surface(dataset: Dataset, surface: SurfaceGML):
    """updates the min and max values of the dataset based on the new surface

    Parameters
    ----------
    dataset : Dataset
        cityDPC dataset object
    surface : SurfaceGML
        SurfaceGML object
    """
    dataset._minimum, dataset._maximum = update_min_max_from_surface(
        dataset._minimum, dataset._maximum, surface
    )


def update_min_max_from_min_max(eMinList: list[float], eMaxList: list[float], nMinList: list[float], nMaxList: list[float]):
    """updates the min and max values of existing min and max list based
    on new min and max list

    Parameters
    ----------

    eMinList : list[float]
        list of existing minimums
    eMaxList : list[float]
        list of exisiting maximums
    nMinList : list[float]
        list of new minimums
    nMaxList : list[float]
        list of new maximums
    
    Returns
    -------
    set
        set of updated miniums and maximums
    """
    for i in range(3):
        if nMinList[i] < eMinList[i]:
            eMinList[i] = nMinList[i]
        if nMaxList[i] > eMaxList[i]:
            eMaxList[i] = nMaxList[i]
    return (eMinList, eMaxList)


def update_dataset_min_max_from_min_max(
    dataset: Dataset, minList: list[float], maxList: list[float]
):
    """updates the min and max values of the dataset based on min and max list

    Parameters
    ----------
    dataset : Dataset
        cityDPC dataset object
    minList : list[float]
        list of minimums
    maxList : list[float]
        list of maximums
    """
    dataset._minimum, dataset._maximum = update_min_max_from_min_max(
        dataset._minimum, dataset._maximum, minList, maxList
    )
