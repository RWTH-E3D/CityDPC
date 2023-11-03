from pyStadt.core.obejcts.abstractBuilding import AbstractBuilding

class BuildingPart(AbstractBuilding):
    """extends _AbstractBuilding class

    contains attributes and functions specific to Buildings

    """

    def __init__(self, id: str, parent_id: str) -> None:
        """_summary_

        Parameters
        ----------
        id : str
            gml:id of BuildingPart
        parent_id : str
            gml:id of parent Building
        """
        super().__init__(id)
        self.parent_gml_id = parent_id
        self.is_building_part = True
