import pandas as pd
import numpy.ma as ma

import pymongo
mclient = pymongo.MongoClient("mongodb://localhost:27017/")
db = mclient['boilerplate']
correlations = db['correlations']

print('read')
t=pd.read_csv('./E-MTAB-2706-query-results.tpms_.tsv',delimiter='\t',encoding='utf-8')
count = 0
while count in range(t.shape[0]//500):
    d1 = t.loc[count].values[2:].astype(float)
    n1 = t.loc[count][0]
    print(n1)
    corrs = []
    for i in range(t.shape[0]//500):
        d2 = t.loc[i].values[2:].astype(float)
        corr = ma.corrcoef(ma.masked_invalid(d1), ma.masked_invalid(d2))
        corrs.append(corr[0][1])
    correlations.insert_one({
        'gene': n1,
        'co': corrs
    })
    count += 1
# print('drop')
# tt=t.drop(['Gene ID', 'Gene Name'], axis=1)
# print('transpose')
# ttt = tt.T
# print('corr')
# ttt.info(memory_usage='deep')
# mcor3 = ttt.corr()
# print('ok')

