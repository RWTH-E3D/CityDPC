from pyStadt.core.obejcts.abstractBuilding import AbstractBuilding
from pyStadt.core.obejcts.buildingPart import BuildingPart


class Building(AbstractBuilding):
    """extends AbstractBuilding class

    contains attributes and functions specific to Buildings

    """

    def __init__(self, id: str) -> None:
        """initialize new building

        Parameters
        ----------
        id : str
            gml:id of Building
        """
        super().__init__(id)
        self.building_parts = []
        self.is_building_part = False

    def has_building_parts(self) -> bool:
        """checks if the building has building parts

        Returns
        -------
        bool
            true if building has building parts
        """
        return self.building_parts != []

    def get_building_parts(self) -> list[BuildingPart]:
        """return a list of building parts of building

        Returns
        -------
        list[BuildingPart]

        """
        return self.building_parts

    def get_building_part_ids(self) -> list:
        """returns list of building part ids of given building

        Returns
        -------
        list
            all building part ids of building
        """
        return [x.id for x in self.building_parts]
