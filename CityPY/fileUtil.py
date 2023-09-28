class CityFile():
    """class for storing information from CityGML/CityJSON files
    """

    def __init__(self, filepath: str, cityGMLversion: str, building_ids: list, \
                 ades: list, gmlName: str = None) -> None:
        """_summary_

        Parameters
        ----------
        filepath : str
            filepath to given file
        cityGMLversion : str
            CityGML version as string
        building_ids : list
            list of all building ids in given file
        ades : list
            list of recognized ADEs 
        gmlName : str, optional
            content of gml:name element which is child of core:CityModel, by default None
        """
        self.filepath = filepath
        self.cityGMLversion = cityGMLversion
        self.building_ids = building_ids
        self.ades = ades
        self.gmlName = gmlName

        self.lowerCorner = None
        self.upperCorner = None
