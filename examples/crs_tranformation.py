# start by importing the Dataset package
from citydpc import Dataset
# important: import Dataset and not dataset

# create a Dataset object
newDataset = Dataset()

# to load buildings from a file you need the respective importer
# to add a xml/gml file:
from citydpc.core.input.citygmlInput import load_buildings_from_xml_file
load_buildings_from_xml_file(newDataset, "examples/files/EssenExample.gml")


# import cityGTV package
from citydpc.tools import cityGTV


# to validate the geometries of the polygons within a dataset use
res = cityGTV.validate_dataset(newDataset)
# res is a nested dict with key : value pairs of:
# <buildingId>_poly : valiDict
# <buildingId>_bp : buildingPartDict
# best to test it out yourself and look at one result

# import pyproj package and initialize projections
from pyproj import Proj
iP = Proj("epsg:5555")
oP = Proj("epsg:5555")

# transform dataset
newNew = cityGTV.transform_dataset(newDataset, iP, oP, (360133.335, 5706839.754), (324219.701, 5641681.61), "EPSG:5555", 0, 0)

# import exporter for CityGML
from citydpc.core.output.citygmlOutput import write_citygml_file
# call function for export and set new file name
write_citygml_file(newNew, "transformed.gml")




