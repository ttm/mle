#!/usr/bin/python3
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from bson.objectid import ObjectId
from io import StringIO
import numpy as n, networkx as x, percolation as p, nltk as k, gmaneLegacy as gl
import sys, json, os, pickle, random, time as t
from scipy.linalg import expm
from sklearn.metrics import silhouette_score
from sklearn.manifold import MDS, Isomap, LocallyLinearEmbedding
# http://lvdmaaten.github.io/publications/papers/JMLR_2014.pdf
from MulticoreTSNE import MulticoreTSNE as TSNE
from sklearn.decomposition import PCA
import umap  # https://umap-learn.readthedocs.io/en/latest/
from sklearn.cluster import KMeans, AgglomerativeClustering, DBSCAN, SpectralClustering, AffinityPropagation
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import warnings
warnings.filterwarnings('ignore')

keys=tuple(sys.modules.keys())
for key in keys:
    if ("ml" in key) or ("multilevel" in key):
        del sys.modules[key]
import multilevel as ml
mkSafeFname = ml.utils.mkSafeFname

app = Flask(__name__)
CORS(app)

db = ml.db.Connection()

layouts = {
        'circular' : x.layout.circular_layout,
        'fruch' : x.layout.fruchterman_reingold_layout, # same as spring?
        'kamada' : x.layout.kamada_kawai_layout, # cool
        'random' : x.layout.random_layout,
        'shell' : x.layout.shell_layout, # arrumar 3d
        'spectral' : x.layout.spectral_layout,
        'spring' : x.layout.spring_layout,
        'h-bipartite': lambda g, l0 : x.layout.bipartite_layout(g, l0, 'horizontal'),
        'v-bipartite': lambda g, l0 : x.layout.bipartite_layout(g, l0),
        }

def parseMlTxt(fname, split=True):
    with open(fname, 'r') as f:
        data = f.read()
    if split:
        return [[int(i) for i in j.split(' ') if i] for j in data.split('\n') if j]
    else:
        return [int(i) for i in data.split('\n') if i]

def parseBi(request):
    reduction = request.form.getlist('bi[reduction][]')
    max_levels = request.form.getlist('bi[max_levels][]')
    global_min_vertices = request.form.getlist('bi[global_min_vertices][]')
    matching = request.form.getlist('bi[matching][]')
    similarity = request.form.getlist('bi[similarity][]')
    upper_bound = request.form.getlist('bi[upper_bound][]')
    itr = request.form.getlist('bi[itr][]')
    tolerance = request.form.getlist('bi[tolerance][]')

    bi = locals()
    del bi['request']
    return bi

def biEnsureRendered(bi, netid):
    globals().update(bi)
    layout = request.form['layout']
    dim = int(request.form['dim'])
    dname = './mlpb/' + mkSafeFname(netid) + mkSafeFname(str(bi))
    if not os.path.isdir(dname):
        db.dumpFirstNcol(netid)
        fname = './mlpb/input/input-moreno.json'
        with open(fname, 'r') as f:
            c = json.load(f)

        c['directory'] = dname
        c['input'] = './mlpb/input/%s.ncol' % (mkSafeFname(netid),)
        nvertices = db.getBiNvertices(netid)
        c['vertices'] = nvertices


        c['reduction_factor'] = [float(i) for i in reduction]
        c['max_levels'] = [int(i) for i in max_levels]
        c['global_min_vertices'] = [int(i) for i in global_min_vertices]
        c['matching'] = matching
        c['similarity'] = similarity
        c['upper_bound'] = [float(i) for i in upper_bound]
        c['itr'] = [int(i) for i in itr]
        c['tolerance'] = [float(i) for i in tolerance]
        fname2 = './mlpb/input/input-moreno3.json'
        with open(fname2, 'w') as f:
            json.dump(c, f)

        os.system('python3 ./mlpb/coarsening.py -cnf ' + fname2)

        fnames = [i for i in os.listdir(dname) if i.endswith('.ncol')]
        fnames.sort()
        tnet = db.getNetLayer(netid, bi, 0)
        db.getNetLayout(netid, bi, 0, layout, dim, tnet)
        for fname in fnames:
            tnet = ml.parsers.parseBiNcol(dname + '/' + fname)
            layer_ = int(fname[-6])
            tinsert = {
                    'data': pickle.dumps(tnet),
                    'uncoarsened_network': ObjectId(netid),
                    'coarsen_method': bi,
                    'layer': layer_,
                    'filename': fname,
                    'urlized': fname
            }
            db.networks.insert_one(tinsert)
            # if layer_ > 1:
            #     query = {'uncoarsened_network': ObjectId(netid), 'layer': layer_ - 1, 'coarsen_method': bi}
            # else:
            #     query = {'uncoarsened_network': ObjectId(netid), 'layer': layer_ - 1}
            # print(query, '----------------<<<<<<<<<< tquery')
            # network_id = db.networks.find_one(query, {'_id': 1})
            # db.getNetLayout(network_id['_id'], bi, int(layer_), layout, dim, tnet)
            db.getNetLayout(netid, bi, int(layer_), layout, dim, tnet)

@app.route("/geneData/", methods=['POST'])
def geneData():
    r = request.get_json()
    g = r['gene']
    co = [i['co'] for i in db.db['correlations'].find({'gene': g}, {'co':1,'_id':0})]
    return jsonify(co[0])

@app.route("/genes/", methods=['POST'])
def genes():
    genes = [i['gene'] for i in db.db['correlations'].find({}, {'gene':1,'_id':0})]
    return jsonify(genes)

@app.route("/layoutOnDemand/", methods=['POST'])
def layoutOnDemand():
    # print(request.form)
    r = request.get_json()
    l = r['layout']
    d = r['dim']
    nodes = r['nodes']
    links = r['links']
    g = x.Graph()
    for n_ in nodes: g.add_node(n_)
    for ll in links: g.add_edge(ll[0], ll[1], weight=ll[2])
    if 'bipartite' in l:
        l_ = layouts[l](g, r['l0'])
    else:
        l_ = layouts[l](g, dim=d)
    l__ = n.array([l_[i] for i in nodes])
    if l__.shape[0] != 1:
        l__[:, 0] -= n.min(l__[:, 0])
        l__[:, 1] -= n.min(l__[:, 1])
        l__[:, 0] /= n.max(n.abs(l__[:, 0]))
        l__[:, 1] /= n.max(n.abs(l__[:, 1]))
        l__[:, 0] *= 2
        l__[:, 1] *= 2
        l__[:, 0] -= 1
        l__[:, 1] -= 1
    if r['lonely']:
        l__[:, 1] *= 0.9
        l__[:, 1] += 0.1
    # pos = {n: l_[n].tolist() for n in nodes}
    # pos = l__.tolist()
    pos = {n: l__[i].tolist() for i, n in enumerate(nodes)}
    return jsonify(pos)

