from pyStadt.dataset import Dataset
from pyStadt.tools import cityBIT
from pyStadt.core.output import cityjsonOutput

# create empty dataset
newDataset = Dataset()

# create a building with a flat roof
bId0 = "building0"
building = cityBIT.create_LoD2_building(bId0,
                                        [[294390, 5628950],
                                         [294400, 5628950],
                                         [294400, 5628960],
                                         [294390, 5628960]],
                                        160, 10, "1000")
newDataset.buildings[bId0] = building

# create a building with a sloped roof
bId1 = "building1"
building = cityBIT.create_LoD2_building(bId1,
                                        [[294410, 5628950],
                                         [294420, 5628950],
                                         [294420, 5628960],
                                         [294410, 5628960]],
                                        160, 10, "1010", 3, 0)
newDataset.buildings[bId1] = building

# create a building with a dualpent roof
bId2 = "building2"
building = cityBIT.create_LoD2_building(bId2,
                                        [[294430, 5628950],
                                         [294440, 5628950],
                                         [294440, 5628960],
                                         [294430, 5628960]],
                                        160, 10, "1020", 3, 0)
newDataset.buildings[bId2] = building

# create a building with a gabled roof
bId3 = "building3"
building = cityBIT.create_LoD2_building(bId3,
                                        [[294390, 5628930],
                                         [294400, 5628930],
                                         [294400, 5628940],
                                         [294390, 5628940]],
                                        160, 10, "1030", 3, 0)
newDataset.buildings[bId3] = building

# create a building with a hipped roof
bId4 = "building4"
building = cityBIT.create_LoD2_building(bId4,
                                        [[294410, 5628920],
                                         [294420, 5628920],
                                         [294420, 5628940],
                                         [294410, 5628940]],
                                        160, 10, "1040", 3)
# building = cityBIT.create_LoD2_building(bId4,
#                                         [[294410, 5628920],
#                                          [294430, 5628920],
#                                          [294430, 5628930],
#                                          [294410, 5628930]],
#                                         160, 10, "1040", 3)
newDataset.buildings[bId4] = building

# create a building with a pavilion roof
bId5 = "building5"
building = cityBIT.create_LoD2_building(bId5,
                                        [[294430, 5628920],
                                         [294440, 5628920],
                                         [294440, 5628930],
                                         [294430, 5628930]],
                                        160, 10, "1070", 3)
newDataset.buildings[bId5] = building


cityjsonOutput.write_cityjson_file(newDataset, "examples/files/cityBITExample.json")
