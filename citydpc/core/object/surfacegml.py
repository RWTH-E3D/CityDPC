# taken from the bs2023-MaSh branch of TEASER plus,
# last update: Mar 11, 2023 9:23pm GMT+0100, slightly modified
import numpy as np
from numpy import linalg as LA
from itertools import tee, chain

from citydpc.logger import logger
from . import SurfaceConfig
from citydpc.core.input import CHECK_IF_SURFACES_ARE_PLANAR


class SurfaceGML(object):
    """Class for calculating attributes of CityGML surfaces

    this class automatically calculates surface area using an algorithm for
    polygons with arbitrary number of points. The Surface orientation by
    analysing the normal vector (caution: the orientations are then set to
    TEASER orientation). The Surface tilt by analysing the normal vector.

    Parameters
    ----------

    gml_surface : list[float]
        list of gml points with srsDimension=3 the first 3 and the last 3
        entries must describe the same point in CityGML

    boundary : str
        Name of the boundary surface

    """

    def __init__(
        self,
        gml_surface: list[float],
        surface_id=None,
        surface_type=None,
        polygon_id=None,
    ):
        self.gml_surface = gml_surface
        self.surface_id = surface_id
        self.surface_type = surface_type
        self.polygon_id = polygon_id
        self.surface_area = None
        self.surface_orientation = None
        self.surface_tilt = None
        self.normal_uni = None

        useless_points = []
        split_surface = list(zip(*[iter(self.gml_surface)] * 3))
        for three_points in self.n_wise(split_surface, 3):
            useless_points.append(
                self.check_if_points_on_line(
                    np.asarray(three_points[1]),
                    np.asarray(three_points[0]),
                    np.asarray(three_points[2]),
                )
            )
        for element in split_surface:
            if element in useless_points:
                split_surface.remove(element)
        self.gml_surface = list(chain(*split_surface))
        if len(self.gml_surface) < 12:
            self.isSurface = False
            logger.warning(
                f"The surface {surface_id} - {polygon_id} has to few "
                + "individual coordinates"
            )
            return
        self.isSurface = True

        self.gml_surface_2array = np.reshape(self.gml_surface, (-1, 3))
        if CHECK_IF_SURFACES_ARE_PLANAR:
            if not self.is_planar():
                logger.warning(
                    f"Surface {self.surface_id} is not planar, "
                    + "the area and orientation might be incorrect."
                )
        self.normal_uni = self._calculate_unit_normal(
            self.gml_surface_2array[0],
            self.gml_surface_2array[1],
            self.gml_surface_2array[2],
        )

        self.creationDate = None

        self.surface_area = self.get_gml_area()
        self.surface_orientation = self.get_gml_orientation()
        self.surface_tilt = self.get_gml_tilt()

        if self.surface_type is None:
            if self.surface_tilt == 0.0 and self.surface_orientation == -2:
                self.surface_type = "GroundSurface"
            elif self.surface_tilt == 90.0:
                self.surface_type = "WallSurface"
            else:
                self.surface_type = "RoofSurface"

    def get_gml_area(self):
        """calc the area of a gml_surface defined by gml coordinates

        Surface needs to be planar

        Returns
        ----------
        surface_area : float
            returns the area of the surface
        """

        split_surface = list(zip(*[iter(self.gml_surface)] * 3))
        self.surface_area = self.poly_area(poly=split_surface)
        return self.surface_area

    def get_gml_tilt(self):
        """calc the tilt of a gml_surface defined by 4 or 5 gml coordinates

        Surface needs to be planar

        Returns
        ----------
        surface_tilt : float
            returns the orientation of the surface
        """

        cos_angle = abs(self.normal_uni[2])
        angle_rad = np.arccos(np.clip(cos_angle, -1.0, 1.0))

        self.surface_tilt = np.rad2deg(angle_rad)

        if self.surface_tilt == 180:
            self.surface_tilt = 0.0
        elif str(self.surface_tilt) == "nan":
            self.surface_tilt = None
        return self.surface_tilt

    def get_gml_orientation(self):
        """calc the orientation of a gml_surface defined by 4 or 5 gml
        coordinates

        Surface needs to be planar, the orientation returned is in TEASER
        coordinates

        Returns
        ----------
        surface_orientation : float
            returns the orientation of the surface
        """

        if np.isclose(self.normal_uni[2], 1.0):
            # surface is horizontal
            self.surface_orientation = -1
            return self.surface_orientation
        elif np.isclose(self.normal_uni[2], -1.0):
            # surface is horizontal but upside down
            self.surface_orientation = -2
            return self.surface_orientation

        azimuth_rad = np.arctan2(
            self.normal_uni[1], self.normal_uni[0]
        )
        azimuth_deg = np.rad2deg(azimuth_rad)

        self.surface_orientation = (450 - azimuth_deg) % 360
        return self.surface_orientation

    def poly_area(self, poly):
        """calculates the area of a polygon with arbitrary points

        Parameters
        ----------

        poly : list
            polygon as a list in srsDimension = 3

        Returns
        ----------

        area : float
            returns the area of a polygon
        """

        if len(poly) < 3:  # not a plane - no area
            return 0
        total = [0, 0, 0]
        length = len(poly)
        for i in range(length):
            vi1 = poly[i]
            vi2 = poly[(i + 1) % length]
            prod = np.cross(vi1, vi2)
            total[0] += prod[0]
            total[1] += prod[1]
            total[2] += prod[2]
        result = np.dot(total, self.normal_uni)
        return abs(result / 2)

    @staticmethod
    def n_wise(iterable, n=2):
        iterable_list = tee(iterable, n)
        for i in range(len(iterable_list)):
            for j in range(i):
                next(iterable_list[i], None)
        return zip(*iterable_list)

    @staticmethod
    def check_if_points_on_line(p, a, b):
        # normalized tangent vector
        d = np.divide(b - a, np.linalg.norm(b - a))

        # signed parallel distance components
        s = np.dot(a - p, d)
        t = np.dot(p - b, d)

        # clamped parallel distance
        h = np.maximum.reduce([s, t, 0])

        # perpendicular distance component
        c = np.cross(p - a, d)
        if (
            np.hypot(h, np.linalg.norm(c))
            <= SurfaceConfig.DISTANCE_BETWEEN_LINE_AND_POINT
        ):
            return tuple(p)
        else:
            return None

    @staticmethod
    def _calculate_unit_normal(p1, p2, p3):
        """
        Calculates the unit normal vector for a plane defined by three points
        using the cross product

        Parameters
        ----------
        p1, p2, p3 : array-like
            Points defining the plane, each should be a 3-element array-like

        Returns
        -------
        np.ndarray
            The unit normal vector as a 3-element NumPy array. Returns a
            zero vector if the points are co-linear.
        """
        v1 = np.asarray(p2) - np.asarray(p1)
        v2 = np.asarray(p3) - np.asarray(p1)

        cross_product = np.cross(v1, v2)

        norm = LA.norm(cross_product)

        # return zero vector if the points are co-linear
        if np.isclose(norm, 0):
            return np.array([0.0, 0.0, 0.0])

        return cross_product / norm

    def is_planar(self) -> bool:
        """Check if the surface is planar by checking if all points are on the
        same plane.

        Returns
        -------
        bool
            True if the surface is planar, False otherwise.
        """
        logger.debug(f"Checking if surface {self.surface_id} is planar.")
        if len(self.gml_surface_2array) <= 3:
            logger.warning(
                f"Surface {self.surface_id} has too few points to determine if"
                + " it is planar."
            )
            return False
        elif len(self.gml_surface_2array) <= 4:
            # first and last point must be the same
            # so in this case we have 3 points -> has to be planar
            return True
        else:
            # we want to calculate the normal vector for every combination of 3
            # points in order to check if they are all the same
            for i in range(len(self.gml_surface_2array) - 2):
                normal = self._calculate_unit_normal(
                    self.gml_surface_2array[i],
                    self.gml_surface_2array[i + 1],
                    self.gml_surface_2array[i + 2],
                )
                if np.all(normal != self.normal_uni, axis=0):
                    logger.debug(
                        f"Surface {self.surface_id} is not planar"
                    )
                    return False
        logger.debug(
            f"Surface {self.surface_id} is planar"
        )
        return True
