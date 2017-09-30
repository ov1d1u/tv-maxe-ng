import json

class Channel:
    def __init__(self, row, type, origin):
        self.type = type
        self.origin = origin
        self.id = str(row['id'])
        self.icon = row['icon']
        self.name = str(row['name'])
        self.streamurls = json.loads(row['streamurls'])
        self.params = json.loads(row['params'])
        if type == 'tv':
            self.guide = row['guide']
            self.audiochannels = json.loads(row['audiochannels'])