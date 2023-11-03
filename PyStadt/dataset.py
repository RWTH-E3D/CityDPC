from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyStadt.core.obejcts.building import Building

import math

from PyStadt.core.input.citygmlInput import load_buildings_from_xml_file
from PyStadt.core.output.citygmlOutput import write_citygml_file


class Dataset():
    """
    class to input single or multiple files and gather basic information on them

    """

    def __init__(self, name: str = None) -> None:
        self.name = name
        self._files = []
        self.srsName = None
        self.buildings = {}
        self.otherCityObjectMembers = []
        self.party_walls = None

        self._minimum = [math.inf, math.inf, math.inf]
        self._maximum = [-math.inf, -math.inf, -math.inf]

    def size(self) -> int:
        """return the number of buildings within the dataset

        Returns
        -------
        int
            number of buildings within the dataset
        """
        return len(self.buildings) 

    def get_building_list(self) -> list[Building]:
        """returns a list of all buildings in dataset

        Returns
        -------
        list
            list of all buildings in dataset
        """
        return list(self.buildings.values())
    
    def add_buildings_from_xml_file(self, filepath: str, borderCoordinates: list= None,
                                    addressRestriciton: dict= None) -> None:
        """adds buildings from filepath to the dataset

        Parameters
        ----------
        filepath : str
            path to .gml or .xml CityGML file
        borderCoordinates : list, optional
            list of coordinates ([x0, y0], [x1, y1], ..) in fileCRS to restrict the dataset,
            by default None
        addressRestriciton : dict, optional
            dictionary of address values to restrict the dataset, by default None
        """
        load_buildings_from_xml_file(self, filepath, borderCoordinates, addressRestriciton)
       

    def write_to_citygml(self, filename: str, version: str= "2.0") -> None:
        """writes the current Dataset to a CityGML

        Parameters
        ----------
        filename : str
            new filename (including path if wanted)
        version : str, optional
            CityGML version - either "1.0" or "2.0", by default "2.0"
        """
        write_citygml_file(self, filename, version)