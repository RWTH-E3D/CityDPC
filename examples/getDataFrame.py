from citydpc import Dataset
from citydpc.core.input.citygmlInput import load_buildings_from_xml_file
from citydpc.tools.datasetToDataFrame import getDataFrame

# create a Dataset object
newDataset = Dataset()

load_buildings_from_xml_file(newDataset, "examples/files/EssenExample.gml")

print(getDataFrame(newDataset, True, True))
