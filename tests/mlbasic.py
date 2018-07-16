import sys
keys=tuple(sys.modules.keys())
for key in keys:
    if ("ml" in key) or ("multilevel" in key):
        del sys.modules[key]
import multilevel as ml, networkx as x
g = ml.parsers.GMLParser('/home/renato/Dropbox/Public/doc/vaquinha/FASE1/aa.gml').g

mls = ml.basic.MLS1()
mls.setNetwork(g)
mls.mkLayout()
mls.mkMetaNetwork(method='cp')
mls.mkLayout(1)

