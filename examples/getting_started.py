"""
This is an example script shows how you 
can load files to the package and get some
basic information about the dataset
"""

# start by importing the Dataset package
from PyStadt import Dataset
# important: import Dataset and not dataset

# create a Dataset object
newDataset = Dataset()

# add a xml/gml file
newDataset.add_buildings_from_xml_file("examples/files/EssenExample.gml")

# get the number of buildings in the Dataset
number_of_buildings = newDataset.size()

# you can get some more info (e.g. gml_version, crs, LoD) 
# using the analysis function
from PyStadt import cityATB
dict_with_info = cityATB.analysis(newDataset)

# buildings are stored as a dict
# where the key is a gml:id and the value is a building object
# you can iterate over them like this:
for gml_id, building in newDataset.buildings.items():

    # you can get the level of deatail of the building
    level_of_detail = building.lod
    
    # check if it has a 3D geometry
    is_3D = building.has_3Dgeometry()

    if is_3D:
        # you can get coordinates as dict like this
        # where the key is the id of the surface and 
        # the value is a surfacegml representation
        walls = building.walls
        grounds = building.grounds
        roofs = building.roofs

        # e.g. to get the area of all roof surfaces
        # you can use the next two lines
        for id, surface in roofs.items():
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
        for builidngPart in building_parts.items():
            roof_volume = builidngPart.roof_volume

# if you don't want to use a dict you can 
# also get a list of all buildings using
buildings = newDataset.get_building_list()


