from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import numpy as n, networkx as x
import sys, json
keys=tuple(sys.modules.keys())
for key in keys:
    if ("ml" in key) or ("multilevel" in key):
        del sys.modules[key]
import multilevel as ml

app = Flask(__name__)
CORS(app)

@app.route("/postTest/", methods=['POST'])
def postTest():
    # print(data)
    print(request.form.getlist('message_range[]'))
    print(dir(request.form))
    print(request.form.to_dict())
    return jsonify({
        'networks': [
            {'nodes': [1,2,3], 'edges': [(1,2), (1,3)]},
            {'nodes': [2,3,5], 'edges': [(2,5), (2,3)]}
        ],
        'stats': [
            {'clust':[.3, .4, .1], 'degree': [2,1,1]},
            {'clust':[.1, .6, .2], 'degree': [3,2,0]}
        ]
    })

@app.route("/evolvingNet/<netid>/")
def evolvingNet(netid):
    # return the {nodes:[], edges:[], ntransactions: N} structure
    with open('../utils/here.enet', 'r') as f:
        edges_ = json.load(f)

    net = ml.utils.mkNetFromEdges(edges_)
    nodes = list(net.nodes())
    edges = list(net.edges(data=True))
    return jsonify({
        'nodes': nodes,
        'edges': edges,
        'transactions': edges_
    })

@app.route("/evolvingAnalysis/<netid>/<window_size>/<step>/<first_message>/<last_message>/")
def evolvingAnalysis():
    # return the {degrees:{node: N}, edges:[], ntransactions: N} structure
    # for each snapshot
    # maybe make other measures as well
    # make the analysis data reuse through mongo
    return 'ok man in pyserver'

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
def net(net, layout, dim=3):  # deprecated?
    g = ml.parsers.GMLParser(nets[net]).g
    l = layouts[layout](g, dim=dim)
    nodepos = [l[i].tolist() for i in g.nodes]
    edges = [list(i) for i in g.edges]
    # nodepos = (2*n.random.random((nn,3))-1).tolist()
    return jsonify({'nodes': nodepos, 'edges': edges})

@app.route("/netlevel/<int:net>/<layout>/<int:dim>/<int:level>/<method>/")
def netlevel(net, layout, dim=3, links=1, level=1, method='mod'):
    # modularity, min_cut, center-periphery, hubs-int-per, 
    mls = ml.basic.MLS1()
    mls.setLayout(layout)
    mls.setDim(dim)
    mls.setNetwork(ml.parsers.GMLParser(mls.nets[net]).g)
    mls.mkMetaNetwork(level, method)
    mls.mkLayout(level)
    nodepos = [i.tolist() for i in mls.npos[level]]
    edges = [list(i) for i in mls.gs[level].edges]
    return jsonify({'nodes': nodepos, 'edges': edges})

@app.route("/netlevels/<int:net>/<layout>/<int:dim>/<int:level>/<method>/<sep>/<int:axis>/")
def netlevels(net, layout, dim=3, links=1, level=1, method='mod', sep=1, axis=3):
    # modularity, min_cut, center-periphery, hubs-int-per, 
    mls = ml.basic.MLS2()
    mls.setLayout(layout)
    mls.setDim(dim)
    mls.setNetwork(ml.parsers.GMLParser(mls.nets[net]).g)  # set o _id da network
    mls.mkMetaNetwork(level, method)  # buscar tb se tiver feito
    mls.mkLayout(level)  # buscar, soh fazer se n estiver pronto
    mls.mkLayout(level+1)  # idem
    mls.mkLevelLayers(float(sep), axis)  # aqui aplicar sempre
    nodepos = [i.tolist() for i in mls.npos_]
    edges = mls.edges_
    return jsonify({'nodes': nodepos, 'edges': edges})

db = ml.db.Connection()

@app.route("/netlevelsFoo/<net>/<layout>/<int:dim>/<int:level>/<method>/<sep>/<int:axis>/")
def netlevelsFoo(net, layout, dim=3, links=1, level=1, method='mod', sep=1, axis=3):
    # modularity, min_cut, center-periphery, hubs-int-per, 
    mls = ml.basic.MLS2()
    mls.setLayout(layout)
    mls.setDim(dim)
    mls.setNetwork(db.getNet(net))  # apenas pegar a rede pelo ID
    mls.mkMetaNetwork(level, method)  # buscar tb se tiver feito
    mls.mkLayout(level)  # buscar, soh fazer se n estiver pronto
    mls.mkLayout(level+1)  # idem
    mls.mkLevelLayers(float(sep), axis)  # aqui aplicar sempre
    nodepos = [i.tolist() for i in mls.npos_]
    edges = mls.edges_
    return jsonify({'nodes': nodepos, 'edges': edges})

@app.route("/netlevelsDB/<netid>/<layout>/<int:dim>/<int:nlayers>/<method>/<sep>/<int:axis>/")
def netlevelsDB(netid, layout, dim=3, links=1, nlayers=1, method='mod', sep=1, axis=3):
    layers = []
    # nlayers >= 1, if == 1 there is no coarsening
    for layer in range(nlayers):
        # two lists: one of node ids, another of tuples of ids of each link:
        print('layer')
        tnet = db.getNetLayer(netid, method, layer)
        # a dict { node_id: position (x, y, z) } as { key: value }
        tlayout = db.getNetLayout(netid, method, layer, layout, dim, tnet)
        # layers.append( {'network': tnet, 'layout': tlayout} )
        nodepos = tlayout.tolist()
        edges = [(i, j) for i, j in tnet.edges]
        layers.append( {'nodes': nodepos, 'edges': edges} )
    return jsonify(layers)

@app.route("/plotlevels/<int:net>/<layout>/<int:dim>/<int:links>/<int:level>/<method>/<sep>/<axis>/")
def plotlevels(net, layout, dim=3, links=1, level=1, method='mod', sep=1, axis=3):
    return render_template('basicURLMLInterface2.html', net=net, layout=layout, dim=dim, links=links, ml=ml, levels=level, method=method, sep=sep, axis=axis)

@app.route("/plotlevel/<int:net>/<layout>/<int:dim>/<int:links>/<int:level>/<method>/")
def plotlevel(net, layout, dim=3, links=1, level=1, method='mod'):
    return render_template('basicURLMLInterface.html', net=net, layout=layout, dim=dim, links=links, ml=ml, levels=level, method=method)


@app.route("/plotmultilevel/<int:net>/<layout>/<int:dim>/<int:links>/<levels>/<method>/")
def plotmultilevel(net, layout, dim=3, links=1, levels=0, method='mod'):
    # if levels == 0, plot from full network to singleton
    return render_template('basicURLMLInterface.html', net=net, layout=layout, dim=dim, links=links, ml=ml, levels=levels)




@app.route("/part/<slug>/")
def part(slug):
    # use slug to access data of participant/user which is a person, an organization, an institution, an entity, other
    # rdf data of the part is shown, it is an string ID, preferably user-readable
    # networks related to the slug are shown, in their pre-coarsenest version (before collapse into singleton) by default, 
    # the client may navigate such structures, obtain more by scrapping bots and APIs.
    # the client may analyse such structures, obtain insights in how it is organized, how it is characterized and differs from others,
    # and how to engage in it to alter its structures, for collection and diffusion of information, and for linking their social networks
    # (virtual or in-person) to them.
    pass
