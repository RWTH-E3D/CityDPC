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


class AddressCollection:
    """object representing a collection of core:Address elements"""

    def __init__(self) -> None:
        self.addresses = []

    def addressCollection_is_empty(self) -> bool:
        """check if address collection is empty

        Returns
        -------
        bool
            True:  address collection is empty
            False: address collection is not empty
        """
        return len(self.addresses) == 0

    def add_address(self, address: CoreAddress) -> None:
        """add address to collection

        Parameters
        ----------
        address : CoreAddress
            address object
        """
        self.addresses.append(address)

    def get_adresses(self) -> list[CoreAddress]:
        """return list of addresses in collection

        Returns
        -------
        list[CoreAddress]
            list of addresses
        """
        return self.addresses

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
        for address in self.addresses:
            res = address.check_address(addressRestriciton)
            if res:
                return True

        return False
