from flask import Flask, jsonify, render_template
from flask_cors import CORS
import numpy as n, networkx as x
import sys
keys=tuple(sys.modules.keys())
for key in keys:
    if ("ml" in key) or ("multilevel" in key):
        del sys.modules[key]
import multilevel as ml

app = Flask(__name__)
CORS(app)

db = ml.db.Connection()

@app.route("/netlevels/<net>/<layout>/<int:dim>/<int:layers>/<method>/<sep>/<int:axis>/")
def netlevels(net, layout, dim=3, links=1, layers=1, method='mod', sep=1, axis=3):
    # modularity, min_cut, center-periphery, hubs-int-per, 
    print(net, 'ok')
    # para cada nivel:
    nets = [ml.io.getNetworkAndLayout(net, method, layer, layout, dim, net_prev=None)]

    for layer in range(layers+1):
        # verifica se existe a rede ou precisa fazer (coarsen) e salvar
        tnet = db.getNetLayer(net, method, layer, nets[-1][0])
        print('===========', tnet['data'])
        tnet_ = ml.parsers.GMLParserDB(tnet['data'])
        print(tnet_, tnet_.g.number_of_nodes(), tnet_.g.number_of_edges())
        # verifica se existe o layout ou precisa fazer e salvar
        print(db.getNetLayout(net, layout, dim, method, layer))

    return 'my return'
    # mls = ml.basic.MLS2()
    # mls.setLayout(layout)
    # mls.setDim(dim)
    # mls.setNetwork(ml.parsers.GMLParser(mls.nets[net]).g)  # set o _id da network
    # mls.mkMetaNetwork(level, method)  # buscar tb se tiver feito
    # mls.mkLayout(level)  # buscar, soh fazer se n estiver pronto
    # mls.mkLayout(level+1)  # idem
    # mls.mkLevelLayers(float(sep), axis)  # aqui aplicar sempre
    # nodepos = [i.tolist() for i in mls.npos_]
    # edges = mls.edges_
    # return jsonify({'nodes': nodepos, 'edges': edges})
