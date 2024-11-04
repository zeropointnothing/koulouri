import curses
from time import sleep
from main import fetch_cache
from player import Player

class Window:
    def __init__(self, player: Player, stdscr: curses.window):
        self.stdscr = stdscr
        self.player = player
        self.songs = []
        
        self.h, self.w = self.stdscr.getmaxyx()

        self.__user_inp = ""
        self.__running = True
        self.__mode = "single"
        self.__index = 0
        self.__offset = 0

    def main(self):
        self.stdscr.nodelay(True)
        curses.noecho()
        song_meta = fetch_cache()
        self.songs = sorted(song_meta, key=lambda d: d["album"])
        selected_song = None

        try:
            while self.__running:
                sleep(0.05)
                k = self.stdscr.getch() # to reload xy
                self.h, self.w = self.stdscr.getmaxyx()

                for i, song in enumerate(self.songs[self.__offset:self.h-3]):
                    entry = f"{i}: {song["artist"]} - {song["title"]}"
                    entry_trimmed = entry[:self.w-3] + (entry[self.w-3:] and '...')
                    self.stdscr.addstr(i, 0, entry_trimmed)
                    self.stdscr.clrtoeol()

                self.stdscr.addstr(self.h-3, 0, self.__user_inp)
                self.stdscr.clrtoeol()

                # CONTROLS

                if k in [curses.KEY_BACKSPACE, 127]:
                    self.__user_inp = self.__user_inp[:len(self.__user_inp)-1]
                elif k in [curses.KEY_ENTER, 10, 13]:
                    try:
                        k = int(self.__user_inp)
                        self.__index = k
                        self.__user_inp = ""
                        if k in range(len(self.songs)-1):

                            selected_song = self.songs[self.__index]
                            self.player.stop() # ensure that we stop anything currently playing
                            self.player.play(selected_song["path"], selected_song["type"])
                            song_len = selected_song["duration"]
                        else:
                            continue
                    except:
                        sleep(0.005)
                        continue
                elif k == -1:
                    pass
                else:
                    self.__user_inp += chr(k)

                if not selected_song:
                    continue


                # progress bar / now playing
                prog_bar = "="*round(self.w*((self.player.mixer.get_pos()/1000)/song_len))
                now_playing = f"{selected_song["artist"]} - {selected_song["title"]}, [{self.__mode.upper()}]"
                nplaying_trimmed = now_playing[:self.w-3] + (now_playing[self.w-3:] and '...')
                # prog_bar = self.player.mixer.get_pos()/1000
                try:
                    self.stdscr.addstr(self.h-1, 0, f"{prog_bar}")
                except:
                    selected_song = None
                    pass
                self.stdscr.addstr(self.h-2, 0, nplaying_trimmed)

                self.stdscr.refresh()
        except KeyboardInterrupt:
            self.player.stop()

    def play_single(self, index: int):
        self.__index = index
        
        self.main()
