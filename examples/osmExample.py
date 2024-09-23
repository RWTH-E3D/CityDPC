from citydpc import Dataset
import json
from citydpc.tools import cityBIT
from citydpc.core.output import cityjsonOutput
from pyproj import Transformer

# load osm query that only contains buildings
with open("examples/exampleQuery.json") as f:
    osmQuery = json.load(f)

# create empty dataset
dataset = Dataset()
t = Transformer.from_crs("epsg:4326", "epsg:5555")

# split query into dict of nodes and ways for easier access
nodes = {}
ways = {}
for element in osmQuery["elements"]:
    if element["type"] == "node":
        nodes[element["id"]] = element
    elif element["type"] == "way":
        ways[element["id"]] = element

# transform all nodes to local coordinate system
for node in nodes.values():
    lat, lon = t.transform(node["lat"], node["lon"])
    node["lat"] = round(lat, 3)
    node["lon"] = round(lon, 3)

# iterate over ways and create building objects
for bID, obj in ways.items():
    coordinates = []
    # iterate over nodes and append them to the coordinates list
    for node in obj["nodes"]:
        coordinates.append([nodes[node]["lat"], nodes[node]["lon"]])
    # create building object with a ground surface height of 160m and
    # building height of 12m with a flat roof (code: "1000")
    building = cityBIT.create_LoD2_building(str(bID), coordinates, 160, 12, "1000")
    # add building object to dataset
    dataset.buildings[building.gml_id] = building

cityjsonOutput.write_cityjson_file(dataset, "example.city.json")
