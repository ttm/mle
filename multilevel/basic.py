import networkx as x, numpy as n
class MLS:
    """
    Multilevel Strategy class

    """
    def __init__(self):
        pass
    def setNetwork(self, network):
        pass
    def coarsen(self):
        pass
    def uncoarsen(self):
        self._project()
        pass
    def _project(self):
        pass
    def _refine(self):
        pass
    def _match(self):
        pass
    def _collapse(self):
        pass

class MLS1:
    """
    Multilevel Strategy class

    """
    def __init__(self):
        self.gs = {}
        self.npos = {}
        self.status = ''
        self.nets = [
                '/home/renato/Dropbox/Public/doc/vaquinha/FASE1/aa.gml',
                '/home/renato/Dropbox/Public/doc/vaquinha/FASE1/automata18022013.gml',
                '/home/renato/Dropbox/Public/doc/vaquinha/FASE1/GabiThume_huge_100002011676407_2013_02_19_04_40_b60204320447f88759e1efe7b031357b.gml',
                '/home/renato/Dropbox/Public/doc/vaquinha/FASE1/LarissaAnzoateguihuge_1760577842_2013_02_20_02_07_f297e5c8675b72e87da409b2629dedb3.gml',
                '/home/renato/Dropbox/Public/doc/vaquinha/FASE1/PedroRochaAttaktorZeros10032013.gml',
        ]
        self.layouts = {
                'circular' : x.layout.circular_layout,
                'fruch' : x.layout.fruchterman_reingold_layout, # same as spring?
                'kamada' : x.layout.kamada_kawai_layout, # cool
                'random' : x.layout.random_layout,
                'shell' : x.layout.shell_layout, # arrumar 3d
                'spectral' : x.layout.spectral_layout,
                'spring' : x.layout.spring_layout,
        }
        self.layout = 'spring'
        self.dim = 3
    def setLayout(self, layout):
        assert layout in self.layouts
        self.layout = layout
    def setDim(self, dim):
        assert dim in {2,3}
        self.dim = dim
    def setNetwork(self, network):
        self.g = network
        self.gs[0] = self.g
        self.nodes = tuple(self.g.nodes())
        self.nodes_ = set(self.nodes)
        self.status += 'networkset|'
    def mkMetaNetwork(self, level=-1, method='mod'):
        """ level here is of the network to be coarsened """
        assert 'networkset' in self.status
        if level == -1:
            level = len(self.npos) -1
        self._match(level, method)  # make metaNodes
        self._collapse(level)  # make metaLinks
    def _match(self, level, method):
        if level not in self.gs:
            self.mkMetaNetwork(level -1, method)
            self.mkLayout(level-1)
        g_ = self.gs[level]
        if 'kclick' in method:  # k-click communities
            k_ = int(method.replace('kclick', ''))
            svs = [i for i in x.algorithms.community.k_clique_communities(g_, k_)]
            gg = x.Graph()
            for i, sv in enumerate(svs):
                gg.add_node(i, weight=len(sv), children=sv)
            self.gs[level+1] = gg
        elif method == 'lab':  # label propagation
            svs = [i for i in x.algorithms.community.label_propagation_communities(g_)]
            gg = x.Graph()
            for i, sv in enumerate(svs):
                gg.add_node(i, weight=len(sv), children=sv)
            self.gs[level+1] = gg
        elif method == 'cp':
            sub = [i for i in x.connected_component_subgraphs(g_)]
            g = sub[0]
            per = set(x.periphery(g))
            if len(sub) > 1:
                for per_ in sub[1:]:
                    per.update(per_.nodes())
            cen = set(x.center(g))
            pc = per.union(cen)
            nodes = set(g.nodes())
            inter = nodes.difference(pc)
            gg = x.Graph()
            gg.add_node(0, label='center', weight=len(cen), children=cen)
            gg.add_node(1, label='intermediary', weight=len(inter), children=inter)
            gg.add_node(2, label='periphery', weight=len(per), children=per)
            self.gs[level+1] = gg
        self._mkNodeMetaNodeDict(level)
    def _findMetaNode(self, node, level=0):
        for node_ in self.gs[level+1].nodes():
            if node in self.gs[level+1][node_]['children']:
                return node_
    def _mkNodeMetaNodeDict(self, level):
        self.nmn = {}
        for node_ in self.gs[level+1]:
            ch = self.gs[level+1].nodes[node_]['children']
            ad = dict.fromkeys(ch, node_)
            self.nmn.update(ad)

    def _collapse(self, level):
        """Make meta-links"""
        # contar as arestas entre os membros dos supervertices
        # ou montar lista com os vizinhos, depois contar quantas vezes cada membro ocorreu
        # ou montar dicionario em que o vertice eh chave e o sv eh o valor, ao iterar pelos vizinhos, jah considerar o sv correspondente
        # ou iterar pelas arestas, convertendo para as meta-arestas
        for e in self.gs[level].edges():
            mv1 = self.nmn[e[0]]
            mv2 = self.nmn[e[1]]
            if mv2 not in self.gs[level+1][mv1]:
                self.gs[level+1].add_edge(mv1, mv2, weight = 0)
            self.gs[level+1][mv1][mv2]['weight'] += 1
    def mkLayout(self, level=0, inherit=1):
        if inherit == 0:
            self.mkRawLayout(level)
        else:
            if level == 0:
                self.mkRawLayout(level)
            else:
                # put vertices in the centroid of its children
                pos_ = []
                for node in self.gs[level].nodes():
                    # if node has children:
                    if len(self.gs[level].nodes[node]['children']) > 0:
                        pos = self.npos[level-1][n.array(list(self.gs[level].nodes[node]['children']))]
                        pos_.append(pos.mean(0))
                    else:
                        pos_.append([0,0,0])
                self.npos[level] = n.array(pos_)
    def mkRawLayout(self, level):
        l = self.layouts[self.layout](self.gs[level], dim=self.dim)
        nodepos = n.array([l[i] for i in self.nodes])
        # edges = [list(i) for i in g.edges]
        # nodepos = (2*n.random.random((nn,3))-1).tolist()
        # self.llayouts[level] = (nodepos, edges))
        self.npos[level] = nodepos

class MLS2(MLS1):
    def __init__(self):
        MLS1.__init__(self)
    def mkLevelLayers(self, sep=1, axis=2):
        """
        sep : separation in normalized units (?)
        axis : 0, 1, 2 are x, y, z

        """
        for level in self.npos:
            if level != 0:
                self.npos[level][:,axis] += level * sep
        self.npos_ = n.vstack(self.npos.values())
        es = []
        disp = 0
        for g in range(len(self.gs)):
            es_ = [(i+disp, j+disp) for i, j in self.gs[g].edges]
            es.extend(es_)
            disp += self.gs[g].number_of_nodes()
        self.edges_ = es