@app.route("/biMLDBgetinfo/", methods=['POST'])
def biMLDBgetinfo():
    netid = request.form['netid']
    query = {'_id': ObjectId(netid), 'layer': 0}
    network_ = db.networks.find_one(query)
    data = network_['data']
    links = n.loadtxt(StringIO(data), skiprows=0, dtype=float).astype(int)
    nnodes = len(set(links[:, 0]).union(links[:, 1]))
    fltwo = len(set(links[:,0]))
    info = {
        'n2': nnodes - fltwo,
        'n1': fltwo,
        'l': len(links)
    }
    return jsonify(info)

@app.route("/biMLDBtopdown/", methods=['POST'])
def biMLDBtopdown():
    bi = parseBi(request)
    globals().update(bi)
    netid = request.form['netid']
    dim = int(request.form['dim'])

    dname = './mlpb/' + mkSafeFname(netid) + mkSafeFname(str(bi))
    if not os.path.isdir(dname):
        db.dumpFirstNcol(netid)
        fname = './mlpb/input/input-moreno.json'
        with open(fname, 'r') as f:
            c = json.load(f)

        c['directory'] = dname
        c['input'] = './mlpb/input/%s.ncol' % (mkSafeFname(netid),)
        nvertices = db.getBiNvertices(netid)
        c['vertices'] = nvertices

        c['reduction_factor'] = [float(i) for i in reduction]
        c['max_levels'] = [int(i) for i in max_levels]
        c['global_min_vertices'] = [int(i) for i in global_min_vertices]
        c['matching'] = matching
        c['similarity'] = similarity
        c['upper_bound'] = [float(i) for i in upper_bound]
        c['itr'] = [int(i) for i in itr]
        c['tolerance'] = [float(i) for i in tolerance]
        fname2 = './mlpb/input/input-moreno3.json'
        with open(fname2, 'w') as f:
            json.dump(c, f)

        os.system('python3 ./mlpb/coarsening.py -cnf ' + fname2)
        os.system('cp ./mlpb/input/'+mkSafeFname(netid)+'.ncol '+dname+'/moreno-0.ncol')

    fnames = [i for i in os.listdir(dname) if i.endswith('.ncol')]
    fnames.sort()
    count = 0
    layers = []
    for fname in fnames:
        fname = dname+'/'+fname
        links = n.loadtxt(fname, skiprows=0, dtype=float).astype(int)
        nnodes = len(set(links[:, 0]).union(links[:, 1]))
        fltwo = len(set(links[:,0]))
        links = links.tolist()
        if count != 0: # level 0 has no such files:
            sou = parseMlTxt(fname.replace('.ncol', '.source'))
            pred = parseMlTxt(fname.replace('.ncol', '.predecessor'))
            suc = parseMlTxt(fname.replace('.ncol', '.successor'), False)
        else:
            sou = pred = suc = [[]] * nnodes
        if count == len(fnames) - 1:
            suc = [None] * nnodes
        layer_ = {
            'links': links, 'sources': sou,
            'children': pred, 'parents': suc,
            'layer': count, 'fltwo': fltwo
        }
        layers.append(layer_)
        count += 1

    return jsonify(layers)

@app.route("/biGetLastLevel/", methods=['POST'])
def biGetLastLevel():
    bi = parseBi(request)
    netid = request.form['netid']
    biEnsureRendered(bi, netid)
    dname = './mlpb/' + mkSafeFname(netid) + mkSafeFname(str(bi))
    fnames = [i for i in os.listdir(dname) if i.endswith('.ncol')]
    levels = [int(i[-6]) for i in fnames]
    return str(max(levels))
            
@app.route("/biMLDB/", methods=['POST'])
def biMLDB():
    bi = parseBi(request)

    netid = request.form['netid']
    layout = request.form['layout']
    dim = int(request.form['dim'])
    layer = int(request.form['layer'])

    biEnsureRendered(bi, netid)

    tnet = db.getNetLayer(netid, bi, layer)
    if tnet == 'coarsening finished':
        return tnet
    # a dict { node_id: position (x, y, z) } as { key: value }
    tlayout = db.getNetLayout(netid, bi, layer, layout, dim, tnet)
    # layers.append( {'network': tnet, 'layout': tlayout} )
    nodepos = tlayout.tolist()
    edges = [(i, j) for i, j in tnet.edges]
    degrees = list(dict(tnet.degree()).values())
    clust = list(dict(x.algorithms.bipartite.clustering(tnet)).values())
    children = [list(tnet.nodes[node]['children']) for node in tnet]
    source = [list(tnet.nodes[node]['source']) for node in tnet]
    layer_ = {
        'nodes': nodepos, 'edges': edges,
        'children': children, 'source': source,
        'degrees': degrees, 'clust': clust,
        'layer': layer
    }
    return jsonify(layer_)

@app.route("/biMLDBAll/", methods=['POST'])
def biMLDBAll():
    bi = parseBi(request)

    netid = request.form['netid']
    layout = request.form['layout']
    dim = int(request.form['dim'])

    biEnsureRendered(bi, netid)
    layer = 0
    layers = []
    while 1:
        print('lstart')
        tnet = db.getNetLayer(netid, bi, layer)
        if tnet == 'coarsening finished':
            break
        nodes = tnet.nodes()
        # a dict { node_id: position (x, y, z) } as { key: value }
        tlayout = db.getNetLayout(netid, bi, layer, layout, dim, tnet)
        # layers.append( {'network': tnet, 'layout': tlayout} )
        nodepos = tlayout.tolist()
        edges = [(i, j) for i, j in tnet.edges]
        degrees = list(dict(tnet.degree()).values())
        clust = list(dict(x.algorithms.bipartite.clustering(tnet)).values())
        children = [list(tnet.nodes[node]['children']) for node in nodes]
        parents = [list(tnet.nodes[node]['parent']) for node in nodes]
        sources = [list(tnet.nodes[node]['source']) for node in nodes]
        layer_ = {
            'nodes': nodepos, 'edges': edges, 'sources': sources,
            'children': children, 'parents': parents,
            'degrees': degrees, 'clust': clust,
            'layer': layer
        }
        layers.append(layer_)
        layer += 1
        print('lfinish', layer)
    print('returning response', layers)
    return jsonify(layers)
    # fnames = [i for i in os.listdir(dname) if i.endswith('.ncol')]
    # for fname in fnames:
    #     query2 = {'network': ObjectId(netid), 'layout_name': layout, 'dimensions': dim}
    #     layout_ = db.layouts.find_one(query2)
    #     if layout_:
    #         positions = pickle.loads(layout_['data'])
    #     else:
    #     tnet = ml.parsers.parseBiNcol(tdir + '/' + fname)
    #     l = layouts[layout](tnet, dim=dim)
    #     layer = fname[-6]
    #     with open(dname+'/'+layout+layer+'.pickle', 'wb') as f:
    #         pickle.dump(l, f)

    # layers = []
    # for fname in fnames:
    #     tnet = ml.parsers.parseBiNcol(tdir + '/' + fname)
    #     l = layouts[layout](tnet, dim=dim)
    #     tlayout = n.array([l[i] for i in tnet.nodes])

    #     nodepos = tlayout.tolist()
    #     edges = [(i, j) for i, j in tnet.edges]
    #     degrees = list(dict(tnet.degree()).values())
    #     clust = list(dict(x.clustering(tnet)).values())
    #     layer_ = {
    #         'nodes': nodepos, 'edges': edges,
    #         'children': [[]] * len(clust),
    #         'degrees': degrees, 'clust': clust
    #     }
    #     layers.append(layer_)
    # tnet = db.getNetLayer(netid, c, layer)
    # # a dict { node_id: position (x, y, z) } as { key: value }
    # tlayout = db.getNetLayout(netid, c, layer, layout, dim, tnet)
    # # layers.append( {'network': tnet, 'layout': tlayout} )
    # nodepos = tlayout.tolist()
    # edges = [(i, j) for i, j in tnet.edges]
    # degrees = list(dict(tnet.degree()).values())
    # clust = list(dict(x.clustering(tnet)).values())
    # if layer > 0:
    #     children = [list(tnet.nodes[node]['children']) for node in tnet]
    #     print('=============> ', type(children[0]))
    # else:
    #     children = [[]] * len(clust)
    # layer_ = {
    #     'nodes': nodepos, 'edges': edges,
    #     'children': children,
    #     'degrees': degrees, 'clust': clust
    # }
    return jsonify(layer_)


