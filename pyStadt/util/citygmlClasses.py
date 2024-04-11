# collection of CityGML namespaces for file creation and
# getting versions of inputed files


class CGML0:
    core = ""
    gen = ""
    grp = ""
    app = ""
    bldg = ""
    gml = ""
    xal = ""
    xlink = ""
    xsi = ""


class CGML1(CGML0):
    core = "http://www.opengis.net/citygml/1.0"
    gen = "http://www.opengis.net/citygml/generics/1.0"
    grp = "http://www.opengis.net/citygml/cityobjectgroup/1.0"
    app = "http://www.opengis.net/citygml/appearance/1.0"
    bldg = "http://www.opengis.net/citygml/building/1.0"
    gml = "http://www.opengis.net/gml"
    xal = "urn:oasis:names:tc:ciq:xsdschema:xAL:2.0"
    xlink = "http://www.w3.org/1999/xlink"
    xsi = "http://www.w3.org/2001/XMLSchema-instance"


class CGML2(CGML0):
    core = "http://www.opengis.net/citygml/2.0"
    gen = "http://www.opengis.net/citygml/generics/2.0"
    grp = "http://www.opengis.net/citygml/cityobjectgroup/2.0"
    app = "http://www.opengis.net/citygml/appearance/2.0"
    bldg = "http://www.opengis.net/citygml/building/2.0"
    gml = "http://www.opengis.net/gml"
    xal = "urn:oasis:names:tc:ciq:xsdschema:xAL:2.0"
    xlink = "http://www.w3.org/1999/xlink"
    xsi = "http://www.w3.org/2001/XMLSchema-instance"


class CGML3(CGML0):
    core = "http://www.opengis.net/citygml/3.0"
    con = "http://www.opengis.net/citygml/construction/3.0"
    gen = "http://www.opengis.net/citygml/generics/3.0"
    grp = "http://www.opengis.net/citygml/cityobjectgroup/3.0"
    app = "http://www.opengis.net/citygml/appearance/3.0"
    bldg = "http://www.opengis.net/citygml/building/3.0"
    gml = "http://www.opengis.net/gml/3.2"
    xal = "urn:oasis:names:tc:ciq:xal:3"
    xlink = "http://www.w3.org/1999/xlink"
    xsi = "http://www.w3.org/2001/XMLSchema-instance"
    vers = "http://www.opengis.net/citygml/versioning/3.0"
