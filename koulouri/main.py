import argparse
import json
import os, sys
import hashlib
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide" # hide pygame welcome
from player import Player
from time import sleep, time

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--play", help="Play a song, artist, or albumb.", type=int)
parser.add_argument("-l", "--list", help="List all available songs, albums, or artists.", action="store_true")
parser.add_argument("-r", "--refresh", help="Refresh Koulouri's song cache.", action="store_true")
parser.add_argument("-c", "--curses", help="Run the Curses-based frontend instead.", action="store_true")
parser.add_argument("-v", "--version", help="Print Koulouri's version, then exit.", action="store_true")
parser.add_argument("--album", help="Set supported commands to Album Mode.", action="store_true")
parser.add_argument("--add-source", help="Add a folder to your library.", action="append")

VERSION = "2.0.0"

def assemble_songs(dir):
    output = []

    for song in os.listdir(dir):
        if os.path.isdir(f"{dir}/{song}"):
            output.extend(assemble_songs(f"{dir}/{song}")) # recursive
        elif song.split(".")[-1] in ["flac", "mp3", "wav"]:
            output.append((f"{dir}/{song}", song.split(".")[-1]))
        # print(song.split("."))

    return output

def generate_cache(dir):
    songs = assemble_songs(dir)
    song_meta = []

    plr = Player()

    for song in songs:
        info = plr.get_info(song[0], song[1])
        # create a unique id for each track that can persist
        tid = hashlib.sha256(f"{info["artist"]}{info["title"]}".encode()).hexdigest()
        song_meta.append({"id": tid, "info": info})

    plr.exit()

    return song_meta

def fetch_cache(force: bool = False, sources: list | None = None) -> dict:
    out = []
    if not os.path.exists("songcache.json") or force:
        user = os.environ.get('USER', os.environ.get('USERNAME', "user"))
        paths = [f"/home/{user}/Music", f"C:/Users/{user}/Music"]
        if sources:
            paths.extend(sources)
        print("fetching metadata...")
        for path in paths:
            try:
                song_meta = generate_cache(path)
                out.extend(song_meta)
            except FileNotFoundError:
                continue
        
        if out:
            with open("songcache.json", "w") as f:
                json.dump(out, f)
                return out
        else:
            raise FileNotFoundError("Unable to locate music folder!")

    with open("songcache.json", "r") as f:
        return json.load(f)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(sys.argv[0]))) # ensure we run from the same place every time.c
    args = parser.parse_args()

    if args.version:
        print(f"koulouri v{VERSION} ({os.getcwd()})")
        parser.exit()

    if args.curses:
        from tui import Window
        try:
            from discord import RPC
            rpc = RPC()
            plr = Player(rpc)
        except ModuleNotFoundError: # optional RPC modules not installed
            plr = Player()
        import curses

        stdscr = curses.initscr()
        win = Window(plr, stdscr)
        win.main()

    elif args.play != None:
        print("fetching media...")
        # songs = assemble_songs("/home/exii/Music")
        # songs = sorted(songs, key=lambda d: d["track"])
        song_meta = fetch_cache()
        songs = sorted(song_meta, key=lambda d: d["info"]["album"])
        song = songs[args.play]

        if not args.album:
            plr = Player()
            info = plr.play(song["info"]["path"], song["info"]["type"])

            print(f"Playing {info["title"]} by {info["artist"]}...")
            print("Press q<ENTER> to quit or h<ENTER> for commands.")

            try:
                while plr.is_playing():
                    sleep(1)
                    user_inp = input("> ")

                    if user_inp.lower() == "q":
                        raise KeyboardInterrupt("user abort")
                    elif user_inp.lower().startswith("seek"):
                        cmd, to = user_inp.split(" ")
                        plr.seek(int(to))
                    elif user_inp.lower() == "p":
                        plr.pause()
                        paused = True
                    elif user_inp.lower() == "u":
                        plr.resume()
                        paused = False
                    elif user_inp.lower() == "+":
                        plr.change_volume(10)
                        print(f"Volume now at {round(plr.mixer.get_volume(), 2)}")
                    elif user_inp.lower() == "-":
                        plr.change_volume(-10)
                        print(f"Volume now at {round(plr.mixer.get_volume(), 2)}")

            except KeyboardInterrupt:
                plr.stop()
        if args.album:
            song_meta = fetch_cache()
            
            plr = Player()
            
            albums = list(dict.fromkeys([_["info"]["album"] for _ in song_meta]))

            queue = [_ for _ in song_meta if _["info"]["album"] == albums[args.play]]
            queue = sorted(queue, key=lambda d: d["info"]["track"])
            queue_index = 0

            print(f"Playing album '{albums[args.play]}' by {queue[0]["info"]["album_artist"]}...")
            print("Press q<ENTER> to quit or h<ENTER> for commands.")

            try:
                while queue_index < len(queue):
                    paused = False
                    print(f"Playing {queue[queue_index]["info"]["title"]} by {queue[queue_index]["info"]["artist"]}...")
                    plr.play(queue[queue_index]["info"]["path"], queue[queue_index]["info"]["type"])

                    while plr.is_playing()[1] or paused:
                        sleep(1)
                        user_inp = input("> ")

                        if user_inp.lower() == "q":
                            raise KeyboardInterrupt("user abort")
                        elif user_inp.lower().startswith("seek"):
                            cmd, to = user_inp.split(" ")
                            plr.seek(int(to))
                        elif user_inp.lower() == "s":
                            break
                        elif user_inp.lower() == "p":
                            plr.pause()
                            paused = True
                        elif user_inp.lower() == "u":
                            plr.resume()
                            paused = False
                        elif user_inp.lower() == "r":
                            queue_index -= 1
                            break
                        elif user_inp.lower() == "+":
                            plr.change_volume(10)
                            print(f"Volume now at {round(plr.mixer.get_volume(), 2)}")
                        elif user_inp.lower() == "-":
                            plr.change_volume(-10)
                            print(f"Volume now at {round(plr.mixer.get_volume(), 2)}")

                    plr.stop() # ensure the song is over
                    queue_index += 1
            except KeyboardInterrupt:
                plr.stop()



    elif args.refresh:
        fetch_cache(True, args.add_source)
    elif args.list:
        song_meta = fetch_cache()
        songs = sorted(song_meta, key=lambda d: d["info"]["album"])

        print("Your Library:")
        for i, song in enumerate(songs):
            print(f"{i} : {song["info"]["artist"]} - {song["info"]["title"]}")
