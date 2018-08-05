from pymodm import connect, MongoModel, fields
import pickle
from .utils import absoluteFilePaths
from .parsers import GMLParser

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

