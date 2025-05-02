import hashlib

import pydub, pydub.utils, pyaudio, wave
import os, sys
import threading, time
import logging
import json
from tempfile import NamedTemporaryFile

logging.basicConfig(level=logging.DEBUG, filename="test.txt")

class Player:
    """
    Alternate player backend using `pyaudio` instead of `pygame.mixer` to play audio.

    May be more reliable than PyGame, due to the writer thread's direct control over the audio stream
    allowing for per-chunk data analysis and manipulation, however, may use more CPU due to
    math applied to the audio data (volume adjustment).
    """
    def __init__(self, rpc = None):

        # Settings
        self.__volume = 100

        self.__playing = False # playing audio
        self.__paused = False
        self.__file = None
        self.__chunk_total = 0
        self.__seek_to = 0
        self.__offset_time = 0 # visual offset

        self.__lyrics = ""
        self.__rpc = rpc

        self.__audio = pyaudio.PyAudio()
        self.__audio_stream = None
        self.__audio_thread = None
        self.__audio_samprate = 44100
        self.__audio_channels = 2
        self.__audio_sampwidth = 0

    @property
    def volume(self) -> int:
        """
        An int between 0 and 100.
        """
        return self.__volume

    @volume.setter
    def volume(self, new_vol: int):
        if new_vol <= 0:
            new_vol = 0
        elif new_vol >= 100:
            new_vol = 100
        
        self.__volume = new_vol

    def _write_audio(self, wf: wave.Wave_read):
        """
        Write audio into the stream.

        Automatically adjusts the volume of the audio before writing it into the stream.
        """
        # set these globally, so we can use them elsewhere
        self.__audio_sampwidth = wf.getsampwidth()
        self.__audio_channels = wf.getnchannels()
        self.__audio_samprate = wf.getframerate()

        self.__chunk_total = 0

        data = wf.readframes(1024)

        while self.__playing:
            if self.__seek_to:
                # Calculate the byte position from the time in seconds
                byte_position = int(self.__seek_to * self.__audio_sampwidth * self.__audio_channels * self.__audio_samprate)
                
                if byte_position < 0: # can't go under 0!
                    pass
                elif byte_position > os.path.getsize(self.__file.name): # don't go over!
                    pass
                else:
                    # Seek the file to the calculated byte position
                    # the wave module expects frame position, so some extra math is needed.
                    wf.setpos(byte_position // (self.__audio_sampwidth * self.__audio_channels))
                    
                    # Update the chunk total to reflect the new position
                    self.__chunk_total = byte_position
                self.__seek_to = 0

            if self.__paused:
                time.sleep(0.001)
                continue

            adjusted_data = bytearray()

            if data:
                # adjust volume
                for i in range(0, len(data), 2):  # Process two bytes at a time (16-bit PCM)
                    # Read two bytes (16-bit audio)
                    sample = int.from_bytes(data[i:i+2], byteorder='little', signed=True)
                    
                    # Adjust the volume by scaling the sample
                    adjusted_sample = int(sample * (self.__volume/100))

                    # Clip to valid 16-bit range and append to the adjusted audio
                    adjusted_sample = max(min(adjusted_sample, 32767), -32768)
                    adjusted_data.extend(adjusted_sample.to_bytes(2, byteorder='little', signed=True))

                self.__audio_stream.write(bytes(adjusted_data))
                self.__chunk_total += len(data)
                data = wf.readframes(1024)
            else:
                try:
                    self.stop(False)
                except RuntimeError: # can't join ourself
                    pass
                break


    def get_info(self, path: str, type: str):
        # fetch metadata
        audio_info = pydub.utils.mediainfo(path)
        # audio_info = TinyTag.get(path)
        tags = audio_info.get("TAG", "???")

        if type == "flac":
            artist = tags.get("ARTIST", None)
            album_artist = tags.get("album_artist")
            album = tags.get("ALBUM", None)
            title = tags.get("TITLE", None)
            track = int(tags.get("track", 0))
            genre = tags.get("GENRE", None)
        elif type == "mp3":
            artist = tags.get("artist", None)
            album_artist = tags.get("album_artist")
            album = tags.get("album", None)
            title = tags.get("title", None)
            track = int(tags.get("track", 0))
            genre = None

        duration = float(audio_info.get("duration", 0)) # should exist in all formats            

        return {"path": path, "type": type, "duration": duration, "artist": artist, "album_artist": album_artist, "album": album, "title": title, "genre": genre, "track": track}
    
    def play(self, path: str, input_format: str, preserve: bool = False):
        """
        Load a file into memory and start playback.

        Automatically converts the input file into a wav, storing it temporarily inside of
        the system's temp folder via `tempfile`.

        If 'preserve' is set, the converted file will be saved to a cache for later recall
        instead.
        """
        info = self.get_info(path, input_format)

        if preserve:
            tid = hashlib.sha256(f"{info["artist"]}{info["title"]}".encode()).hexdigest()
            if not os.path.isdir("./cache"):
                os.makedirs("./cache")
                with open("./cache/README.txt", "w") as f:
                    f.write("Here be dragons!\n\nIn most cases, Koulouri should handle all files within this "
                            "directory. You likely don't need to change anything.\n\nIf you must, only delete files!")

            if not os.path.exists(f"cache/{tid}.wav"):
                audio = pydub.AudioSegment.from_file(path, input_format).set_channels(2).set_sample_width(2)
                self.__audio_samprate = audio.frame_rate
                audio.export(f"cache/{tid}.wav", "wav")

            self.__file = open(f"cache/{tid}.wav", "rb")
        else:
            tmp = NamedTemporaryFile(prefix="koulouri-conv_")

            if sys.platform == "win32":
                tmp.delete = False
                tmp.close()

            self.__file = tmp

            audio = pydub.AudioSegment.from_file(path, input_format).set_channels(2).set_sample_width(2)
            self.__audio_samprate = audio.frame_rate
            audio.export(self.__file.name, "wav")

        wf = wave.open(self.__file.name, "rb") # we shouldn't be reading headers

        self.__audio_stream = self.__audio.open(format=pyaudio.paInt16,
                channels=wf.getnchannels(),
                rate=wf.getframerate(), # adapting early may avoid us headaches
                output=True,
                frames_per_buffer=1024)

        if self.__rpc: # update RPC stats
            if not self.__rpc.is_alive():
                self.__rpc.start()

            self.__rpc.title = info["title"]
            self.__rpc.artist = info["artist"]
            self.__rpc.album = info["album"]

        self.__playing = True

        self.__audio_thread = threading.Thread(target=self._write_audio, args=(wf,))
        self.__audio_thread.start()
        # self.__audio_stream.stop_stream()
        # self.__audio_stream.close()

        return info

    def stop(self, join: bool = True) -> None:
        self.__playing = False
        if self.__audio_thread and join:
            self.__audio_thread.join() # wait for the writer to stop writing

        if self.__audio_stream:
            self.__audio_stream.stop_stream()
            # self.__audio_stream.close()

        if self.__file and not self.__file.closed: # ensure temp files are closed properly
            self.__file.close()

        if sys.platform == "win32" and self.__file: # manually delete the temp file on windows systems
            os.unlink(self.__file.name)

        self.__lyrics = ""
        self.__file = None
        self.__active = False

    def pause(self):
        self.__paused = True

    def resume(self):
        self.__paused = False

    def seek(self, to: int):
        self.__seek_to = to
    
    def get_time(self) -> float:
        """
        Calculate the current playback time via the current chunk position.
        """
        return self.__chunk_total / (self.__audio_sampwidth * self.__audio_channels * self.__audio_samprate)
        # return self.__time
    
    def fetch_lyrics(self, path: str):
        lyric_file = path.split(".")[0]+".lrc"
        
        if not os.path.exists(lyric_file):
            return ""

        if self.__lyrics:
            return self.__lyrics

        with open(lyric_file, "r") as f:
            lyrics = []
            for line in f.read().split("\n"):
                try:
                    time_min = int(line[1:3])
                    time_sec = int(line[4:6])
                    time_mili = float(line[6:9])
                    lyric = line[10:]

                    lyrics.append({"lyric": lyric, "tmin": time_min, "tsec": time_sec, "tmil": time_mili})
                except:
                    pass
            self.__lyrics = lyrics

            return self.__lyrics

    def is_playing(self) -> tuple[bool, bool]:
        """
        Whether or not the player is playing audio.

        Returns a tuple of the `Player` status and the `pyaudio.Stream` status.
        """
        if self.__audio_stream:
            act = self.__audio_stream.is_active()
        else:
            act = False

        return (self.__playing, act)

    def is_active(self) -> bool: # compat?
        if self.__audio_thread:
            return self.__audio_thread.is_alive()
        else:
            return False


class Data:
    def __init__(self):
        self.__path = "kdata.json"
        self.__data = {}

        if not os.path.exists(self.__path):
            self.__data = {
                "favorites": [],
                "preferences": {
                    "cache_keepConversions": False
                },
                "playlists": []
            }
            self.__sync()
        else:
            self.__data = self.__load()

        self.__preferences = self.Preferences(self.__data["preferences"])
        self.__preferences.freeze()

    @property
    def preferences(self):
        """
        Get user preferences.
        """
        return self.__preferences

    class Preferences(dict):
        """
        Modified dictionary class that allows for the storage of user preferences, all while preventing
        further (potentially breaking) edits via freezing.

        Once frozen, two types of data are stored:

        FROZEN: Frozen data can be read from, but not modified. This is to protect against broken or odd Koulouri
        behavior caused by changing a value mid-session. These variables can be changed "upon restart" however.

        THAWED: Thawed data has no restrictions, acting like typical dict keys.

        Once frozen, new values are treated as "FROZEN", preventing any changes whatsoever. Additionally, data must be
        set to "THAWED" before the database is frozen.
        """
        def __init__(self, *args, **kwargs):
            # Preferences need to be frozen to avoid broken behavior.
            self.__frozen = False
            self.__thaw = []

            super().__init__(*args, **kwargs)

        @property
        def _frozen(self):
            """
            Whether the internal database is frozen.
            """
            return self.__frozen

        @property
        def _thawed(self):
            """
            Attributes that should be kept "thawed".
            """
            return self.__thaw

        # prevent dict modification if we're supposed to be frozen
        def __setitem__(self, key, value):
            if getattr(self, "_frozen", False) and key not in getattr(self, "_thawed", []):
                raise AttributeError(f"Cannot modify key '{key}', as database is frozen.")

            super().__setitem__(key, value)

        def freeze(self):
            """
            Freeze the preference database.

            Once frozen, any values marked as freezable will throw an AttributeError upon
            further attempts to edit them. The database cannot be unfrozen after this is
            called.
            """
            self.__frozen = True

        def set_thawed(self, key: str):
            """
            Make a value "thawed", allowing it to change even after
            the internal database is frozen.
            """

            if self.__frozen:
                raise AttributeError(f"Unable to modify a frozen database.")
            try:
                self[key]
            except KeyError as e:
                raise NameError(f"No such key '{key}' exists within current scope.") from e

            self.__thaw.append(key)

    def __sync(self):
        """
        Sync current memory data to disk.
        """
        with open(self.__path, "w") as f:
            json.dump(self.__data, f, indent=4)
    def __load(self):
        """
        Load disk to memory.
        """
        with open(self.__path, "r") as f:
            return json.load(f)

    def add_favorite(self, tid: str):
        """
        Add a track to the user's favorites.

        Returns False if the song is already a favorite.
        """
        favorites = self.__data.get("favorites", [])
        if tid not in favorites:
            self.__data["favorites"].append(tid)
            self.__sync()
            return True
        else:
            return False

    def remove_favorite(self, tid: str):
        """
        Remove a track from the user's favorites.

        Returns False if the track did not exist already.
        """

        favorites = self.__data.get("favorites", [])
        if tid in favorites:
            self.__data["favorites"].remove(tid)
            self.__sync()
            return True
        else:
            return False

    def toggle_favorite(self, tid: str):
        """
        Helper function that automatically adds or removes a track to the user's
        favorite.

        Returns the current status of `is_favorite` after toggling.
        """
        is_favorite = not self.is_favorite(tid)

        if is_favorite:
            self.add_favorite(tid)
        else:
            self.remove_favorite(tid)

        return self.is_favorite(tid)

    def is_favorite(self, tid: str):
        """
        Fetch a favorite song by its TID, if it exists.
        """
        favorites = self.__data.get("favorites", [])
        if tid in favorites:
            return True
        else:
            return False

    def create_playlist(self, name: str):
        playlists: list[dict] = self.__data.get("playlists", [])

        if name in [_.get("name", "Unnamed") for _ in playlists]:
            raise ValueError(f"Playlist with name {name} already exists!")
        else:
            playlists.append({
                "name": name,
                "tracks": []
            })
            self.__data["playlists"] = playlists
            self.__sync()

    def delete_playlist(self, name: str):
        playlists: list[dict] = self.__data.get("playlists", [])

        if name not in [_.get("name", "Unnamed") for _ in playlists]:
            raise ValueError(f"Playlist with name {name} does not exist!")
        else:
            playlists.remove([_ for _ in playlists if _["name"] == name][0])
            self.__data["playlists"] = playlists
            self.__sync()

    def get_playlist(self, name: str):
        playlists: list[dict] = self.__data.get("playlists", [])

        for playlist in playlists:
            if playlist.get("name", "Unnamed") == name:
                return playlist

        raise ValueError(f"Playlist with name {name} does not exist!")

    def get_all_playlists(self) -> list[dict]:
        return self.__data.get("playlists", [])

    def append_playlist_track(self, name: str, tid: str):
        playlists: list[dict] = self.__data.get("playlists", [])

        for playlist in playlists:
            if playlist.get("name", "Unnamed") == name:
                if tid not in playlist["tracks"]:
                    playlist["tracks"].append(tid)
                    self.__sync()
                    return
                else:
                    return

    def remove_playlist_track(self, name, tid: str):
        playlists: list[dict] = self.__data.get("playlists", [])

        for playlist in playlists:
            if playlist.get("name", "Unnamed") == name:
                if tid in playlist["tracks"]:
                    playlist["tracks"].remove(tid)
                    self.__sync()
                    return
                else:
                    return

    def toggle_playlist_track(self, name, tid: str):
        playlists: list[dict] = self.__data.get("playlists", [])

        for playlist in playlists:
            if playlist.get("name", "Unnamed") == name:
                if tid in playlist["tracks"]:
                    playlist["tracks"].remove(tid)
                    self.__sync()
                    return
                else:
                    playlist["tracks"].append(tid)
                    self.__sync()
                    return

# test = Player()

# test.play("/home/exii/Music/s777n/remains of a corrupted file/s777n - remains of a corrupted file.flac", "flac")
# time.sleep(3)
# test.pause()
# test.volume = 20
# time.sleep(3)
# test.resume()
# time.sleep(1)
# test.volume = 150
# print(test.volume)
# time.sleep(1)
# test.stop()
# time.sleep(3)

# test.play("/home/exii/Music/Catarinth/Catarinth - River Fallen/Catarinth - River Fallen - 02 River Fallen (Orchestral Version).flac", "flac")
# time.sleep(8)
# test.stop()
# time.sleep(3)
