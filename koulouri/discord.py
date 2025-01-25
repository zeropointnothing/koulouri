from pypresence import Presence, ActivityType
from pypresence.exceptions import PipeClosed, ServerError
import time
import threading
import requests

"""
You need to upload your image(s) here:
https://discordapp.com/developers/applications/<APP ID>/rich-presence/assets
"""
class RPC:
    def __init__(self):
        self.client_id = "1079931412154691624"  # Enter your Application ID here.

        self.title = None
        self.artist = None
        self.album = None

        self.RPC = Presence(client_id=self.client_id)

        self.__running = False

    def get_musicbrainz_album_cover(self, artist, album):
        """
        Fetch a url to the album cover from coverartarchive, if any. 
        """
        # Search for the album on MusicBrainz
        search_url = f'https://musicbrainz.org/ws/2/release-group/'
        params = {
            'query': f'artist:{artist} AND release:{album}',
            'fmt': 'json',
            'limit': 1
        }
        response = requests.get(search_url, params=params)
        results = response.json()

        # Get the album's MusicBrainz ID
        if 'release-groups' in results and results['release-groups']:
            release_group_id = results['release-groups'][0]['id']
            cover_url = f'https://coverartarchive.org/release-group/{release_group_id}/front-500'  # 500px size
            return {"release": release_group_id, "cover": cover_url}
        else:
            return None

    def __watch_loop(self):
        title = self.title
        artist = self.artist
        album = self.album

        while self.__running:
            time.sleep(5)
            if self.artist != artist or self.album != album or self.title != title:
                try:
                    self.set_activity(self.title, self.artist, self.album)
                except PipeClosed: # lost connection to discord
                    self.RPC.close()
                    self.__running = False
                title, artist, album = self.title, self.artist, self.album

    def is_alive(self):
        """
        Whether or not the watcher thread is alive.
        """
        return self.__running

    def start(self):
        """
        Start up the RPC client and a watcher thread.

        The watcher thread will wait for changes to `artist`, `title`, or `album` and update
        when needed.
        """
        try:
            self.RPC.connect()
        except: # couldn't connect to discord.
            return
        self.__running = True
        threading.Thread(target=self.__watch_loop, daemon=True).start()

    def set_activity(self, title: str, artist: str, album: str):
        # Make sure you are using the same name that you used when uploading the image
        mb = self.get_musicbrainz_album_cover(artist, album)

        start_time=time.time() # Using the time that we imported at the start. start_time equals time.
        try:
            self.RPC.update(activity_type=ActivityType.LISTENING, 
                            details=f"{title}",
                            state=artist,
                            start=start_time,
                            large_image=mb["cover"],
                            large_text=album,
                            buttons=[{"label": "Album (MusicBrainz)", "url": f"https://musicbrainz.org/release-group/{mb['release']}"}] if mb else None)
        except ServerError:
            self.RPC.close()
            self.__running = False
