import sys
import threading
import time
import logging as log
import random
log.basicConfig(level=log.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

from PyQt5 import QtCore, QtWidgets
from player import Player
from main import fetch_cache, VERSION


class PlayerWorker(QtCore.QObject):
    started = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal()
    percentageChanged = QtCore.pyqtSignal(int)
    titleChanged = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._percentage = 0
        self._title = ""

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        if self._title == value:
            return

        self._title = value
        self.titleChanged.emit(self.title)

    @property
    def percentage(self):
        return self._percentage

    @percentage.setter
    def percentage(self, value):
        if self._percentage == value:
            return
        self._percentage = value
        self.percentageChanged.emit(self.percentage)

    def start(self):
        self.started.emit()

    def finish(self):
        self.finished.emit()


class Widget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(f"koulouri v{VERSION} - EARLY GUI")

        self.__length = 0
        self.__paused = False
        self.__alive = False
        self.__queue = []
        self.__song_list = [] # widgets
        self.__index = -1
        self.__current_song = None

        self.player = Player()

        # set up queue
        song_meta = fetch_cache()
        self.songs = sorted(song_meta, key=lambda d: d["info"]["album"])
        random.shuffle(self.songs)
        self.__queue = self.songs


        # QT Widgets

        songlistcont = QtWidgets.QGroupBox()
        songlistform = QtWidgets.QFormLayout()
        labellist = []
        for i, song in enumerate(self.songs):
            labellist.append(QtWidgets.QLabel(song["info"]["title"]))
            songlistform.addRow(labellist[i])
        songlistcont.setLayout(songlistform)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidget(songlistcont)
        scroll.setWidgetResizable(True)
        # scroll.setFixedHeight(200)


        self.volume = QtWidgets.QSlider()
        self.progress = QtWidgets.QProgressBar()
        self.label = QtWidgets.QLabel()
        self.play_button = QtWidgets.QPushButton("Start")
        self.pause_button = QtWidgets.QPushButton("Pause")
        self.next_button = QtWidgets.QPushButton("Next")
        self.previous_button = QtWidgets.QPushButton("Previous")


        self.volume.setValue(self.player.volume)


        lay = QtWidgets.QGridLayout(self)        
        lay.addWidget(scroll)
        lay.addWidget(self.label)
        lay.addWidget(self.play_button)
        lay.addWidget(self.pause_button)
        lay.addWidget(self.next_button)
        lay.addWidget(self.previous_button)
        lay.addWidget(self.volume)
        lay.addWidget(self.progress)

        self.play_button.clicked.connect(self.play)
        self.pause_button.clicked.connect(self.pause)
        self.next_button.clicked.connect(self.next)
        self.previous_button.clicked.connect(self.previous)
        self.volume.valueChanged.connect(self.volchange)

    def queue_thread(self, worker: PlayerWorker):
        """
        Queue management thread.

        Uses PlayerWorker to update the GUI in a QT compliant fashion.
        """
        # if not self.player.is_playing()[1]:
        #     self.player.change_volume(-70)
        #     info = self.player.play("/home/exii/Music/s777n/remains of a corrupted file/s777n - remains of a corrupted file.flac", "flac")
        #     log.debug(f"now playing: {info["type"]} of '{info['title']}'")

        #     self.__length = info["duration"]

        worker.start()
        while self.__alive:
            if (not self.player.is_playing()[1] and not self.__paused) and (self.__queue and self.__index < len(self.__queue)-1):                
                self.__index += 1
                self.__current_song = self.__queue[self.__index]
                self.player.stop() # ensure that we stop anything currently playing
                self.player.play(self.__current_song["info"]["path"], self.__current_song["info"]["type"])
                self.__length = self.__current_song["info"]["duration"]
                self.__paused = False


            progress = int((self.player.get_time()/self.__length)*100)
            worker.percentage = progress
            worker.title = f"{self.__current_song["info"]["artist"]} - {self.__current_song["info"]["title"]}"
            # print(worker.percentage)
            time.sleep(0.5)
        worker.finish()
        self.player.stop()

        worker.title = ""
        worker.percentage = 0

        log.debug("queue thread finished. (thread died?)")

    def play(self):
        if not self.__alive:
            self.launch()
        else:
            self.player.resume()
            self.__paused = False

    def pause(self):
        if self.player.is_playing()[0]:
            self.player.pause()
            self.__paused = True

    def next(self):
        if self.player.is_playing()[0]:
            self.player.stop()

    def previous(self):
        if self.player.get_time() > 5:
            self.__index -= 1
            self.player.stop()
            self.__current_song = None
        elif self.__index <= 0:
            pass
        else:
            self.__index -= 2
            self.player.stop()
            self.__current_song = None

    def volchange(self, to: int):
        log.debug(f"Updating Player volume to: {to}")
        self.player.volume = to

    def launch(self):
        worker = PlayerWorker()
        worker.percentageChanged.connect(self.progress.setValue)
        worker.titleChanged.connect(self.label.setText)
        worker.titleChanged.connect(lambda x: self.setWindowTitle(f"koulouri - {x}"))

        self.__alive = True
        threading.Thread(
            target=self.queue_thread,
            kwargs=dict(worker=worker),
            daemon=True,
        ).start()
        log.debug("started worker thread.")

    # ensure we cleanup before closing
    def closeEvent(self, a0):
        self.player.stop()
        log.info("graceful(?) program exit. goodbye!")
        return super().closeEvent(a0)


def launch_qt():
    """
    Helper function to launch the GUI.
    """
    app = QtWidgets.QApplication(sys.argv)
    w = Widget()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    launch_qt()