import json

class Channel:
    def __init__(self, row, type):
        self.id = row['id']
        self.type = type
        self.icon = row['icon']
        self.name = row['name']
        self.streamurls = json.loads(row['streamurls'])
        self.params = json.loads(row['params'])
        if type == 'tv':
            self.guide = row['guide']
            self.audiochannels = json.loads(row['audiochannels'])