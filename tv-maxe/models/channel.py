import json
import paths

class Channel:
    def __init__(self, row, type='tv', origin=paths.LOCAL_CHANNEL_DB):
        row = dict(row)
        self.type = type
        self.origin = origin
        self.id = str(row['id'])
        self.icon = row['icon']
        self.name = str(row['name'])
        self.streamurls = json.loads(row['streamurls'])
        self.params = json.loads(row.get("params", "{}"))
        self.guide = row.get("guide", "")
        self.audiochannels = json.loads(row.get("audiochannels", "[]"))

    def args(self, url):
        return self.params.get(url, {})

    def to_dict(self):
        return {
            "id": self.id,
            "icon": self.icon,
            "name": self.name,
            "streamurls": json.dumps(self.streamurls),
            "params": json.dumps(self.params),
            "guide": self.guide,
            "audiochannels": json.dumps(self.audiochannels)
        }

    def __eq__(self, obj):
        if isinstance(obj, Channel):
            return self.id == obj.id
        return False