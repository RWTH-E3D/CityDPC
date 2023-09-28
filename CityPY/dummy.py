import sys
import matplotlib

matplotlib.use('Qt5Agg')

from PySide6 import QtWidgets

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


from CityPY.dataset import Dataset

import numpy as np
import xml.etree.ElementTree as ET

def getPosListOfSurface(surface_E, namespace):
    """extracts a numpy array of coordinates from a surface"""
    for polygon_E in surface_E.findall('.//gml:Polygon',namespace):
        Pts = polygon_E.find('.//gml:posList',namespace)
        if Pts != None:
            posList = np.array(str(Pts.text).split(' '))
        else:
            points = []
            for Pt in polygon_E.findall('.//gml:pos', namespace):
                points.extend([float(i) for i in Pt.text.split(' ')])
            posList = np.array(points)
    return posList.astype(np.float64)



class MplCanvas(FigureCanvasQTAgg):

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111,projection='3d')
        super(MplCanvas, self).__init__(fig)


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        # Create the maptlotlib FigureCanvas object,
        # which defines a single set of axes as self.axes.
        sc = MplCanvas(self, width=5, height=4, dpi=100)
        # read xml
        fileName = r"D:\downloads\Essen-Vogelheim_LoD2_YOCed.gml"
        # fileName = r"C:\Users\srami\Desktop\#testing-datasets\Aachen_grabenring.gml"

        tree = ET.parse(fileName)
        root = tree.getroot()

        # nameSpace used for ElementTree's search function
        # CityGML 1.0
        _nameSpace1 = {'core':"http://www.opengis.net/citygml/1.0",
        'gen':"http://www.opengis.net/citygml/generics/1.0",
        'grp':"http://www.opengis.net/citygml/cityobjectgroup/1.0",
        'app':"http://www.opengis.net/citygml/appearance/1.0",
        'bldg':"http://www.opengis.net/citygml/building/1.0",
        'gml':"http://www.opengis.net/gml",
        'xal':"urn:oasis:names:tc:ciq:xsdschema:xAL:2.0",
        'xlink':"http://www.w3.org/1999/xlink",
        'xsi':"http://www.w3.org/2001/XMLSchema-instance"}

        # CityGML 2.0
        _nameSpace2 = {'core':"http://www.opengis.net/citygml/2.0",
        'gen':"http://www.opengis.net/citygml/generics/2.0",
        'grp':"http://www.opengis.net/citygml/cityobjectgroup/2.0",
        'app':"http://www.opengis.net/citygml/appearance/2.0",
        'bldg':"http://www.opengis.net/citygml/building/2.0",
        'gml':"http://www.opengis.net/gml",
        'xal':"urn:oasis:names:tc:ciq:xsdschema:xAL:2.0",
        'xlink':"http://www.w3.org/1999/xlink",
        'xsi':"http://www.w3.org/2001/XMLSchema-instance"}

        # check the version of CityGML
        with open(fileName,"r") as fileHandle:
            version = 0
            for line in fileHandle.readlines():
                #print("current line = ",line)
                if str(line).find("citygml/1.0")!= -1:
                    _nameSpace = _nameSpace1
                    version = 1
                    print("CityGml Version = 1.0")
                    break
                elif str(line).find("citygml/2.0")!= -1:
                    _nameSpace = _nameSpace2
                    version = 2
                    print("CityGML Version = 2.0")
                    break
            # end loop 
            if version == 0:
                print("CityGML Version Not Supported.")
                return -1

        roof_list = []
        foot_list = []
        wall_list = []

        num_building = 0
        for bldg in root.findall('.//bldg:Building',_nameSpace):
            num_building += 1
            for roof in bldg.findall('.//bldg:RoofSurface',_nameSpace):
                posList = getPosListOfSurface(roof, _nameSpace)
                roof = []
                for j in range(int(len(posList)/3)):
                    pt = [posList[3*j],posList[3*j+1],posList[3*j+2]]
                    roof.append(pt)
                roof_list.append(roof)
            for foot in bldg.findall('.//bldg:GroundSurface',_nameSpace):
                posList = getPosListOfSurface(foot, _nameSpace)
                foot = []
                for j in range(int(len(posList)/3)):
                    pt = [posList[3*j],posList[3*j+1],posList[3*j+2]]
                    foot.append(pt)
                foot_list.append(foot)
            for wall in bldg.findall('.//bldg:WallSurface',_nameSpace):
                posList = getPosListOfSurface(wall, _nameSpace)
                wall = []
                for j in range(int(len(posList)/3)):
                    pt = [posList[3*j],posList[3*j+1],posList[3*j+2]]
                    wall.append(pt)
                wall_list.append(wall)

        print("Extracted " + str(num_building) + " Buildings.")
        print("Extracted " + str(len(roof_list)) + " roof surfaces.")
        print("Extracted " + str(len(foot_list)) + " foot prints.")
        print("Extracted " + str(len(wall_list))+ " wall surfaces.")


        minRange = np.array([0,0,0])
        maxRange = np.array([0,0,0])

        totalPts = []
        for roof in roof_list:
            for pt in roof:
                totalPts.append(pt)
        for foot in foot_list:
            for pt in roof:
                totalPts.append(pt)
        for wall in wall_list:
            for pt in roof:
                totalPts.append(pt)
        
        totalPts = np.array(totalPts)

        minRange = [np.amin(totalPts[:,0]),np.amin(totalPts[:,1]),np.amin(totalPts[:,2])]
        maxRange = [np.amax(totalPts[:,0]),np.amax(totalPts[:,1]),np.amax(totalPts[:,2])]

        #---------------------------------------------------------------------------------------
        # Drawings
        # fig = plt.figure(figsize=[100,100], dpi=100)
        # ax1 = fig.add_subplot(111,projection='3d')
        # ax1.azim = 100
        lineWidth = 0.5

        axLabelSign = 0
        for roof in roof_list:
            xs = []
            ys = []
            zs = []
            for pt in roof:
                xs.append(pt[0])
                ys.append(pt[1])
                zs.append(pt[2])
            xs = np.asarray(xs)
            ys = np.asarray(ys)
            zs = np.asarray(zs)
            if axLabelSign == 0:
                sc.axes.plot(xs,ys,zs,color='firebrick',lw=lineWidth,label='Roofedges')
                axLabelSign = 1
            else:
                sc.axes.plot(xs,ys,zs,color='firebrick',lw=lineWidth)
            # polygon
            verts = [list(zip(xs,ys,zs))]
            sc.axes.add_collection(Poly3DCollection(verts,alpha=0.1,facecolor='red'))
            
        axLabelSign = 0
        for foot in foot_list:
            xs = []
            ys = []
            zs = []
            for pt in foot:
                #ax1.scatter(pt[0],pt[1],pt[2],marker='^',color='indigo')
                xs.append(pt[0])
                ys.append(pt[1])
                zs.append(pt[2]) 
            xs = np.asarray(xs)
            ys = np.asarray(ys)
            zs = np.asarray(zs)
            if axLabelSign == 0:
                sc.axes.plot(xs,ys,zs,color='navy',lw=lineWidth,label='Footprints')
                axLabelSign = 1
            else:
                sc.axes.plot(xs,ys,zs,color='navy',lw=lineWidth)
            # polygon
            verts = [list(zip(xs,ys,zs))]
            sc.axes.add_collection(Poly3DCollection(verts,alpha=0.1,facecolor='royalblue'))


        # party
        current_data = Dataset()
        current_data.add_buildings_from_xml_file(fileName)
        party_walls = current_data.check_for_party_walls()
        print(f"party wall count= {len(party_walls)}")
        # print(party_walls)

        axLabelSign = 0
        for _, _, _, _, _, wall in party_walls:
            xs = []
            ys = []
            zs = []
            for pt in wall:
                xs.append(pt[0])
                ys.append(pt[1])
                zs.append(pt[2]) 
            xs = np.asarray(xs)
            ys = np.asarray(ys)
            zs = np.asarray(zs)
            if axLabelSign == 0:
                sc.axes.plot(xs,ys,zs,color='black',lw=lineWidth,label='PartyWalls')
                axLabelSign = 1
            else:
                sc.axes.plot(xs,ys,zs,color='black',lw=lineWidth)
            #polygon
            verts = [list(zip(xs,ys,zs))]
            sc.axes.add_collection(Poly3DCollection(verts,alpha=0.6,facecolor='darkgreen'))

        axLabelSign = 0
        for wall in wall_list:
            
            xs = []
            ys = []
            zs = []
            for pt in wall:
                xs.append(pt[0])
                ys.append(pt[1])
                zs.append(pt[2]) 
            xs = np.asarray(xs)
            ys = np.asarray(ys)
            zs = np.asarray(zs)
            if axLabelSign == 0:
                sc.axes.plot(xs,ys,zs,color='darkorange',lw=lineWidth,label='Walls')
                axLabelSign = 1
            else:
                sc.axes.plot(xs,ys,zs,color='darkorange',lw=lineWidth)
            #polygon
            verts = [list(zip(xs,ys,zs))]
            sc.axes.add_collection(Poly3DCollection(verts,alpha=0.1,facecolor='gold'))


        

                    
        # Set Equal Boundaries for xyz axis, using exact range of coordinates
        # To fool the matplotlib's automatic setting of the scales of xyz-axis
        rangeDiff = np.subtract(maxRange,minRange)
        maxDiff = np.max(rangeDiff)
        print(rangeDiff)


        Xb_1 = 0.5*maxDiff*np.mgrid[-1:1:0.5,-0.5:1.5:0.5,-0.5:1.5:0.5][0].flatten() + 0.5*(maxRange[0]+minRange[0])
        Yb_1 = 0.5*maxDiff*np.mgrid[-1:1:0.5,-0.5:1.5:0.5,-0.5:1.5:0.5][1].flatten() + 0.5*(maxRange[1]+minRange[1])
        Zb_1 = 0.5*maxDiff*np.mgrid[-1:1:0.5,-0.5:1.5:0.5,-0.5:1.5:0.5][2].flatten() + 0.5*(maxRange[2]+minRange[2])

        for xb1, yb1, zb1 in zip(Xb_1, Yb_1, Zb_1):
            #print(xb1,yb1,zb1)
            sc.axes.plot([xb1], [yb1], [zb1], 'w')
        
        self.setCentralWidget(sc)

        self.show()


app = QtWidgets.QApplication(sys.argv)
w = MainWindow()
app.exec()