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
    l = x.layout.spectral_layout(g,3)
    nodepos = [l[i].tolist() for i in g.nodes()]
    # nodepos = (2*n.random.random((nn,3))-1).tolist()
    return jsonify({'nodes': nodepos, 'edges': g.edges()})

@app.route("/gml/")
def gml():
    g = ml.parsers.GMLParser('/home/renato/Dropbox/Public/doc/vaquinha/RenatoFabbri11072013.gml').g
    l = x.layout.spectral_layout(g,3)
    nodepos = [l[i].tolist() for i in g.nodes]
    # nodepos = (2*n.random.random((nn,3))-1).tolist()
    return jsonify({'nodes': nodepos, 'edges': g.edges})

@app.route("/bbl/")
def bbl():
    return render_template('bblTest.html')
