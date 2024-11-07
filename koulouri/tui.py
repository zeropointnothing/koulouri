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

                if self.__mode == "tracks":
                    view = self.songs
                elif self.__mode == "queue":
                    view = self.queue
                elif self.__mode == "albums":
                    view = list(dict.fromkeys([(_["artist"], _["album"]) for _ in self.songs])) # remove duplicates
                    view = [{"artist": _[0], "title": _[1]} for _ in view] # convert back to dicts we can use

                # track rendering
                for i, song in enumerate(view[self.__offset:self.__offset+self.h-4]):
                    entry = f"{i+self.__offset}: {song["artist"]} - {song["title"]}"
                    entry_trimmed = entry[:self.w-3] + (entry[self.w-3:] and '...')
                    self.stdscr.addstr(i+1, 0, entry_trimmed)
                    self.stdscr.clrtoeol()

                self.stdscr.addstr(self.h-3, 0, self.__user_inp)
                self.stdscr.clrtoeol()

                # CONTROLS

                if k in [curses.KEY_BACKSPACE, 127]:
                    self.__user_inp = self.__user_inp[:len(self.__user_inp)-1]
                elif k == curses.KEY_DOWN and view:
                    self.__offset += 1
                    self.__offset %= (len(view))
                    self.stdscr.clear()
                elif k == curses.KEY_UP and view:
                    self.__offset -= 1
                    self.__offset %= (len(view))
                    self.stdscr.clear()
                elif k in [curses.KEY_ENTER, 10, 13]:
                    try:
                        k = int(self.__user_inp)
                        self.__user_inp = ""
                        if k in range(len(self.songs)) and self.__mode == "tracks":
                            self.queue.append(self.songs[k])
                        elif k in range(len(self.queue)) and self.__mode == "queue":
                            self.queue.remove(self.queue[k])

                            # adjust the index if we've moved positions
                            if self.__index >= k and self.__index > -1:
                                self.__index -= 1
                        elif k in range(len(view)) and self.__mode == "albums":
                            album = [_ for _ in self.songs if _["album"] == view[k]["title"]]
                            self.queue.extend(sorted(album, key=lambda d: d["track"]))
                        else:
                            continue
                        self.stdscr.clear()
                    except:
                        sleep(0.005)
                        continue
                elif k in range(48, 58):
                    self.__user_inp += chr(k)
                elif k == -1:
                    pass
                elif chr(k) == "q":
                    self.__mode = "queue"
                    self.__offset = 0
                    self.stdscr.clear()
                elif chr(k) == "t":
                    self.__mode = "tracks"
                    self.__offset = 0
                    self.stdscr.clear()
                elif chr(k) == "a":
                    self.__mode = "albums"
                    self.__offset = 0
                    self.stdscr.clear()
                elif chr(k) == "s":
                    self.player.stop()
                elif chr(k) == "+":
                    self.player.change_volume(10)
                elif chr(k) == "-":
                    self.player.change_volume(-10)
                elif chr(k) == " ":
                    paused = not paused

                    if paused:
                        self.player.pause()
                    else:
                        self.player.resume()

                if (not self.player.is_playing()[1] and not paused) and (self.queue and self.__index < len(self.queue)-1):
                    self.__index += 1
                    selected_song = self.queue[self.__index]
                    self.player.stop() # ensure that we stop anything currently playing
                    self.player.play(selected_song["path"], selected_song["type"])
                    song_len = selected_song["duration"]
                    paused = False

                try:
                    volume = round(self.player.mixer.get_volume()*100)
                    title_str = f"koulouri  / [{volume}%] / {self.__mode.upper()}"
                    title_mid = (self.w//2)-(len(title_str)//2)
                    self.stdscr.move(0, 0) # ensure title is cleared, since it may have left behind text in front of it
                    self.stdscr.clrtoeol()
                    self.stdscr.addstr(0, title_mid, title_str)
                    self.stdscr.refresh()
                except:
                    pass

                if self.player.is_active() and selected_song:
                    try:
                        # progress bar / now playing
                        now_at = self.player.mixer.get_pos()/1000
                        symbol = ">" if not paused else "#"
                        prog_bar = "="*round((self.w-13)*((now_at)/song_len))
                        now_playing = f"{self.__index+1} of {len(self.queue)}, {selected_song["artist"]} - {selected_song["title"]}"
                        nplaying_trimmed = now_playing[:self.w-3] + (now_playing[self.w-3:] and '...')
                        # prog_bar = self.player.mixer.get_pos()/1000
                        final_prog = f"{round(now_at//60):02d}:{round(now_at%60):02d}-{round(song_len//60):02d}:{round(song_len%60):02d} {symbol}{prog_bar}"
                        self.stdscr.addstr(self.h-1, 0, final_prog)
                        self.stdscr.clrtoeol()
                    except:
                        selected_song = None
                        pass
                    self.stdscr.addstr(self.h-2, 0, nplaying_trimmed)
                    self.stdscr.clrtoeol()

                    self.stdscr.refresh()
        except KeyboardInterrupt:
            self.player.stop()
            # restore terminal to normal state
            curses.echo()
            curses.endwin()
            self.stdscr.keypad(False)

    def play_single(self, index: int):
        self.__index = index
        
        self.main()
