import pickle
import os

class SongMetadataFile():
    def __init__(self, path:str='cache/metadata.pkl') -> None:
        self.path = path
        if not os.path.isfile(path):
            self._created = False
        else:
            self._created = True
    
    def add_metadata(self, info: tuple[str, dict[str, str]]):
        current = self.read()
        
        current[info[0]] = info[1]
        
        with open(self.path, 'wb') as file:
            pickle.dump(current, file)
            self._created = True
            
    def read(self) -> dict[str, dict[str, str]]:
        if self._created:
            with open(self.path, 'rb') as file:
                return pickle.load(file)
        else:
            return {}
        
    def get_metadata(self, key) -> dict[str, str]|None:
        data = self.read()
        return data.get(key)
    
        
    