# koulouri 
a lightweight Python music player

## Discord RPC

Koulouri supports Discord RPC by default, but does not include the packages needed to make it functional.

to enable RPC, run the following commands:
- `pip install requests`
- `pip install https://github.com/qwertyquerty/pypresence/archive/master.zip`

## commands (terminal)

### play

`-p, --play INT`

plays a song from the `songcache`.

if `album` is set, will play an entire album instead. (see [album](#album))

### list

`-l, --list`

lists all the songs that Koulouri can play.

if a `songcache` hasn't been created yet, it will create one to reduce fetch time for the next run. this file is named `songcache.json`.

if `album` is set, display entire albums. (see [album](#album))

### refresh

`-r, --refresh`

manually refreshes the `songcache`.

scans known media locations and assembles a list of song metadata. the results will be saved in a file name `songcache.json` for further use.

### album

`--album`

the album flag. for commands that support it, will switch them to 'album mode'.

### tui

`-c, --curses`

start Koulouri using the built in TUI, powered by the Curses library.

note that curses support is only likely to work on UNIX/Linux systems, and Windows users may experience issues. thus, it is only imported when this flag is supplied.

## commands (tui)

commands for Koulouri's build in TUI (see [tui](#tui)).

### scroll up

`KEY_UP`

scrolls the track view up one.

### scroll down

`KEY_DOWN`

scrolls the track view down one.

### play

`INT`

play the selected song.

type in the track number, then press enter.

## credits

Koulouri wouldn't be possible without these projects <3:

- [pydub](https://github.com/jiaaro/pydub) (wav conversion/metadata gathering) - jiaaro
- [pygame](https://github.com/pygame/pygame) (audio playback) - the PyGame team
- [ffmpeg](https://github.com/FFmpeg/FFmpeg) (the actuall wav conversion) - the FFmpeg team
- curses (tui) - Ken Arnold, AT&T, and others
- [pypresence](https://github.com/qwertyquerty/pypresence) (Discord RPC) - QwertyQwerty