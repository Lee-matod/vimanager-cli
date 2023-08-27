[![PyPi](https://img.shields.io/pypi/v/vimanager-cli.svg)](https://pypi.python.org/pypi/vimanager-cli)
[![Python versions](https://img.shields.io/pypi/pyversions/vimanager-cli.svg)](https://pypi.python.org/pypi/vimanager-cli)
[![License](https://img.shields.io/pypi/l/vimanager-cli.svg)](https://github.com/Lee-matod/vimanager-cli/blob/main/LICENSE)

# vimanager

A command-line tool written in Python that enhances the management of your playlists in the [ViMusic](https://github.com/vfsfitvnm/ViMusic) application.

_**NOTE:** This is an unofficial tool that is not maintained nor run by the developers of ViMusic._

Along side with its various other functionalities, a few of its key features are allowing you to move your [Spotify](https://open.spotify.com) playlists to ViMusic, and downloading your playlist tracks to your device.

_Due to other dependencies being needed, these features are not natively supported. See [All features](https://github.com/Lee-matod/vimanager-cli#all-features) for more information._

# Installing and updating

Python 3.8 or higher is required. Depending on the version you wish to install, run the appropriate command.

Once installed, run `vimanager --help` for a help menu and more information on how to use the playlist manager.

> Note that on some systems, you might have to replace `python3` with `py -3`.

## Stable

```sh
python3 -m pip install -U vimanager-cli
```

## Development

```sh
python3 -m pip install -U git+https://github.com/Lee-matod/vimanager-cli
```

## All features

Installing using this command includes the optional features listed below, which can also be installed seperatly.

```sh
python3 -m pip install -U "vimanager-cli[full]"
```

### Spotify Support

Copy your playlists from Spotify to ViMusic.

```sh
python3 -m pip install -U "vimanager-cli[spotify]"
```

### Download Support

Download the tracks in your playlist to your device.

```sh
python3 -m pip install -U "vimanager-cli[download]"
```

> _FFmpeg is required for this feature. If you do not have it installed on your device, see below for guidance._

#### Downloading FFmpeg

- [Windows Tutorial](https://windowsloop.com/install-ffmpeg-windows-10/)
- **MacOS** - `brew install ffmpeg`
- **Linux** - `sudo apt install ffmpeg` or whichever package manager you use.

## Getting your playlists as a database file

All of the feature in this tool require a database that has your playlists stored in it. You can easily obtain this file through the ViMusic application thanks to their backup feature. Follow the steps below.

1. Open ViMusic.
2. Open the Configuration menu.
3. Go to the Database tab.
4. Click on Backup.
5. Save the backup file to the desired destination.

Similarly, once you have finished editing your playlists, click on `Restore` instead of `Backup` and select the file you edited to apply the changes made.

# License

This project is Licensed under the [MIT](https://github.com/Lee-matod/vimanager-cli/blob/main/LICENSE) License.