@app.route("/biML/", methods=['POST'])
def biML():
    print(request.form)
    
    reduction = request.form.getlist('bi[reduction][]')
    max_levels = request.form.getlist('bi[max_levels][]')
    global_min_vertices = request.form.getlist('bi[global_min_vertices][]')
    matching = request.form.getlist('bi[matching][]')
    similarity = request.form.getlist('bi[similarity][]')
    upper_bound = request.form.getlist('bi[upper_bound][]')
    itr = request.form.getlist('bi[itr][]')
    tolerance = request.form.getlist('bi[tolerance][]')

    layout = request.form['layout']
    dim = int(request.form['dim'])

    fname = './mlpb/input/input-moreno.json'
    with open(fname, 'r') as f:
        c = json.load(f)

    tdir = './mlpb/apple'
    c['directory'] = tdir
    c['input'] = './mlpb/input/moreno.ncol'

    c['reduction_factor'] = [float(i) for i in reduction]
    c['max_levels'] = [int(i) for i in max_levels]
    c['global_min_vertices'] = [int(i) for i in global_min_vertices]
    c['matching'] = matching
    c['similarity'] = similarity
    c['upper_bound'] = [float(i) for i in upper_bound]
    c['itr'] = [int(i) for i in itr]
    c['tolerance'] = [float(i) for i in tolerance]

    fname2 = './mlpb/input/input-moreno3.json'
    with open(fname2, 'w') as f:
        json.dump(c, f)

    os.system('python3 ./mlpb/coarsening.py -cnf ' + fname2)

    fnames = [i for i in os.listdir(tdir) if i.endswith('.ncol')]

    layers = []
    for fname in fnames:
        tnet = ml.parsers.parseBiNcol(tdir + '/' + fname)
        l = layouts[layout](tnet, dim=dim)
        tlayout = n.array([l[i] for i in tnet.nodes])

        nodepos = tlayout.tolist()
        edges = [(i, j) for i, j in tnet.edges]
        degrees = list(dict(tnet.degree()).values())
        clust = list(dict(x.clustering(tnet)).values())
        layer_ = {
            'nodes': nodepos, 'edges': edges,
            'children': [[]] * len(clust),
            'degrees': degrees, 'clust': clust
        }
        layers.append(layer_)

    return jsonify(layers)

@app.route("/postTest3/", methods=['POST'])
def postTest3():
    # print(data)
    mrange = request.form.getlist('message_range[]')
    mrange = [int(i) for i in mrange]
    window_size = int(request.form['window_size'])
    window_sep = int(request.form['window_sep'])
    sec_method = request.form['sec_method']
    hip_perc = [int(i)/100 for i in request.form.getlist('hip_perc[]')]
    # with open('../utils/here.enet', 'r') as f:
    if request.form['scf'] != 'false':
        with open('../utils/scalefree.enet', 'r') as f:
            edges_ = json.load(f)
    else:
        with open('../utils/here.enet', 'r') as f:
            edges_ = json.load(f)

    e = edges_[mrange[0]:mrange[1]+1]
    count = 0
    e_ = [e]
    while count + window_size < len(e):
        chunck = e[count:count+window_size]
        e_.append(chunck)
        count += window_sep
    chunck = e[count:count+window_size]
    e_.append(chunck)

    # nets = [ml.utils.mkNetFromEdges(ee) for ee in e_]
    nets = [ml.utils.mkDiNetFromEdges(ee) for ee in e_]

    networks = []
    stats = []
    total = n.zeros((6, len(nets)))
    count = 0
    fvecs = []
    evalus = []
    for nn in nets:
        measures = p.measures.topology.directMeasures.simpleMeasures(nn)
        nodes = measures['nodes_']
        networks.append({'nodes': nodes , 'edges': list(nn.edges(data=True))})
        # d = nn.degree()
        # degree = [d[i] for i in nodes]
        degree = measures['degrees_']

        if sec_method == 'Percentages':
            # d_ = list(dict(d).items())
            d_ = list(dict(measures['degrees']).items())
            d_.sort(key = lambda x: -x[1])
            d_ = [i[0] for i in d_]
            nh = int(len(d_)*hip_perc[0])
            ni = int(len(d_)*hip_perc[1])
            hs = d_[:nh]
            is_ = d_[nh:nh+ni]
            ps = d_[nh+ni:]
            hip = [hs, is_, ps]
        else:
            class NM: pass
            nm = NM()
            dv = nn.degree()
            nm.degrees_ = list(dict(dv).values())
            nm.N = nn.number_of_nodes()
            nm.E = nn.number_of_edges()
            nm.degrees = dict(nn.degree())
            sec = p.analysis.sectorialize.NetworkSectorialization(nm, metric='d')
            hip = sec.sectorialized_agents__[::-1]

        # clust = x.clustering(nn)
        # clust_ = [clust[i] for i in nodes]

        # k = 30
        # if k > nn.number_of_nodes():
        #     k = nn.number_of_nodes() // 2
        # bet = x.betweenness_centrality(nn, k)
        # bet_ = [bet[i] for i in nodes]

        nzero = n.array(  measures['degrees_']).nonzero()
        degree_ = n.array(measures['degrees_'])[nzero]
        clust__ = n.array(measures['clustering_'])[nzero]
        bet__ = n.array(  measures['bet_'])[nzero]

        degree_mean = n.mean(degree_)
        degree_std = n.std(degree_)
        clust_mean = n.mean(clust__)
        clust_std = n.std(clust__)
        bet_mean = n.mean(bet__)
        bet_std = n.std(bet__)

        stats.append({
            'degree': degree, 'clust': measures['clustering_'], 'hip': hip,
            'degree_mean': degree_mean, 'degree_std': degree_std,
            'clust_mean': clust_mean, 'clust_std': clust_std
        })

        total[0][count] = degree_mean
        total[1][count] = degree_std
        total[2][count] = clust_mean
        total[3][count] = clust_std
        total[4][count] = bet_mean
        total[5][count] = bet_std

        pca = p.analysis.pca.PCA([degree_, clust__, bet__])
        fvecs.append(pca.feature_vec_)
        evalus.append(pca.eig_values_)

        count += 1
    
    means = total.mean(1)
    stds = total.std(1)
    stats[0]['degree_mean_mean'] = means[0]
    stats[0]['degree_mean_std'] = stds[0]
    stats[0]['degree_std_mean'] = means[1]
    stats[0]['degree_std_std'] = stds[1]
    stats[0]['clust_mean_mean'] = means[2]
    stats[0]['clust_mean_std'] = stds[2]
    stats[0]['clust_std_mean'] = means[3]
    stats[0]['clust_std_std'] = stds[3]
    stats[0]['bet_mean_mean'] = means[4]
    stats[0]['bet_mean_std'] = stds[4]
    stats[0]['bet_std_mean'] = means[5]
    stats[0]['bet_std_std'] = stds[5]

    fvecs_ = n.hstack(fvecs)
    evalus_ = n.array(evalus)
    mean_fv = fvecs_.mean(1)
    std_fv = fvecs_.std(1)
    mean_e = evalus_.mean(0)
    std_e = evalus_.std(0)
    stats[0]['pca_mean_vec'] =  list(mean_fv)
    stats[0]['pca_std_vec'] =   list(std_fv)
    stats[0]['pca_mean_eigv'] = list(mean_e)
    stats[0]['pca_std_eigv'] =  list(std_e)

    return jsonify({
        'networks': networks,
        'stats': stats 
    })


