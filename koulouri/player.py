import pydub
import os, sys
import pydub.utils
from pygame import mixer
from pygame import error as pyerr
from tempfile import NamedTemporaryFile
import time

class Player:
    def __init__(self, rpc = None):
        mixer.init()
        
        self.mixer = mixer.music

        # Settings
        self.volume = 100

        # Status
        self.__playing = False # playing audio
        self.__active = False # loaded audio, ready to play
        self.__file = None
        self.__offset_time = 0 # visual offset
        
        # External
        self.__lyrics = ""
        self.__rpc = rpc

        pass

    def play(self, path: str, input_format: str):
        """
        Load a file into memory and start playback.

        Automatically converts the input file into a wav, storing it temporarily inside of
        the system's temp folder via `tempfile`.

        Returns song information.
        """
        tmp = NamedTemporaryFile(prefix="koulouri-conv_") # create a temp file to write the conversion to
        
        if sys.platform == "win32":
            tmp.delete = False # windows support
            tmp.close()

        self.__file = tmp
        # print(tmp.name)

        audio = pydub.AudioSegment.from_file(path, input_format)
        info = self.get_info(path, input_format)

        if self.__rpc: # update RPC stats
            if not self.__rpc.is_alive():
                self.__rpc.start()

            self.__rpc.title = info["title"]
            self.__rpc.artist = info["artist"]
            self.__rpc.album = info["album"]

        audio.export(self.__file.name, "wav")
        # audio.export(self.__file, "wav")


        self.mixer.load(self.__file.name)
        self.mixer.play()

        self.__playing = True
        self.__active = True
        self.__offset_time = 0

        return info

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
    
    def stop(self):
        """
        Stop playback and close the input file, if necessary.
        """
        self.mixer.stop()
        self.mixer.unload()

        if self.__file and not self.__file.closed: # ensure temp files are closed properly
            self.__file.close()

        if sys.platform == "win32" and self.__file: # manually delete the temp file on windows systems
            os.unlink(self.__file.name)

        self.__lyrics = ""
        self.__file = None
        self.__playing = False
        self.__active = False

    def exit(self):
        """
        Exit the mixer.

        Useful if you only need the player for info gathering.
        """
        mixer.quit()

    def pause(self):
        """
        Pause playback.
        """
        self.mixer.pause()
        self.__playing = False

    def resume(self):
        """
        Resume playback.

        Automatically shifts the `__start_time` variable so that it matches with
        the song after it resumes.
        """
        self.mixer.unpause()
        self.__playing = True

    def seek(self, to: int):
        try:
            self.__offset_time += to # offset to visuals; pygame doesn't store this for us

            # Ensure we don't go into the negatives
            new_pos = self.get_time()
            if new_pos < 0:
                self.__offset_time -= to  # undo the change if we have
                return False

            # Most accurate by restarting the playback
            self.mixer.stop()
            self.mixer.play(start=new_pos)

            if not self.__playing: # most likely paused, so we should ensure it stays that way
                self.mixer.pause()

            return True
        except Exception as e:
            print(f"Seek error: {e}")
            return False

    def get_time(self) -> float:
        """
        Get the current playtime in seconds.

        Should be more accurate when accounting for pausing than the mixer by calculating
        the time based on a shiftable start value.
        """
        return self.mixer.get_pos()/1000 + self.__offset_time

    def change_volume(self, by: int):
        new_vol = self.volume+by

        if new_vol <= 0:
            new_vol = 0
        elif new_vol >= 100:
            new_vol = 100

        self.volume = new_vol
        self.mixer.set_volume(new_vol/100)

    def is_playing(self):
        """
        Whether or not the player is currently playing.

        Returns a tuple of the `Player` status and the status reported by PyGame. These should match.
        """
        return (self.__playing, self.mixer.get_busy())
    
    def is_active(self):
        """
        Whether or not the player has a file loaded and ready to play.
        """
        return self.__active
    
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
