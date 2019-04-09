#!/usr/bin/python3
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import numpy as n, networkx as x, percolation as p
import sys, json
keys=tuple(sys.modules.keys())
for key in keys:
    if ("ml" in key) or ("multilevel" in key):
        del sys.modules[key]
import multilevel as ml

app = Flask(__name__)
CORS(app)

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
    with open('../utils/scalefree.enet', 'r') as f:
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
        degrees = list(dict(tnet.degree()).values())
        clust = list(dict(x.clustering(tnet)).values())
        layers.append({
            'nodes': nodepos, 'edges': edges,
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
