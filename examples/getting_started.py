"""
This is an example script shows how you 
can load files to the package and get some
basic information about the dataset
"""

# start by importing the Dataset package
from pyStadt import Dataset

# important: import Dataset and not dataset

# create a Dataset object
newDataset = Dataset()

# to load buildings from a file you need the respective importer
# to add a xml/gml file:
from pyStadt.core.input.citygmlInput import load_buildings_from_xml_file

load_buildings_from_xml_file(newDataset, "examples/files/EssenExample.gml")

# get the number of buildings in the Dataset
number_of_buildings = newDataset.size()

# you can get some more info (e.g. gml_version, crs, LoD)
# using the analysis function
from pyStadt.tools import cityATB

dict_with_info = cityATB.analysis(newDataset)

# buildings are stored as a dict
# where the key is a gml:id and the value is a building object
# you can iterate over them like this:
for building in newDataset.get_building_list():
    # you can get the id by
    id = building.gml_id

    # check if it has a 3D geometry
    is_3D = building.has_3Dgeometry()

    if is_3D:
        # you can get coordinates as dict like this
        # where the key is the id of the surface and
        # the value is a surfacegml representation
        walls = building.get_surfaces(surfaceTypes=["WallSurface"])
        grounds = building.get_surfaces(surfaceTypes=["GroundSurface"])
        roofs = building.get_surfaces(surfaceTypes=["RoofSurface"])

        # e.g. to get the area of all roof surfaces
        # you can use the next two lines
        for surface in roofs:
            area = surface.surface_area

        # I recommend looking at the surfacegml.py
        # SurfaceGML object for more surface related info

    # get the roof volume
    roof_volume = building.roof_volume

    # check if it has building parts
    has_children = building.has_building_parts()
    # and get them using
    if has_children:
        building_parts = building.get_building_parts()
        # building parts have very similar methods and
        # and parameters as buildings

        # for example
        for builidngPart in building_parts:
            roof_volume = builidngPart.roof_volume

# searching for a street name can be done like this
# you can use as many or as few key value pairs as you like
dataAddress = cityATB.search_dataset(newDataset, addressRestriciton={"thoroughfareName": "Stakenholt"}, inplace=False)
# with the parameter inplace= False a new Dataset will be created (default)
# when setting the parameter to True the operation will be done on the existing dataset

# you can also create a coordinate border using the borderCoordinates argument
dataCoordinate = cityATB.search_dataset(newDataset, borderCoordinates=[[360057.31, 5706881.64], [360057.31, 5706267.41], [359792.94, 5706267.41], [359792.94, 5706881.64]])

# you can also do both operations at the same time (and even in the load_buildings_from_xml_file function)
dataCombine = cityATB.search_dataset(
    newDataset,
    borderCoordinates=[
        [360057.31, 5706881.64],
        [360057.31, 5706267.41],
        [359792.94, 5706267.41],
        [359792.94, 5706881.64],
    ],
    addressRestriciton={"thoroughfareName": "Stakenholt"},
)

# if you want to save your changes you need the respective exporter
# for CityGML use:
print(len(dataCombine.get_building_list()))
from pyStadt.core.output.citygmlOutput import write_citygml_file

write_citygml_file(dataCombine, "newFilename.gml")
# you can choose between CityGML 1.0 and 2.0
