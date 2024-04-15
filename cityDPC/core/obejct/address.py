class CoreAddress:
    """object representing a core:Address element"""

    def __init__(self) -> None:
        self.gml_id = None

        self.countryName = None
        self.locality_type = None
        self.localityName = None
        self.thoroughfare_type = None
        self.thoroughfareNumber = None
        self.thoroughfareName = None
        self.postalCodeNumber = None

    def address_is_empty(self) -> bool:
        """checks if address object is empty

        Returns
        -------
        bool
            True:  address is empty
            False: address is not empty
        """
        if (
            self.countryName is None
            and self.locality_type is None
            and self.localityName is None
            and self.thoroughfare_type is None
            and self.thoroughfareNumber is None
            and self.thoroughfareName is None
            and self.postalCodeNumber is None
        ):
            return True
        else:
            return False

    def check_address(self, addressRestriciton: dict) -> bool:
        """checks if the address building matches the restrictions

        Parameters
        ----------
        addressRestriciton : dict
            list of address keys and their values
            e.g. localityName = Aachen

        Returns
        -------
        bool
            True:  building address matches restrictions
            False: building address does not match restrictions
        """
        if self.address_is_empty() and addressRestriciton != {}:
            return False

        for key, value in addressRestriciton.items():
            if key == "countryName":
                if self.countryName != value:
                    return False
            elif key == "locality_type":
                if self.locality_type != value:
                    return False
            elif key == "localityName":
                if self.localityName != value:
                    return False
            elif key == "thoroughfare_type":
                if self.thoroughfare_type != value:
                    return False
            elif key == "thoroughfareNumber":
                if self.thoroughfareNumber != value:
                    return False
            elif key == "thoroughfareName":
                if self.thoroughfareName != value:
                    return False
            elif key == "postalCodeNumber":
                if self.postalCodeNumber != value:
                    return False

        return True
