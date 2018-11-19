from pymodm import connect, MongoModel, fields
import pickle, pymongo
from bson.objectid import ObjectId
from .utils import absoluteFilePaths, fpath
from .parsers import GMLParser

class Connection:
    def __init__(self):
        mclient = pymongo.MongoClient("mongodb://localhost:27017/")
        self.db = mclient['boilerplate']
        self.layouts = self.db['layouts']
        self.layers = self.db['layers']
        self.netuploads = self.db['netuploads']

    def getNetLayout(self, netid, layout, dimensions, method, layer):
        """
        If layer == 0, method does not matter.

        In all other cases, each combination of these parameters gives
        us a new item in the collection.
        """
        if layer > 0:
            query = {'netid': netid, 'layout': layout, 'dimensions': dimensions, 'method': method, 'layer': layer}
        else:
            query = {'netid': netid, 'layout': layout, 'dimensions': dimensions, 'layer': layer}
        positions = self.layouts.find_one(query, {'positions': 1})
        return positions

    def setNetLayout(self, netid, layout, dimensions, method, layer, positions):
        if layer > 0:
            data = {'netid': netid, 'layout': layout, 'dimensions': dimensions, 'method': method, 'layer': layer, 'positions': positions}
        else:
            data = {'netid': netid, 'layout': layout, 'dimensions': dimensions, 'layer': layer, 'positions': positions}
        self.layouts.insert_one(data)

    def getNetLayer(self, netid, method, layer):
        if layer == 0:
            print('it is the network itself')
            query = {'_id': ObjectId(netid)}
            network_ = self.netuploads.find_one(query)
            network = ml.parsers.GMLParserDB(network_['data'])
        else:
            query = {'netid': netid, 'method': method, 'layer': layer}
            network_ = self.layers.find_one(query, {'network': 1})
            network = pickle.loads(network_['data'])
        return network

    def setNetLayer(self, netid, method, layer, network_coarsened):
        if layer == 0:
            print('it is the network itself')
        else:
            data = {'netid': netid, 'method': method, 'layer': layer, 'network': network_coarsened}
        self.layers.insert_one(data)




### Deprecated:
class Network(MongoModel):
    network = fields.BinaryField()
    filename = fields.CharField()
    def save(self, cascade=None, full_clean=True, force_insert=False):
        self.network = pickle.dumps(self.network)
        return super(Network, self).save(cascade, full_clean, force_insert)

class MongoConnect:
    def connect(self):
        self.connect = connect('mongodb://localhost:27017/multilevelDatabase')
    def clear(self):
        Network.objects.delete()

class PopulateNetworks:
    def populate(self):
        self.getFilenames()
        self.getFilenames2()
        self.addToDB()
    def addToDB(self):
        nets = [Network(GMLParser(i).g, i).save() for i in self.fnames_]
        # Network.object.bulk_create(nets)
    def getFilenames(self, adir='/home/renato/Dropbox/Public/doc/vaquinha/'):
        self.fnames = absoluteFilePaths(adir)
        self.fnames_ = [i for i in self.fnames if i.endswith('.gml')]
    def getFilenames2(self, adir='/home/renato/Dropbox/Public/doc/avlab/'):
        self.fnames = absoluteFilePaths(adir)
        self.fnames_ += [i for i in self.fnames if i.endswith('.gml')]

