# takali 
a lightweight Python music player

# commands (terminal)

## play

`-p, --play INT`

plays a song from the `songcache`.

if `album` is set, will play an entire album instead. (see [album](#album))

## list

`-l, --list`

lists all the songs that takali can play.

if a `songcache` hasn't been created yet, it will create one to reduce fetch time for the next run. this file is named `songcache.json`.

if `album` is set, display entire albums. (see [album](#album))

## refresh

`-r, --refresh`

manually refreshes the `songcache`.

scans known media locations and assembles a list of song metadata. the results will be saved in a file name `songcache.json` for further use.

## album

`--album`

the album flag. for commands that support it, will switch them to 'album mode'.

# credits

takali wouldn't be possible without these projects <3:

- [pydub](https://github.com/jiaaro/pydub) (wav conversion/metadata gathering) - jiaaro
- [pygame](https://github.com/pygame/pygame) (audio playback) - the PyGame team
- [ffmpeg](https://github.com/FFmpeg/FFmpeg) (the actuall wav conversion) - the FFmpeg team

