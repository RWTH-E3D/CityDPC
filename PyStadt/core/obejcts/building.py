import numpy as np
import matplotlib.path as mplP

from PyStadt.core.obejcts.abstractBuilding import AbstractBuilding
from PyStadt.core.obejcts.buildingPart import BuildingPart



class Building(AbstractBuilding):
    """extends _AbstractBuilding class

    contains attributes and functions specific to Buildings

    Parameters
    ----------
    _AbstractBuilding : _type_

    """

    def __init__(self, id: str) -> None:
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


    def check_if_building_in_coordinates(self, borderCoordinates: list, 
                                         border: mplP.Path= None) -> bool:
        """checks if a building or any of the building parts of a building
        are located inside the given borderCoordiantes

        Parameters
        ----------
        borderCoordinates : list
            a 2D array of 2D coordinates
        border : mplP.Path, optional
            borderCoordinates as a matplotlib.path.Path, by default None

        Returns
        -------
        bool
            True if building of any building part is within borderCoordinates
        """
        if border == None:
            border = mplP.Path(np.array(borderCoordinates))

        # check for the geometry of the building itself
        res = self._check_if_within_border(borderCoordinates, border)
        if res:
            return True
        
        for buildingPart in self.get_building_parts():
            res = buildingPart._check_if_within_border(borderCoordinates, border)
            if res:
                return True
            
        return False
    
    def check_building_for_address(self, addressRestriciton: dict) -> bool:
        """checks if the address of the building matches the restriction

        Parameters
        ----------
        addressRestriciton : dict
            key: value pair of CoreAddress attribute and wanted value

        Returns
        -------
        bool
            returns True if all conditions are met for the building or at least one buildingPart
        """
        if self.address != None:
            res = self.address.check_address(addressRestriciton)
            if res:
                return True
        
        for buildingPart in self.get_building_parts():
            if buildingPart.address != None:
                res = buildingPart.address.check_address(addressRestriciton)
                if res:
                    return True
            
        return False