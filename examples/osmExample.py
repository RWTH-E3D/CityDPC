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
t = Transformer.from_crs("epsg:4326", "epsg:2555")

# load osm data
for b in osmQuery["elements"]:
    # load coordinates of building outline
    coordinates = []
    for point in b["geometry"]:
        # transform coordinates to local coordinate system
        coordinates.append(t.transform(point["lat"], point["lon"]))
    # create a building with a flat roof
    building = cityBIT.create_LoD2_building(b["id"], coordinates, 160, 10, "1000")
    dataset.buildings[b["id"]] = building

# save dataset as cityjson
cityjsonOutput.write_cityjson_file(dataset, "osmExample.json")
