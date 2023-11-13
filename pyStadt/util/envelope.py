from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyStadt.dataset import Dataset
    from pyStadt.core.obejcts.surfacegml import SurfaceGML


def update_min_max(dataset: Dataset, surface: SurfaceGML):
    """updates the min and max values for the dataset based on the new surface

    Parameters
    ----------
    surface : object
        SurfaceGML object
    """
    for point in surface.gml_surface_2array:
        for i, coordinate in enumerate(point):
            if coordinate < dataset._minimum[i]:
                dataset._minimum[i] = coordinate
            elif coordinate > dataset._maximum[i]:
                dataset._maximum[i] = coordinate
