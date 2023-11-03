from PyStadt.core.obejcts.abstractBuilding import AbstractBuilding

class BuildingPart(AbstractBuilding):
    """extends _AbstractBuilding class

    contains attributes and functions specific to Buildings

    Parameters
    ----------
    _AbstractBuilding : _type_

    """

    def __init__(self, id: str, parent_id: str) -> None:
        super().__init__(id)
        self.parent_gml_id = parent_id
        self.is_building_part = True
