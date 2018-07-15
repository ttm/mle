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
        self.gs = []
        self.npos = {}
        self.status = ''
    def setNetwork(self, network):
        self.g = network
        self.gs.append(self.g)
        self.nodes = tuple(self.g.nodes())
        self.nodes_ = set(self.nodes)
        self.status += 'networkset|'
    def mkMetaNetwork(self, level=-1, method='mod'):
        assert 'networkset' in self.status
        if level == -1:
            level = len(self.npos)
        if method == 'cp':
            per = set(x.periphery(g))
            cen = set(x.center(g))
            pc = per.union(cen)
            nodes = set(g.nodes())
            inter = nodes.difference(pc)
            gg = x.Graph()
            gg.add_node(0, label='center', weight=len(cen), children=cen)
            gg.add_node(1, label='intermediary', weight=len(inter), children=inter)
            gg.add_node(2, label='periphery', weight=len(per), children=per)
            # contar as arestas entre os membros dos supervertices
            # ou montar lista com os vizinhos, depois contar quantas vezes cada membro ocorreu
            # ou montar dicionario em que o vertice eh chave e o sv eh o valor, ao iterar pelos vizinhos, jah considerar o sv correspondente
    def collapse(self):
        for snode in self.snodes[-1]:
            # calculate centroid
            # give size in proportion to nchilds
            # make dictionary where each node is key and the snode is the value
            #   will be used for obtaining the super-edges
    def mkLayout(self, level=0, inherit=1):
        if inherit = 0:
            self.mkRawLayout(level)
        else:
            if level == 0:
                self.mkRawLayout(level)
            else:
                # put vertices in the centroid of its children
                pass
    def mkRawLayout(self, level):
        l = self.layouts[self.layout](self.gs[level], dim=self.dim)
        nodepos = n.array([l[i] for i in self.nodes])
        # edges = [list(i) for i in g.edges]
        # nodepos = (2*n.random.random((nn,3))-1).tolist()
        # self.llayouts[level] = (nodepos, edges))
        self.npos[level] = nodepos
