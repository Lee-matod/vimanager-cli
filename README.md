[![PyPi](https://img.shields.io/pypi/v/vimanager-cli.svg)](https://pypi.python.org/pypi/vimanager-cli)
[![Python versions](https://img.shields.io/pypi/pyversions/vimanager-cli.svg)](https://pypi.python.org/pypi/vimanager-cli)
[![License](https://img.shields.io/pypi/l/vimanager-cli.svg)](https://github.com/Lee-matod/vimanager-cli/blob/main/LICENSE)

# vimanager

A command-line tool written in Python that enhances the management of your playlists in the [ViMusic](https://github.com/vfsfitvnm/ViMusic) application.

_**NOTE:** This is an unofficial tool that is not maintained nor run by the developers of ViMusic._

Along side with its various other functionalities, one of its key features is allowing you to move your [Spotify](https://open.spotify.com) playlists to ViMusic. To do this, a client ID and client secret are required. For more information, see the [Spotify API](https://developer.spotify.com/documentation/web-api/concepts/apps).  
_This feature is not natively supported. See [Spotify Support](https://github.com/Lee-matod/vimanager-cli#spotify-support) to install it._

# Installing and updating

Python 3.8 or higher is required. Depending on the version you wish to install, run the following command.

Once installed, run `vimanager --help` for a help menu and more information on how to use the playlist manager.

> Note that on some systems, you might have to replace `python3` with `py -3`.

### Stable

```sh
python3 -m pip install -U vimanager-cli
```

### Development

```sh
python3 -m pip install -U git+https://github.com/Lee-matod/vimanager-cli
```

### Spotify Support

```sh
python3 -m pip install -U "vimanager-cli[spotify]"
```

## Getting your playlists as a database file

To function properly, this tool requires an SQLite database that has your playlists saved in it. You can obtain this file by following the instructions below.

1. Open ViMusic.
2. Open the Configuration menu.
3. Go to the Database tab.
4. Click on Backup.
5. Save the backup file to the desired destination.

Similarly, once you have finished editing your playlists, click on `Restore` instead of `Backup` and select the file you edited to apply the changes made.

# License

This project is Licensed under the [MIT](https://github.com/Lee-matod/vimanager-cli/blob/main/LICENSE) License.