@app.route("/postTest2/", methods=['POST'])
def postTest2():
    # print(data)
    mrange = request.form.getlist('message_range[]')
    mrange = [int(i) for i in mrange]
    window_size = int(request.form['window_size'])
    window_sep = int(request.form['window_sep'])
    sec_method = request.form['sec_method']
    with open('../utils/here.enet', 'r') as f:
        edges_ = json.load(f)

    e = edges_[mrange[0]:mrange[1]+1]
    count = 0
    e_ = [e]
    while count + window_size < len(e):
        chunck = e[count:count+window_size]
        e_.append(chunck)
        count += window_sep
    chunck = e[count:count+window_size]
    e_.append(chunck)

    nets = [ml.utils.mkNetFromEdges(ee) for ee in e_]

    networks = []
    stats = []
    total = n.zeros((6, len(nets)))
    count = 0
    fvecs = []
    evalus = []
    for nn in nets:
        nodes = list(nn.nodes())
        networks.append({'nodes': nodes , 'edges': list(nn.edges(data=True))})
        d = nn.degree()
        degree = [d[i] for i in nodes]

        if sec_method == 'Percentages':
            d_ = list(dict(d).items())
            d_.sort(key = lambda x: -x[1])
            d_ = [i[0] for i in d_]
            nh = int(len(d_)*0.05)
            ni = int(len(d_)*0.15)
            hs = d_[:nh]
            is_ = d_[nh:nh+ni]
            ps = d_[nh+ni:]
            hip = [hs, is_, ps]
        else:
            class NM: pass
            nm = NM()
            dv = nn.degree()
            nm.degrees_ = list(dict(dv).values())
            nm.N = nn.number_of_nodes()
            nm.E = nn.number_of_edges()
            nm.degrees = dict(nn.degree())
            sec = p.analysis.sectorialize.NetworkSectorialization(nm, metric='d')
            hip = sec.sectorialized_agents__[::-1]

        clust = x.clustering(nn)
        clust_ = [clust[i] for i in nodes]

        k = 30
        if k > nn.number_of_nodes():
            k = nn.number_of_nodes() // 2
        bet = x.betweenness_centrality(nn, k)
        bet_ = [bet[i] for i in nodes]

        nzero = n.array(degree).nonzero()
        degree_ = n.array(degree)[nzero]
        clust__ = n.array(clust_)[nzero]
        bet__ = n.array(bet_)[nzero]

        degree_mean = n.mean(degree_)
        degree_std = n.std(degree_)
        clust_mean = n.mean(clust__)
        clust_std = n.std(clust__)
        bet_mean = n.mean(bet__)
        bet_std = n.std(bet__)

        stats.append({
            'degree': degree, 'clust': clust_, 'hip': hip,
            'degree_mean': degree_mean, 'degree_std': degree_std,
            'clust_mean': clust_mean, 'clust_std': clust_std
        })

        total[0][count] = degree_mean
        total[1][count] = degree_std
        total[2][count] = clust_mean
        total[3][count] = clust_std
        total[4][count] = bet_mean
        total[5][count] = bet_std

        pca = p.analysis.pca.PCA([degree_, clust__, bet__])
        fvecs.append(pca.feature_vec_)
        evalus.append(pca.eig_values_)

        count += 1
    
    means = total.mean(1)
    stds = total.std(1)
    stats[0]['degree_mean_mean'] = means[0]
    stats[0]['degree_mean_std'] = stds[0]
    stats[0]['degree_std_mean'] = means[1]
    stats[0]['degree_std_std'] = stds[1]
    stats[0]['clust_mean_mean'] = means[2]
    stats[0]['clust_mean_std'] = stds[2]
    stats[0]['clust_std_mean'] = means[3]
    stats[0]['clust_std_std'] = stds[3]
    stats[0]['bet_mean_mean'] = means[4]
    stats[0]['bet_mean_std'] = stds[4]
    stats[0]['bet_std_mean'] = means[5]
    stats[0]['bet_std_std'] = stds[5]

    fvecs_ = n.hstack(fvecs)
    evalus_ = n.array(evalus)
    mean_fv = fvecs_.mean(1)
    std_fv = fvecs_.std(1)
    mean_e = evalus_.mean(0)
    std_e = evalus_.std(0)
    stats[0]['pca_mean_vec'] =  list(mean_fv)
    stats[0]['pca_std_vec'] =   list(std_fv)
    stats[0]['pca_mean_eigv'] = list(mean_e)
    stats[0]['pca_std_eigv'] =  list(std_e)

    return jsonify({
        'networks': networks,
        'stats': stats 
    })

