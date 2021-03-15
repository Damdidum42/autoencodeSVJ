from module.DataLoader import DataLoader


class SignalElement(object):
    def __init__(self, path, name):
        self._hlf = None
        self._eflow = None
        self._hlf_to_drop = []
        self._name = name
        self._path = path
        self._loaded = False
    
    def keys(self):
        return [elt for elt in dir(self) if not elt.startswith('__')]
    
    def load(self, hlf=True, eflow=True, hlf_to_drop=['Energy', 'Flavor']):
        if all([hlf == self._hlf, self._eflow == eflow, set(self._hlf_to_drop) == set(hlf_to_drop)]):
            if self._loaded:
                return
        
        self._hlf = hlf
        self._eflow = eflow
        self._hlf_to_drop = hlf_to_drop
        self._loaded = True
        
        data_loader = DataLoader()
        
        (self.data,
         self.jets,
         self.event,
         self.flavor) = data_loader.load_all_data(self._path, self._name,
                                                  include_hlf=self._hlf, include_eflow=self._eflow,
                                                  hlf_to_drop=self._hlf_to_drop
                                                  )