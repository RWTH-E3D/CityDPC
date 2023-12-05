from pyStadt import Dataset
from pyStadt.core.input.cityjsonInput import load_buildings_from_json_file

x = "/Users/simon/Downloads/twobuildings.city.json"
newDataset = Dataset()
load_buildings_from_json_file(newDataset, x)
