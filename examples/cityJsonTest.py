from pyStadt import Dataset
from pyStadt.core.input.cityjsonInput import load_buildings_from_json_file

newDataset = Dataset()
load_buildings_from_json_file(newDataset, "examples/files/twobuildings.city.json")
    

from pyStadt.core.output.cityjsonOutput import write_ciyjson_file
write_ciyjson_file(newDataset, "test.json")
