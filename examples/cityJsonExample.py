from citydpc import Dataset
from citydpc.core.input.cityjsonInput import load_buildings_from_json_file
from citydpc.core.output.cityjsonOutput import write_cityjson_file

# create empty dataset
newDataset = Dataset()

# load buildings from a cityJSON file
x = "examples/files/twobuildings.city.json"
load_buildings_from_json_file(newDataset, x)
# if you want to load a cityJSONSeq file, set the cityJSONSeq parameter to True

# get the number of buildings in the Dataset
print(f"number of buildings in dataset {len(newDataset)}")
for building in newDataset.get_building_list():
    print(f"building id: {building.gml_id}")
    print(f"#s: {len(building.get_surfaces())}")
    for bp in building.get_building_parts():
        print(f"bp id: {bp.gml_id}")
        print(f"#s: {len(bp.get_surfaces())}")
    print()

# do some operations here

# write the dataset to a cityJSON file
write_cityjson_file(newDataset, "test.json")

# write the dataset to a CityJSONSeq file
write_cityjson_file(newDataset, "test.jsonl", cityJSONSeq=True)
