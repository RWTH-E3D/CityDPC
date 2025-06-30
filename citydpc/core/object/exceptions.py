class SurfaceWarning(UserWarning):
    """Base warning for the surface module."""
    pass


class SurfacePlanarityWarning(SurfaceWarning):
    """Warning issued when a surface is found to be non-planar."""
    pass
