# taken from the bs2023-MaSh branch of TEASER plus,
# last update: Mar 11, 2023 9:23pm GMT+0100, slightly modified
import numpy as np
from numpy import linalg as LA
from itertools import tee, chain

from pyStadt.logger import logger


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
            logger.error(
                f"WARNING! The surface {surface_id} - {polygon_id} has to few "
                + "individual coordinates"
            )
            return
        self.isSurface = True

        self.gml_surface_2array = np.reshape(self.gml_surface, (-1, 3))
        self.creationDate = None

        self.surface_area = self.get_gml_area()
        self.surface_orientation = self.get_gml_orientation()
        self.surface_tilt = self.get_gml_tilt()

        if self.surface_type is None:
            if self.surface_tilt == 0.0:
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

        gml_surface = np.array(self.gml_surface)
        gml1 = gml_surface[0:3]
        gml2 = gml_surface[3:6]
        gml3 = gml_surface[6:9]

        vektor_1 = gml2 - gml1
        vektor_2 = gml3 - gml1

        normal_1 = np.cross(vektor_1, vektor_2)
        z_axis = np.array([0, 0, 1])

        self.surface_tilt = (
            np.arccos(np.dot(normal_1, z_axis) / (LA.norm(z_axis) * LA.norm(normal_1)))
            * 360
            / (2 * np.pi)
        )

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

        gml_surface = np.array(self.gml_surface)
        gml1 = gml_surface[0:3]
        gml2 = gml_surface[3:6]
        gml3 = gml_surface[6:9]
        gml4 = gml_surface[9:12]
        if len(gml_surface) > 12:
            vektor_1 = gml2 - gml1
            vektor_2 = gml4 - gml1
        else:
            vektor_1 = gml2 - gml1
            vektor_2 = gml3 - gml1

        normal_1 = np.cross(vektor_1, vektor_2)
        normal_uni = normal_1 / LA.norm(normal_1)

        self.normal_uni = normal_uni

        phi = None
        if normal_uni[0] > 0:
            phi = np.arctan(normal_uni[1] / normal_uni[0])
        elif normal_uni[0] < 0 <= normal_uni[1]:
            phi = np.arctan(normal_uni[1] / normal_uni[0]) + np.pi
        elif normal_uni[0] < 0 > normal_uni[1]:
            phi = np.arctan(normal_uni[1] / normal_uni[0]) - np.pi
        elif normal_uni[0] == 0 < normal_uni[1]:
            phi = np.pi / 2
        elif normal_uni[0] == 0 > normal_uni[1]:
            phi = -np.pi / 2

        if phi is None:
            pass
        elif phi < 0:
            self.surface_orientation = (phi + 2 * np.pi) * 360 / (2 * np.pi)
        else:
            self.surface_orientation = phi * 360 / (2 * np.pi)

        if self.surface_orientation is None:
            pass
        elif 0 <= self.surface_orientation <= 90:
            self.surface_orientation = 90 - self.surface_orientation
        else:
            self.surface_orientation = 450 - self.surface_orientation

        if normal_uni[2] == -1:
            self.surface_orientation = -2
        elif normal_uni[2] == 1:
            self.surface_orientation = -1
        return self.surface_orientation

    def unit_normal(self, a, b, c):
        """calculates the unit normal vector of a surface described by 3 points

        Parameters
        ----------

        a : float
            point 1
        b : float
            point 2
        c : float
            point 3

        Returns
        ----------

        unit_normal : list
            unit normal vector as a list

        """
        x = np.linalg.det([[1, a[1], a[2]], [1, b[1], b[2]], [1, c[1], c[2]]])
        y = np.linalg.det([[a[0], 1, a[2]], [b[0], 1, b[2]], [c[0], 1, c[2]]])
        z = np.linalg.det([[a[0], a[1], 1], [b[0], b[1], 1], [c[0], c[1], 1]])
        magnitude = (x**2 + y**2 + z**2) ** 0.5
        return x / magnitude, y / magnitude, z / magnitude

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
        result = np.dot(total, self.unit_normal(poly[0], poly[1], poly[2]))
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
        if np.hypot(h, np.linalg.norm(c)) <= 0.01:
            return tuple(p)
        else:
            return None
