import numpy as n

def sNcol(nl1=100, nl2=100, ne=1000, wmax=10, fname='mfile'):
    vv = list(range(nl1 + nl2))
    v1 = vv[:nl1]
    v2 = vv[nl1:]
    l1 = n.random.choice(v1, ne)
    l2 = n.random.choice(v2, ne)
    w = n.random.randint(1, wmax + 1, ne)

    d = n.vstack( (l1, l2, w) ).T
    n.savetxt(fname + '.ncol', d, '%d')
    return l1, l2, w

def mkThem():
    sNcol(fname='../data/mfile')
    sNcol(200, 100, 2000, 10, '../data/mfile2')
    sNcol(150, 100, 2000, 40, '../data/mfile3')
