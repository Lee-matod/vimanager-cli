# -*- coding: utf-8 -*-

"""
The MIT License (MIT)

Copyright (c) 2023-present Lee-matod

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""
from typing import Optional, Tuple

import click
from colorama import Fore, Style

from .models import Playlist
from .utils import find_playlist, get_connection


@click.command()
@click.argument("playlist_db", type=click.File("rb"))
@click.argument("new_name", nargs=-1)
@click.option("--playlist", "playlist_name", help="The name of the playlist that will be renamed.")
def rename(playlist_db: click.File, new_name: Tuple[str, ...], playlist_name: Optional[str]) -> None:
    """Rename a playlist.

    If no playlist names are given, then it will open the database and output
    all playlists found, prompting a selection.

    This action cannot be undone.
    """
    conn = get_connection(playlist_db.name)
    cursor = conn.cursor()
    try:
        playlist = Playlist(*find_playlist(playlist_name, cursor), connection=conn)
        if not new_name:
            name = click.prompt(f"{Fore.BLACK}Please specify the new name that the playlist should receive")
        else:
            name = " ".join(new_name)
        confirm = click.confirm(
            f"Are you sure you want to rename {Fore.CYAN}{playlist.name}{Fore.RESET} "
            f"to {Fore.YELLOW}{name}{Fore.RESET}?\nThis action cannot be undone."
        )
        if not confirm:
            raise click.Abort()
        cursor.execute("UPDATE Playlist SET name=? WHERE id=?", (name, playlist.id))
        conn.commit()
        click.echo(f"{Style.BRIGHT}{Fore.GREEN}Successfully renamed playlist.{Fore.RESET}")
    finally:
        cursor.close()
        conn.close()


@click.command()
@click.argument("playlist_db", type=click.File("rb"))
@click.argument("playlist_name", required=False)
def delete(playlist_db: click.File, playlist_name: Optional[str]) -> None:
    """Delete a playlist.

    If no playlist names are given, then it will open the database and output
    all playlists found, prompting a selection.

    This action cannot be undone.
    """
    conn = get_connection(playlist_db.name)
    cursor = conn.cursor()
    try:
        playlist = Playlist(*find_playlist(playlist_name, cursor), connection=conn)
        confirm = click.confirm(
            f"Are you sure you want to delete {Fore.CYAN}{playlist.name}{Fore.RESET}?\n"
            f"This action cannot be undone."
        )
        if not confirm:
            raise click.Abort()
        cursor.execute("DELETE FROM Playlist WHERE name=? AND id=?", (playlist.name, playlist.id))
        cursor.executemany(
            "DELETE FROM SongPlaylistMap WHERE songId=? AND playlistId=?",
            [(song.id, playlist.id) for song in playlist.songs],
        )
        conn.commit()
        click.echo(f"{Style.BRIGHT}{Fore.GREEN}Successfully deleted playlist.{Fore.RESET}")
    finally:
        cursor.close()
        conn.close()
