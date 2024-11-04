import pydub
import pydub.utils
from pygame import mixer
from pygame import error as pyerr
from tempfile import NamedTemporaryFile
from time import sleep

class Player:
    def __init__(self):
        mixer.init()
        
        self.mixer = mixer.music

        # Settings
        self.volume = 100

        # Status
        self.__playing = False # playing audio
        self.__active = False # loaded audio, ready to play
        self.__file = None

        pass

    def play(self, path: str, input_format: str):
        """
        Load a file into memory and start playback.

        Automatically converts the input file into a wav, storing it temporarily inside of
        the system's temp folder via `tempfile`.

        Returns song information.
        """
        tmp = NamedTemporaryFile(prefix="takali-conv_") # create a temp file to write the conversion to
        self.__file = tmp
        # print(tmp.name)

        audio = pydub.AudioSegment.from_file(path, input_format)
        info = self.get_info(path, input_format)

        audio.export(self.__file.name, "wav")
        # audio.export(self.__file, "wav")


        self.mixer.load(self.__file.name)
        self.mixer.play()

        self.__playing = True
        self.__active = True

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

        if self.__file and not self.__file.closed: # ensure temp files are closed properly
            self.__file.close()

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
        """
        self.mixer.unpause()
        self.__playing = True

    def seek(self, to: int):
        try:
            self.mixer.set_pos(to)
            return True
        except pyerr:
            return False

    def change_volume(self, by: int):
        new_vol = self.mixer.get_volume()+(by/100)

        if new_vol <= 0:
            new_vol = 0.0
        elif new_vol >= 1.0:
            new_vol = 1.0

        self.mixer.set_volume(new_vol)

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