@app.route("/postTest/", methods=['POST'])
def postTest():
    # print(data)
    mrange = request.form.getlist('message_range[]')
    mrange = [int(i) for i in mrange]
    window_size = int(request.form['window_size'])
    window_sep = int(request.form['window_sep'])
    with open('../utils/here.enet', 'r') as f:
        edges_ = json.load(f)

    e = edges_[mrange[0]:mrange[1]+1]
    count = 0
    e_ = [e]
    while count + window_size < len(e):
        chunck = e[count:count+window_size]
        e_.append(chunck)
        count += window_sep
    chunck = e[count:count+window_size]
    e_.append(chunck)

    nets = [ml.utils.mkNetFromEdges(ee) for ee in e_]

    networks = []
    stats = []
    total = n.zeros((4, len(nets)))
    count = 0
    for nn in nets:
        nodes = list(nn.nodes())
        networks.append({'nodes': nodes , 'edges': list(nn.edges(data=True))})
        d = nn.degree()
        degree = [d[i] for i in nodes]

        d_ = list(dict(d).items())
        d_.sort(key = lambda x: -x[1])
        d_ = [i[0] for i in d_]
        nh = int(len(d_)*0.05)
        ni = int(len(d_)*0.15)
        hs = d_[:nh]
        is_ = d_[nh:nh+ni]
        ps = d_[nh+ni:]
        hip = [hs, is_, ps]


        clust = x.clustering(nn)
        clust_ = [clust[i] for i in nodes]

        nzero = n.array(degree).nonzero()
        degree_ = n.array(degree)[nzero]
        clust__ = n.array(clust_)[nzero]

        degree_mean = n.mean(degree_)
        degree_std = n.std(degree_)
        clust_mean = n.mean(clust__)
        clust_std = n.std(clust__)

        stats.append({
            'degree': degree, 'clust': clust_, 'hip': hip,
            'degree_mean': degree_mean, 'degree_std': degree_std,
            'clust_mean': clust_mean, 'clust_std': clust_std
        })

        total[0][count] = degree_mean
        total[1][count] = degree_std
        total[2][count] = clust_mean
        total[3][count] = clust_std
        count += 1

    means = total.mean(1)
    stds = total.std(1)
    print(len(means), len(stds))
    stats[0]['degree_mean_mean'] = means[0]
    stats[0]['degree_mean_std'] = stds[0]
    stats[0]['degree_std_mean'] = means[1]
    stats[0]['degree_std_std'] = stds[1]
    stats[0]['clust_mean_mean'] = means[2]
    stats[0]['clust_mean_std'] = stds[2]
    stats[0]['clust_std_mean'] = means[3]
    stats[0]['clust_std_std'] = stds[3]

    return jsonify({
        'networks': networks,
        'stats': stats 
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

@app.route("/netlevelDB/<netid>/<layout>/<int:dim>/<int:layer>/<method>/")
def netlevelDB(netid, layout, dim=3, layer=0, method='mod'):
    # two lists: one of node ids, another of tuples of ids of each link:
    tnet = db.getNetLayer(netid, method, layer)
    # a dict { node_id: position (x, y, z) } as { key: value }
    tlayout = db.getNetLayout(netid, method, layer, layout, dim, tnet)
    # layers.append( {'network': tnet, 'layout': tlayout} )
    nodepos = tlayout.tolist()
    edges = [(i, j) for i, j in tnet.edges]
    degrees = list(dict(tnet.degree()).values())
    clust = list(dict(x.clustering(tnet)).values())
    if layer > 0:
        children = [list(tnet.nodes[node]['children']) for node in tnet]
        print('=============> ', type(children[0]))
    else:
        children = [[]] * len(clust)
    layer_ = {
        'nodes': nodepos, 'edges': edges,
        'children': children,
        'degrees': degrees, 'clust': clust,
        'source': [[]]*len(degrees)
    }
    return jsonify(layer_)

@app.route("/netlevelsDB/<netid>/<layout>/<int:dim>/<int:nlayers>/<method>/<int:axis>/")
def netlevelsDB(netid, layout, dim=3, links=1, nlayers=1, method='mod', axis=3):
    layers = []
    # nlayers >= 1, if == 1 there is no coarsening
    for layer in range(nlayers):
        # two lists: one of node ids, another of tuples of ids of each link:
        tnet = db.getNetLayer(netid, method, layer)
        # a dict { node_id: position (x, y, z) } as { key: value }
        tlayout = db.getNetLayout(netid, method, layer, layout, dim, tnet)
        # layers.append( {'network': tnet, 'layout': tlayout} )
        nodepos = tlayout.tolist()
        edges = [(i, j) for i, j in tnet.edges]
        degrees = list(dict(tnet.degree()).values())
        clust = list(dict(x.clustering(tnet)).values())
        if layer > 0:
            children = [list(tnet.nodes[node]['children']) for node in tnet]
            print('=============> ', type(children[0]))
        else:
            children = [[]] * len(clust)
        layers.append({
            'nodes': nodepos, 'edges': edges,
            'children': children,
            'degrees': degrees, 'clust': clust
        })
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

def sphereFit(spX,spY,spZ):
    #   Assemble the A matrix
    spX = n.array(spX)
    spY = n.array(spY)
    spZ = n.array(spZ)
    A = n.zeros((len(spX),4))
    A[:,0] = spX*2
    A[:,1] = spY*2
    A[:,2] = spZ*2
    A[:,3] = 1

    #   Assemble the f matrix
    f = n.zeros((len(spX),1))
    f[:,0] = (spX*spX) + (spY*spY) + (spZ*spZ)
    C, residules, rank, singval = n.linalg.lstsq(A,f)

    #   solve for the radius
    t = (C[0]*C[0])+(C[1]*C[1])+(C[2]*C[2])+C[3]
    radius = t**0.5

    return {'r': radius[0], 'c': [C[0][0], C[1][0], C[2][0]]}

def getSphere(points):
    data = sphereFit(points[:,0], points[:,1], points[:,2])
    dists = (
                  (points[:,0] - data['c'][0])**2 
                + (points[:,1] - data['c'][1])**2 
                + (points[:,2] - data['c'][2])**2 
            ) ** 0.5
    mean = dists.mean()
    std = dists.std()
    d = {'mean': mean, 'std': std}
    return {**data, **d}


mfnames = {'dolphins': 'dolphinsA.txt', 'zackar': 'ZackarA.txt'}
@app.route("/communicabilityNets/", methods=['POST'])
def communicabilityNets():
    ns = [i for i in db.networks.find({'filename':{'$regex':'.txt$'}}, {'filename': 1, 'data': 1})]
    nets = []
    for net in ns:
        # print(net, '<<=======BBBBBB')
        if ',' in net['data']:
            A = n.loadtxt(StringIO(net['data']), delimiter=',')
        else:
            A = n.loadtxt(StringIO(net['data']))
        if A.shape[0] != A.shape[1]:
            continue
        nnodes = A.shape[0]
        nlinks = n.count_nonzero(n.maximum(A, A.T) - n.diag(n.diag(A))) / 2
        nets.append( {
            'filename': net['filename'],
            'nnodes': nnodes,
            'nlinks': nlinks,
            '_id': str(net['_id'])
        })
    return jsonify(nets)


@app.route("/communicability2/", methods=['POST'])
def communicability2():
    def decompose(dimred, dim, nneigh):
        print(dimred, dim, nneigh, [type(i) for i in (dimred, dim, nneigh)])
        if dimred == 'MDS': # slowest!
            embedding = MDS(n_components=dim, n_init=__inits, max_iter=__iters, n_jobs=-1)
        elif dimred == 'ISOMAP': # slow
            embedding = Isomap(n_neighbors=nneigh, n_components=dim, n_jobs=-1)
        elif dimred == 'LLE': # slow-acceptable
            embedding = LocallyLinearEmbedding(n_neighbors=nneigh, n_components=dim, n_jobs=-1)
        elif dimred == 'TSNE': # acceptable
            embedding = TSNE(n_components=dim, n_iter=__iters, learning_rate=__lrate, perplexity=__perplexity)
        elif dimred == 'UMAP': # fast
            embedding = umap.UMAP(n_neighbors=nneigh, n_components=dim, min_dist=0.1)
        elif dimred == 'PCA': # fastest!
            embedding = PCA(n_components=dim)
        else:
            raise ValueError('dimension reduction method not recognized')

        positions = embedding.fit_transform(An)
        return positions

    def clust(clu, i):
        if clu == 'KM': # very large
            calg = KMeans(n_clusters=i, n_init=100,n_jobs=-1)
        elif clu == 'AG': # large
            calg = AgglomerativeClustering(n_clusters=i)
        elif clu == 'SP': # medium
            # calg = SpectralClustering(n_clusters=i, affinity='precomputed', n_jobs=-1)
            calg = SpectralClustering(n_clusters=i, n_jobs=-1)
        elif clu == 'AF': # not scalable
            # calg = AffinityPropagation(n_clusters=i, affinity='precomputed', n_jobs=-1)
            calg = AffinityPropagation()
        else:
            raise ValueError('clustering algorithm not recognized: ' + clu)
        res = calg.fit(pC)
        return [int(j) for j in res.labels_]
    __inits = 30  # for MDS ~3
    __iters = 1000  # for MDS (~100) and t-SNE (~250)
    __perplexity = 5  # for t-SNE
    __lrate = 12  # for t-SNE
    f = request.get_json()
    __dimred = f['dimredmetL']
    __dimredC = f['dimredmet']
    __clu = f['clustmet']
    # __dis = 'precomputed'
    __dim =     int(f['dim'])
    __dimC =    int(f['cdim'])
    __nneigh =  int(f['nneighborsL'])
    __nneighC = int(f['nneighbors'])
    __minclu =  int(f['ncluin'])
    __nclu =    int(f['nclu'])
    netid = f['netid']
    query = {'_id': ObjectId(netid), 'layer': 0}
    network_ = db.networks.find_one(query)
    dd = {}
    tt = t.time()
    A = n.loadtxt(StringIO(network_['data']))
    As = n.maximum(A, A.T) - n.diag(n.diag(A))
    N = As.shape[0]

    G = expm(float(f['temp'])*As)  # communicability matrix using Pade approximation
    sc = n.matrix(n.diag(G)).T  # vector of self-communicabilities
    u = n.matrix(n.ones(N)).T

    c = G / (n.array(n.dot(sc, u.T)) * n.array( n.dot(u, sc.T))) ** .5
    c[c > 1] = 1
    An___ = n.arccos(c)
    # An___ = n.arccos((G / (n.array(n.dot(sc, u.T)) * n.array( n.dot(u, sc.T)))) ** .5)
    An__ = n.degrees(An___)
    min_angle = float(f['mangle'])*10e-6
    An_ = An__ + min_angle - n.identity(N) * min_angle
    An = n.real( n.maximum(An_, An_.T) ) # communicability angles matrix
    dd['communcability'] = t.time() - tt
    tt = t.time()

    p = decompose(__dimred, __dim, __nneigh)
    dd['embedding'] = t.time() - tt
    tt = t.time()

    p = .7 * p / n.abs(p).max()
    if p.shape[1] == 3:
        sphere_data = getSphere(p)
    else:
        sphere_data = getSphere(n.vstack((p.T, n.zeros(p.shape[0]))).T)
    dd['sphere'] = t.time() - tt
    tt = t.time()

    # detecting communities
    if __dimC == N:
        pC = An
    elif (__dimredC == __dimred) and (__dimC == __dim):
        pC = p
    else:
        pC = decompose(__dimredC, __dimC, __nneighC)
        dd['second embedding'] = t.time() - tt
        tt = t.time()
    km = []
    ev = []
    if __minclu == 1:
        __minclu = 2
        ev.append(-5)
        km.append([0]*N)
    nclusts = list(range(__minclu, __nclu +1 ))
    if __clu == 'AF':
        labels = clust(__clu, 0)
        km.append(labels)
        ev.append(1)
    else:
        for i in nclusts:
            labels = clust(__clu, i)
            km.append(labels)
            score = silhouette_score(pC, labels)
            ev.append(score)
    dd['clustering'] = t.time() - tt

    ll = n.vstack( A.nonzero() ).T.tolist()  # links
    print('communicability2 out')
    return jsonify({
        'nodes': p.tolist(), 'links': ll, 'sdata': sphere_data,
        'ev': ev, 'clusts': km,
        'durations': dd
    })

@app.route("/communicability/", methods=['POST'])
def communicability():
    f = request.form

    netid = request.form['netid']
    query = {'_id': ObjectId(netid), 'layer': 0}
    network_ = db.networks.find_one(query)
    A = n.loadtxt(StringIO(network_['data']))
    As = n.maximum(A, A.T) - n.diag(n.diag(A))
    N = As.shape[0]

    G = expm(float(f['temp'])*As)  # communicability matrix using Pade approximation
    sc = n.matrix(n.diag(G)).T  # vector of self-communicabilities

    u = n.matrix(n.ones(N)).T

    if f['cdmethod'] == 'dist':
        CD = n.dot(sc, u.T) + n.dot(u, sc.T) -2 * G  # squared communicability distance matrix
        X = n.array(CD) ** .5  # communicability distance matrix

    c = G / (n.array(n.dot(sc, u.T)) * n.array( n.dot(u, sc.T))) ** .5
    c[c > 1] = 1
    An___ = n.arccos(c)
    # An___ = n.arccos((G / (n.array(n.dot(sc, u.T)) * n.array( n.dot(u, sc.T)))) ** .5)
    An__ = n.degrees(An___)
    min_angle = float(f['mangle'])*10e-6
    An_ = An__ + min_angle - n.identity(N) * min_angle
    An = n.real( n.maximum(An_, An_.T) ) # communicability angles matrix

    # E_original = n.linalg.eigvals(An)

    if f['dimredtype'] == 'MDS':
        embedding = MDS(n_components=int(f['dim']), n_init=int(f['inits']), max_iter=int(f['iters']), n_jobs=-1, dissimilarity='precomputed')
    else:
        embedding = TSNE(n_components=int(f['dim']), n_iter=int(f['iters']), metric='precomputed', learning_rate=int(f['lrate']), perplexity=int(f['perplexity']))
    p = positions = embedding.fit_transform(An)

    p = .7 * p / n.abs(p).max()
    if p.shape[1] == 3:
        sphere_data = getSphere(p)
    else:
        sphere_data = getSphere(n.vstack((p.T, n.zeros(p.shape[0]))).T)
    ll = n.vstack( A.nonzero() ).T.tolist()  # links

    # detecting communities
    km = []
    ev = []
    minclu = int(f['ncluin'])
    if minclu == 1:
        minclu = 2
        ev.append(-5)
        km.append([0]*N)
    nclusts = list(range(minclu, int(f['nclu'])+1))

    if f['cdmethod'] == 'dist' and f['cddim'] == 'rd':
        X_ = embedding.fit_transform(X)
    for i in nclusts:
        # kmeans = KMeans(n_clusters=i, n_init=100, max_iter=3000, n_jobs=-1, tol=1e-6).fit(p)
        if f['cdmethod'] == 'an' and f['cddim'] == 'nd':
            kmeans = KMeans(n_clusters=i, n_init=100, max_iter=3000, n_jobs=-1, tol=1e-6).fit(An)
        if f['cdmethod'] == 'an' and f['cddim'] == 'rd':
            kmeans = KMeans(n_clusters=i, n_init=100, max_iter=3000, n_jobs=-1, tol=1e-6).fit(p)
        if f['cdmethod'] == 'dist':
            if f['cddim'] == 'nd':
                kmeans = KMeans(n_clusters=i, n_init=100, max_iter=3000, n_jobs=-1, tol=1e-6).fit(X)
            if f['cddim'] == 'rd':
                kmeans = KMeans(n_clusters=i, n_init=100, max_iter=3000, n_jobs=-1, tol=1e-6).fit(X_)
        km.append([int(j) for j in kmeans.labels_])
        score = silhouette_score(p, kmeans.labels_)
        ev.append(score)

    return jsonify({
        'nodes': p.tolist(), 'links': ll, 'sdata': sphere_data,
        'ev': ev, 'clusts': km
    })

@app.route("/getTextNetwork/", methods=['POST'])
def getTextNetwork():
    # mkNet
    # sendNet
    nn = n.random.randint(40,100)
    mm = n.random.randint(20,nn)
    g = x.barabasi_albert_graph(nn, mm)
    nodes = [i for i in g.nodes()]
    edges = [(i, j) for i, j in g.edges]
    texts = getRandomTexts(len(nodes))
    data = {
        'nodes': nodes,
        'links': edges,
        'texts': texts
    }
    return jsonify(data)

def getRandomTexts(nn):
    fids = k.corpus.brown.fileids()[:]
    texts = []
    while len(texts) < nn:
        fid = random.choice(fids)
        texts.append(' '.join(k.corpus.brown.words(fid)))
        fids.pop(fids.index(fid))
    return texts

@app.route("/anTexts/", methods=['POST'])
def anTexts():
    r = request.get_json()
    t1 = r['t1']
    t2 = r['t2']
    l1 = [len(i) for i in t1.split()]
    l2 = [len(i) for i in t2.split()]
    m1 = n.mean(l1)
    d1 = n.std(l1)
    m2 = n.mean(l2)
    d2 = n.std(l2)

    # ks statistic:
    ks = gl.kolmogorovSmirnovDistance_(l1,l2)
    return jsonify({
        'l': [m1,m2,d1,d2],
        'c': ks
    })
@app.route("/anSound/", methods=['POST'])
def anSound():
    # mk sound excerpt with start and end instants
    r = request.get_json()
    s = r['s']
    e = r['e']
    nc = int(r['ncomp'])
    d = e - s
    npath = os.environ['nuxtPATH']
    npath_ = npath + 'static/audio/'
    fn = r['fname']
    fn2 = fn.replace('.wav', 'MMMEXCERPT.wav')
    cmd = 'sox %s%s %s%s trim %f %f' % (npath_, fn, npath_, fn2, s, d)
    print(cmd)
    os.system(cmd)
    # mk arguments
    os.system('python2 ./AA/mkAn.py %s %d' % (fn2, nc))
    # run analysis
    # save files to netText/static/audio/

    return 'ok'

@app.route("/findEvents/", methods=['POST'])
def findEvents():
    # mk sound excerpt with start and end instants
    r = request.get_json()
    c = r['c'] - 1
    npath = os.environ['nuxtPATH']
    npath_ = npath + 'static/audio/MMMcomponent%d.wav' % (c,)
    # run analysis
    # save files to netText/static/audio/

    return 'ok'

@app.route("/getSoundfiles/", methods=['POST'])
def getSoundfiles():
    npath = os.environ['nuxtPATH']
    npath_ = npath + 'static/audio/'
    print(npath_)
    fnames = os.listdir(npath_)
    fnames_ = [i for i in fnames if 'MMMCOMPONENT' not in i]
    fnames_ = [i for i in fnames_ if 'MMMEXCERPT' not in i]
    print(fnames_)
    return jsonify( fnames_ )

import wave
@app.route("/sfileInfo/", methods=['POST'])
def sfileInfo():
    r = request.get_json()
    fname = r['fname']
    npath = os.environ['nuxtPATH']
    fname_ = npath + 'static/audio/' + fname
    with wave.open(fname_, 'r') as f:
        frames = f.getnframes()
        rate = f.getframerate()
        duration = frames / float(rate)
    return jsonify(duration)

import base64, re

@app.route("/saveSound/", methods=['POST'])
def saveSound():
    r = request.get_json()
    fname = r['fname']
    # data = decode_base64(r['fdata'])
    b64 = r['fdata']
    # data = base64.b64decode(b64)
    idict = re.match("data:(?P<type>.*?);(?P<encoding>.*?),(?P<data>.*)", b64).groupdict()
    # blob = idict['data'].decode(idict['encoding'], 'strict')
    blob = base64.b64decode(idict['data'])
    
    npath = os.environ['nuxtPATH']
    fname_ = npath + 'static/audio/' + fname
    with open(fname_, 'wb') as f:
        f.write(blob)
    return 'ok'

# https://stackoverflow.com/questions/24829726/python-function-to-return-javascript-date-gettime
import time, datetime

def now_milliseconds():
   return int(time.time() * 1000)

# reference time.time
# Return the current time in seconds since the Epoch.
# Fractions of a second may be present if the system clock provides them.
# Note: if your system clock provides fractions of a second you can end up
# with results like: 1405821684785.2
# our conversion to an int prevents this

def date_time_milliseconds(date_time_obj):
   return int(time.mktime(date_time_obj.timetuple()) * 1000)

def date_milliseconds():
    return date_time_milliseconds(datetime.datetime.utcnow())

# reference: time.mktime() will
# Convert a time tuple in local time to seconds since the Epoch.

msnowpyserver = now_milliseconds()

msdatepyserver = date_milliseconds()

@app.route("/timeStart/", methods=['POST'])
def timestart():
    mcalltimestart = now_milliseconds()
    r = request.get_json()
    return jsonify({
        'msnowpyserver': msnowpyserver,
        'msdatepyserver': msdatepyserver,
        'mcall_sentfromserver': [
            now_milliseconds(),
            now_milliseconds(),
            date_milliseconds(),
            date_milliseconds(),
        ],
        'mcall_sentfromclient': r['requestTime']
    })


import losd as l
pl = l.plainQueryValues

# get all snapshots:
def getLOSD(mall=True):
    if mall:
        q = '''
        SELECT ?s WHERE {
          ?s a po:Snapshot .
        }
        '''
        r = l.query(q)
        res = pl(r)
        # len(res) = 117

        q = '''
        SELECT ?s WHERE {
          ?s po:socialProtocol "Facebook" .
        }
        '''
        r = l.query(q)
        res2 = pl(r)
        # len res2 = 88
        # get name-related links between FB snapshots (nodes)

        # q = '''
        # SELECT (COUNT(DISTINCT ?author) as ?c) WHERE {
        #     ?author a po:Participant . 
        # }
        # '''
        # r = l.query(q)
        # res3 = pl(r)
        res3 = 350284

        # q = '''
        # SELECT (COUNT(DISTINCT ?f) as ?cf) WHERE {
        #     ?f a po:Friendship . 
        # }
        # '''
        # r = l.query(q)
        # res4 = pl(r)
        res4 = 2409575
        return res, res2, res3, res4
    return ''

@app.route("/mynsaParticipants/", methods=['POST'])
def mynsaParticipants():
    r = request.get_json()
    q = '''
    SELECT ?n WHERE {
      ?p po:name ?n .
      ?p po:snapshot <%s> .
    }
    ''' % (r['muri'], )
    print(q)
    r = l.query(q)
    res = pl(r)
    print(res)
    return res

def getLOSDNet(name):
    # get all names of fb stuff
    # return list of related names
    # return most similar network
    q = '''
    SELECT ?s ?n WHERE {
      ?s a po:Snapshot .
      ?s po:socialProtocol 'Facebook' .
      ?s po:name ?n .
    }
    '''
    r = l.query(q)
    res = pl(r)


def getLOSDSnaps(mall=True):
    if mall == True:
        q = '''
        SELECT ?s ?p WHERE {
          ?s a po:Snapshot .
          ?s po:socialProtocol ?p .
        }
        '''
        r = l.query(q)
        res = pl(r)
        return res
    elif mall == 'fb':
        q = '''
        SELECT ?s ?n WHERE {
          ?s a po:Snapshot .
          ?s po:socialProtocol 'Facebook' .
          ?s po:name ?n .
        }
        '''
        r = l.query(q)
        res = pl(r)
        return res

def getLOSDNetsByName(name):
    q = '''
    SELECT ?s ?n WHERE {
      ?s a po:Snapshot .
      ?s po:socialProtocol 'Facebook' .
      ?s po:name ?n .
    }
    '''
    r = l.query(q)
    res = pl(r)
    dists = calcDists(res, name)
    mdist = min(dists)
    names = [res[i][0] for i in range(dists) if dists[i] == mdist]
    print(names)
    return res

def calcDists(res, name):
    dists = []
    for r in res:
        dists.append( calcDist(r[0], name) )
    return dists

from difflib import SequenceMatcher
def calcDist(a, b):
    return SequenceMatcher(None, a, b).ratio()

def getLOSDFBNet(name):
    q = '''
    SELECT ?s ?n WHERE {
      ?s a po:Snapshot .
      ?s po:socialProtocol 'Facebook' .
      ?s po:name ?n .
    }
    '''
    r = l.query(q)
    res = pl(r)
    dists = calcDists(res, name)
    mdist = min(dists)
    adists = n.argsort(dists)[::-1]
    res_ = [res[i] for i in adists]
    names = [i[0] for i in res_]
    # print('+-=-=-=-=))))> ', name, names, len(names))

    # get network of best name,
    q = '''
    SELECT ?a1 ?a2 WHERE {
            ?f a po:Friendship . ?f po:snapshot <%s> .
            ?f po:member ?a1, ?a2 .
            FILTER(?a1 != ?a2)
            }
    ''' % (res_[0][1],)
    # print( q )
    r = l.query(q)
    res2 = pl(r)
    # print( q, len(res2) )
    # print( len(set([i[0] for i in res2])), len(set([i[1] for i in res2])) )
    q = '''
    SELECT ?p WHERE {
            ?p a po:Participant . ?p po:snapshot <%s> .
            }
    ''' % (res_[0][1],)
    # print( q )
    r = l.query(q)
    res3 = pl(r)

    # return network first 10 names
    return res_, res2, res3


@app.route("/mynsa/", methods=['POST'])
def mynsa():
    r = request.get_json()
    data = {}
    more = ''
    fbnet0 = 'lavanda0'
    if 'name' in r:
        name = r['name']
        name_ = r['name_']
        name__ = r['name__']
        if bool(r['fbnet']):
            fbnet = 'lavanda'
            print('hey man 1')
            netdata = getLOSDFBNet(r['name'])
    elif 'name_' in r:
        nm = r['name_']
        if nm[0] == 'all' and nm[1] == 'nodes':
            more = 'yet them dw.py'
            more_ = getLOSD()
        elif nm[0] == 'all' and nm[1] == 'snaps':
            more = 'yet them all.py'
            more_ = getLOSDSnaps()
            more__ = getLOSDSnaps('fb')
        else:
            print('hey man 1')
            byname = getLOSDNetsByName(name__)

    bi = locals()
    del bi['r']
    return jsonify({
        'ainfo': 56,
        'all': bi,
    })

@app.route("/mynsaLog/", methods=['POST'])
def mynsaLog():
    r = request.get_json()
    return jsonify({
        'ainfo': 56,
    })

@app.route("/mGadget/", methods=['POST'])
def mGadget():
    r = request.get_json()
    data = {}
    bi = [23, 33,2]
    return jsonify({
        'something': 56,
        'all': bi,
    })
