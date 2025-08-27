class SurfaceWarning(UserWarning):
    """Base warning for the surface module."""

    pass


class SurfacePlanarityWarning(SurfaceWarning):
    """Warning issued when a surface is found to be non-planar."""

    pass


class SurfaceCoorNumberWarning(SurfaceWarning):
    """Warning issued when a surface has to few individual coordinates"""

    pass


class SurfaceNotAddedToBuildingWarning(SurfaceWarning):
    """Warning issued when a surface is not being added to a building(part)"""

    pass


class CityGMLInputWarning(UserWarning):
    """Warning issued when there is an issue with the CityGML input."""

    pass


class SurfaceSplitDueToMultipleSurfaceMembers(CityGMLInputWarning):
    """Warning issued when a surface is split due to multiple surfaceMembers"""

    pass
