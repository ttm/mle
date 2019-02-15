# this script is dedicated to generating (dummy) evolving networks
# to aid development
import numpy as n
import json


def eNet(nnodes=100, nlinks=1000):
    edges_ = n.random.randint(0, nnodes, nlinks*2)
    edges = n.reshape( edges_, (nlinks, 2) )
    return edges

def wEvNet(nnodes, nlinks, fname, format_ = 'json'):
    edges = eNet(nnodes, nlinks).tolist()
    if format_ == 'raw':
        edges_ = '\n'.join(['%s %s' % (e[0], e[1]) for e in edges])
        with open(fname, 'w') as f:
            f.write(edges_)
    else:
        with open(fname, 'w') as f:
            json.dump(edges, f)
