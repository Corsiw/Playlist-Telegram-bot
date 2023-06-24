class Playlist:
    def __init__(self, name: str = "Новый плейлист", tracks={}):
        self.name = name
        self.tracks = tracks

    def delete_track(self, num: int):
        return self.tracks.pop(num - 1)

    def add_track(self, track):
        self.tracks.append(track)
