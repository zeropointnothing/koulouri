import curses
from time import sleep
from main import fetch_cache
from player import Player

class Window:
    def __init__(self, player: Player, stdscr: curses.window):
        self.stdscr = stdscr
        self.player = player
        self.songs = []
        self.queue = []

        self.h, self.w = self.stdscr.getmaxyx()

        self.__user_inp = ""
        self.__running = True
        self.__mode = "tracks"
        self.__index = -1
        self.__offset = 0

    def main(self):
        self.stdscr.nodelay(True)
        curses.noecho()
        self.stdscr.keypad(True)
        song_meta = fetch_cache()
        self.songs = sorted(song_meta, key=lambda d: d["album"])
        paused = False
        song_len = 0

        try:
            while self.__running:
                sleep(0.05)
                k = self.stdscr.getch() # to reload xy
                self.h, self.w = self.stdscr.getmaxyx()

                # track rendering
                for i, song in enumerate(self.songs[self.__offset:self.__offset+self.h-3]):
                    entry = f"{i+self.__offset}: {song["artist"]} - {song["title"]}"
                    entry_trimmed = entry[:self.w-3] + (entry[self.w-3:] and '...')
                    self.stdscr.addstr(i, 0, entry_trimmed)
                    self.stdscr.clrtoeol()

                self.stdscr.addstr(self.h-3, 0, self.__user_inp)
                self.stdscr.clrtoeol()

                # CONTROLS

                if k in [curses.KEY_BACKSPACE, 127]:
                    self.__user_inp = self.__user_inp[:len(self.__user_inp)-1]
                elif k == curses.KEY_DOWN:
                    self.__offset += 1
                    self.__offset %= (len(self.songs))
                    self.stdscr.clear()
                elif k == curses.KEY_UP:
                    self.__offset -= 1
                    self.__offset %= (len(self.songs))
                    self.stdscr.clear()
                elif k in [curses.KEY_ENTER, 10, 13]:
                    try:
                        k = int(self.__user_inp)
                        self.__user_inp = ""
                        if k in range(len(self.songs)):
                            self.queue.append(self.songs[k])
                        else:
                            continue
                    except:
                        sleep(0.005)
                        continue
                elif k in range(48, 58):
                    self.__user_inp += chr(k)
                elif k == -1:
                    pass
                elif chr(k) == "s":
                    self.player.stop()
                
                if (not self.player.is_playing()[1] and not paused) and (self.queue and self.__index < len(self.queue)-1):
                    self.__index += 1
                    selected_song = self.queue[self.__index]
                    self.player.stop() # ensure that we stop anything currently playing
                    self.player.play(selected_song["path"], selected_song["type"])
                    song_len = selected_song["duration"]

                if self.player.is_playing()[1] and selected_song:
                    try:
                        # progress bar / now playing
                        now_at = self.player.mixer.get_pos()/1000
                        prog_bar = "="*round((self.w-13)*((now_at)/song_len))
                        now_playing = f"{selected_song["artist"]} - {selected_song["title"]}, [{self.__mode.upper()}]"
                        nplaying_trimmed = now_playing[:self.w-3] + (now_playing[self.w-3:] and '...')
                        # prog_bar = self.player.mixer.get_pos()/1000
                        final_prog = f"{round(now_at//60):02d}:{round(now_at%60):02d}-{round(song_len//60):02d}:{round(song_len%60):02d} >{prog_bar}"
                        self.stdscr.addstr(self.h-1, 0, final_prog)
                        self.stdscr.clrtoeol()
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
