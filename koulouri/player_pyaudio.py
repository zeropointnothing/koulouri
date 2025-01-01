import pydub, pydub.utils, pyaudio
import os, sys
import threading, time
import logging
import json
from tempfile import NamedTemporaryFile

logging.basicConfig(level=logging.DEBUG, filename="test.txt")

class Player:
    def __init__(self, rpc = None):
        
        # Settings
        self.__volume = 100

        self.__playing = False # playing audio
        self.__paused = False
        self.__file = None
        self.__time = 0
        self.__offset_time = 0 # visual offset

        self.__lyrics = ""
        self.__rpc = rpc

        self.__audio = pyaudio.PyAudio()
        self.__audio_stream = None
        self.__audio_thread = None
        self.__audio_samprate = 44100

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

    def _write_audio(self):
        """
        Write audio into the stream.

        Automatically adjusts the volume of the audio before writing it into the stream.
        """
        with open(self.__file.name, "rb") as f:
            data = f.read(1024)

            bytes_per_sample = 2  # 16-bit PCM
            channels = 2
            self.__time = 0 # reset timer
    
            while self.__playing:
                if self.__paused:
                    time.sleep(0.001)
                    continue
                # while data:

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

                    self.__time += len(data) / (bytes_per_sample * channels * self.__audio_samprate) # update timer
                    self.__audio_stream.write(bytes(adjusted_data))
                    data = f.read(1024)
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
    
    def play(self, path: str, input_format: str):
        """
        Load a file into memory and start playback.

        Automatically converts the input file into a wav, storing it temporarily inside of
        the system's temp folder via `tempfile`.
        """
        tmp = NamedTemporaryFile(prefix="koulouri-conv_")

        if sys.platform == "win32":
            tmp.delete = False
            tmp.close()

        self.__file = tmp

        audio = pydub.AudioSegment.from_file(path, input_format).set_channels(2).set_sample_width(2)
        self.__audio_samprate = audio.frame_rate
        info = self.get_info(path, input_format)

        audio.export(self.__file.name, "wav")

        self.__audio_stream = self.__audio.open(format=pyaudio.paInt16,
                channels=2,
                rate=audio.frame_rate, # adapting early may avoid us headaches
                output=True,
                frames_per_buffer=1024)

        self.__playing = True

        self.__audio_thread = threading.Thread(target=self._write_audio)
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
        ...
    
    def get_time(self) -> float:
        return self.__time
    
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
                "favorites": []
            }
            self.__sync()
        else:
            self.__data = self.__load()

    def __sync(self):
        """
        Sync current memory data to disk.
        """
        with open(self.__path, "w") as f:
            json.dump(self.__data, f)
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
