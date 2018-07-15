from flask import Flask, jsonify, render_template
import numpy as n, networkx as x
import sys
keys=tuple(sys.modules.keys())
for key in keys:
    if ("ml" in key) or ("multilevel" in key):
        del sys.modules[key]
import multilevel as ml

app = Flask(__name__)

@app.route("/")
def index():
    return jsonify((2*n.random.random((15,3))-1).tolist())

@app.route("/rand/")
def rand():
    nn = 50
    g = x.random_graphs.barabasi_albert_graph(nn,3)
    l = x.layout.spectral_layout(g,dim=3)
    nodepos = [l[i].tolist() for i in g.nodes()]
    edges = [list(i) for i in g.edges()]
    # nodepos = (2*n.random.random((nn,3))-1).tolist()
    return jsonify({'nodes': nodepos, 'edges': edges})

@app.route("/gml/")
def gml():
    g = ml.parsers.GMLParser('/home/renato/Dropbox/Public/doc/vaquinha/FASE1/aa.gml').g
    l = x.layout.spring_layout(g,dim=3)
    nodepos = [l[i].tolist() for i in g.nodes]
    edges = [list(i) for i in g.edges]
    # nodepos = (2*n.random.random((nn,3))-1).tolist()
    return jsonify({'nodes': nodepos, 'edges': edges})

@app.route("/bbl/")
def bbl():
    return render_template('bblTest.html')

nets = [
        '/home/renato/Dropbox/Public/doc/vaquinha/FASE1/aa.gml',
        '/home/renato/Dropbox/Public/doc/vaquinha/FASE1/automata18022013.gml',
        '/home/renato/Dropbox/Public/doc/vaquinha/FASE1/GabiThume_huge_100002011676407_2013_02_19_04_40_b60204320447f88759e1efe7b031357b.gml',
        '/home/renato/Dropbox/Public/doc/vaquinha/FASE1/LarissaAnzoateguihuge_1760577842_2013_02_20_02_07_f297e5c8675b72e87da409b2629dedb3.gml',
        '/home/renato/Dropbox/Public/doc/vaquinha/FASE1/PedroRochaAttaktorZeros10032013.gml',
       ]
layouts = {
        'circular' : x.layout.circular_layout,
        'fruch' : x.layout.fruchterman_reingold_layout, # same as spring?
        'kamada' : x.layout.kamada_kawai_layout, # cool
        'random' : x.layout.random_layout,
        'shell' : x.layout.shell_layout, # arrumar 3d
        'spectral' : x.layout.spectral_layout,
        'spring' : x.layout.spring_layout,
        }
@app.route("/plot/<int:net>/<layout>/<int:dim>/<int:links>/")
def plot(net, layout, dim=3, links=1):
    return render_template('basicURLInterface.html', net=net, layout=layout, dim=dim, links=links)

@app.route("/net/<int:net>/<layout>/<int:dim>/")
def net(net, layout, dim=3):
    g = ml.parsers.GMLParser(nets[net]).g
    l = layouts[layout](g, dim=dim)
    nodepos = [l[i].tolist() for i in g.nodes]
    edges = [list(i) for i in g.edges]
    # nodepos = (2*n.random.random((nn,3))-1).tolist()
    return jsonify({'nodes': nodepos, 'edges': edges})

@app.route("/level/<int:net>/<layout>/<int:dim>/<int:links>/<int:level>/<method>/")
def level_(net, layout, dim=3, links=1, level=1, method='mod'):
    # modularity, min_cut, center-periphery, hubs-int-per, 
    if level == 0:
        return render_template('basicURLInterface.html', net=net, layout=layout, dim=dim, links=links)
    if method == 'cp':  # center-periphery
        if level == 2:
            nodepos = [[0, 0, 0]]
            edges = []
        if level == 1:
            g = ml.parsers.GMLParser(nets[net]).g
            per = set(x.periphery(g))
            cen = set(x.center(g))
            pc = per.union(cen)
            nodes = set(g.nodes())
            inter = nodes.difference(pc)
            # l = layouts['spring'](g_, dim=dim)
            nodepos = [(-1,0,0,len(per)), (0,0,0,len(inter)), (1,0,0,len(cen))]
            edges = [list(i) for i in g.edges]
    return jsonify({'nodes': nodepos, 'edges': edges})

    return render_template('basicURLMLInterface.html', net=net, layout=layout, dim=dim, links=links, ml=ml, level=level)

