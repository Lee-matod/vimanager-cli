# vimanager

A command-line tool written in Python that enhances the management of your playlists in the [ViMusic](https://github.com/vfsfitvnm/ViMusic) application.

_**NOTE:** This is an unofficial tool that is not maintained nor run by the developers of ViMusic._

# Installing and updating

Python 3.8 or higher is required. To install or update it, simply run the following command depending on your operating system.
**Windows:**

```shell
py -3 -m pip install -U git+https://github.com/Lee-matod/vimanager-cli
```

**Linux/MacOS:**

```shell
python3 -m pip install -U git+https://github.com/Lee-matod/vimanager-cli
```

Once installed, run `vimanager --help` for a help menu and more information on how to use the playlist manager.

# Getting your playlists as a database file

To function properly, this tool requires an SQLite database file that has your playlists saved in it. You can obtain this file by following the instructions below.

1. Open ViMusic.
2. Open the Configuration menu.
3. Go to the Database tab.
4. Click on Backup.
5. Save the backup file to the desired destination.

Similarly, once you have finished editing your playlists, click on `Restore` instead of `Backup` and select the file you edited to update the application with your new items.

# License

This project is Licensed under the [MIT](https://github.com/Lee-matod/vimanager-cli/blob/main/LICENSE) License.
