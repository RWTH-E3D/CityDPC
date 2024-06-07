class CityFile:
    """class for storing information from CityGML/CityJSON files"""

    def __init__(
        self,
        filepath: str,
        cityGMLversion: str,
        building_ids: list,
        num_notLoaded_CityObjectMembers: int,
        ades: list,
        srsName: str = None,
        gmlName: str = None,
        identifier: str = None,
    ) -> None:
        """stores information from an imported file

        Parameters
        ----------
        filepath : str
            filepath to given file
        cityGMLversion : str
            CityGML version as string
        building_ids : list
            list of all building ids in given file
        num_notLoaded_CityObjectMembers : int
            number of not loaded CityObjectMembers in given file
        ades : list
            list of recognized ADEs
        srsName : str, optional
            srsName of the file, by default None
        gmlName : str, optional
            content of gml:name element which is child of core:CityModel,
            by default None
        identifier : str, optional
            identifier of the file, e.g. identifier from metadata of CityJSON file,
            by default None
        """
        self.filepath = filepath
        self.cityGMLversion = cityGMLversion
        self.building_ids = building_ids
        self.num_notLoaded_CityObjectMembers = num_notLoaded_CityObjectMembers
        self.ades = ades
        self.srsName = srsName
        self.gmlName = gmlName
        self.identifier = identifier

        self.lowerCorner = None
        self.upperCorner = None
