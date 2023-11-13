from pyStadt.core.obejcts.address import CoreAddress


class AbstractBuilding:
    """contains all methods and properties that are use by
    buildings and building parts"""

    def __init__(self, id: str) -> None:
        """initialize new AbstractBuilding

        Parameters
        ----------
        id : str
            gml:id of AbstractBuilding
        """
        self.gml_id = id
        self.walls = {}
        self.roofs = {}
        self.grounds = {}
        self.closure = {}
        self.roof_volume = None
        self.lod = None
        self.is_building_part = None

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
        if (
            self.roofs != {}
            and self.grounds != {}
            and (self.walls != {} or self.closure != {})
        ):
            return True
        else:
            return False
