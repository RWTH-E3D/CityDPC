from citydpc import Dataset
from citydpc.core.input.cityjsonInput import load_buildings_from_json_file
from citydpc.core.output.cityjsonOutput import write_cityjson_file

# create empty dataset
newDataset = Dataset()

# load buildings from a cityJSON file
x = "examples/files/twobuildings.city.json"
load_buildings_from_json_file(newDataset, x)

# get the number of buildings in the Dataset
print(newDataset.size())

# do some operations here

# write the dataset to a cityJSON file
write_cityjson_file(newDataset, "test.json")
