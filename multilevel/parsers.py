import networkx as x, numpy as n
import pickle

class GMLParserGeneric:
    def __init__(self):
        self._getNodes()
        self._getEdges()
        self._mkNXRepr()

    def _getNodes(self):
        self.nodes = []
        for line in self.lines:
            if line.startswith('id '):
                self.nodes.append(int(line.split(' ')[1]))
        # missing = [i for i in range(max(self.nodes)+1) if i not in self.nodes]
        # assert len(missing) == 0
        # does not follow the pattern: '/home/renato/Dropbox/Public/doc/avlab/OrlandoCoelho22022014_anon.gml'

    def _getEdges(self):
        self.edges = []
        for i in range(len(self.lines)):
            line = self.lines[i]
            if line.startswith('source '):
                n1 = int(line.split(' ')[1])
                line2 = self.lines[i+1]
                assert line2.startswith('target ')
                n2 = int(line2.split(' ')[1])
                self.edges.append((n1,n2))

    def _mkNXRepr(self):
        self.g = x.Graph()
        self.g.add_nodes_from(self.nodes)
        self.g.add_edges_from(self.edges)

    def getSimpleRepr(self):
        pass

class GMLParser(GMLParserGeneric):
    def __init__(self, fpath):
        self.fpath = fpath
        with open(fpath, 'r') as f:
            self.text_ = f.read()
            self.text = self.text_.replace("\t", '')
            self.lines = self.text.split("\n")
            self.lines = [i.strip() for i in self.lines]
        GMLParserGeneric.__init__(self)

class GMLParserDB(GMLParserGeneric):
    def __init__(self, data):
        self.text_ = data
        self.text = self.text_.replace("\t", '')
        self.lines = self.text.split("\n")
        self.lines = [i.strip() for i in self.lines]
        GMLParserGeneric.__init__(self)

def parseNetworkData(network_item):
    ni = network_item
    if ni['layer'] == 0 and ni['filename'].endswith('.gml'):
        return GMLParserDB(ni['data']).g
    elif ni['layer'] > 0:
        return pickle.loads(ni['data'])
    else:
        raise NotImplementedError('only GML and pickle.dumps of networkX graphs are currently implemented')

def parseBiNcol(fname):
    data = n.loadtxt(fname, skiprows=0, dtype=str)
    g = x.Graph()
    for row in data:
        v1, v2, w = [int(i) for i in row]
        if v1 not in g.nodes():
            g.add_node(v1, ntype=0)
        if v2 not in g.nodes():
            g.add_node(v2, ntype=1)
        g.add_edge(v1, v2, weight=w)
    return g


