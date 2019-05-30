#!/usr/bin/python3
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from bson.objectid import ObjectId
from io import StringIO
import numpy as n, networkx as x, percolation as p
import sys, json, os, pickle
from scipy.linalg import expm
from sklearn.manifold import MDS, TSNE
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

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
    # with open('../utils/scalefree.enet', 'r') as f:
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
    return {**data, **{'mean': mean, 'std': std}}


mfnames = {'dolphins': 'dolphinsA.txt', 'zackar': 'ZackarA.txt'}
@app.route("/communicability/", methods=['POST'])
def communicability():
    f = request.form

    netid = request.form['netid']
    query = {'_id': ObjectId(netid), 'layer': 0}
    network_ = db.networks.find_one(query)
    # A = n.loadtxt('../data/matrix/' + mfnames[f['net']])
    fname = '../data/matrix/' + network_['filename']
    with open(fname, 'w') as f_:
        f_.write(network_['data'])
    A = n.loadtxt(fname)
    As = n.maximum(A, A.T) - n.diag(n.diag(A))
    N = As.shape[0]

    G = expm(float(f['temp'])*As)  # communicability matrix using Pade approximation
    sc = n.matrix(n.diag(G)).T  # vector of self-communicabilities

    u = n.matrix(n.ones(N)).T

    # CD = n.dot(sc, u.T) + n.dot(u, sc.T) -2 * G  # squared communicability distance matrix
    # X = n.array(CD) ** .5  # communicability distance matrix

    An___ = n.arccos(G / (n.array(n.dot(sc, u.T)) * n.array( n.dot(u, sc.T))) ** .5)
    An__ = n.degrees(An___)
    min_angle = float(f['mangle'])
    An_ = An__ + min_angle - n.identity(N) * min_angle
    An = n.real( n.maximum(An_, An_.T) ) # communicability angles matrix

    # E_original = n.linalg.eigvals(An)

    if f['dimredtype'] == 'MDS':
        embedding = MDS(n_components=int(f['dim']), n_init=int(f['inits']), max_iter=int(f['iters']), n_jobs=-1, dissimilarity='precomputed')
    else:
        embedding = TSNE(n_components=int(f['dim']), n_iter=int(f['iters']), metric='precomputed', learning_rate=int(f['lrate']), perplexity=int(f['perplexity']))
    p = positions = embedding.fit_transform(An)

    p_ = .8 * p / n.abs(p).max()
    sphere_data = getSphere(p_)
    ll = n.vstack( A.nonzero() ).T.tolist()  # links

    # detecting communities
    km = []
    ev = []
    nclusts = list(range(int(f['ncluin']), int(f['nclu'])+1))
    for i in nclusts:
        kmeans = KMeans(n_clusters=i, random_state=0).fit(An)
        km.append(kmeans)
        # score = silhouette_score(An, kmeans.labels_, metric='precomputed')
        score = silhouette_score(An, kmeans.labels_)
        ev.append(score)
    km_ = [[int(j) for j in i.labels_] for i in km]

    return jsonify({
        'nodes': p_.tolist(), 'links': ll, 'sdata': sphere_data,
        'ev': ev, 'clusts': km_
    })
            
