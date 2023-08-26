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
from typing import List, Optional, Tuple

import click
from colorama import Back, Fore, Style

from ..models import Playlist, Song
from ..utils import find_playlist, get_connection


@click.command()
@click.argument("playlist_db", type=click.File("rb"))
@click.argument("playlist1_name", required=False)
@click.argument("playlist2_name", required=False)
@click.option("--name", "new_name", help="The name of the new playlist.")
@click.option(
    "--exclude-track",
    "--exclude-song",
    multiple=True,
    help="Song names to exclude from the new playlist. This option can be used multiple times.",
)
@click.option(
    "--exclude-artist",
    multiple=True,
    help="Artists to exclude from the new playlist. This option can be used multiple times.",
)
@click.option(
    "--case-sensitive",
    is_flag=True,
    help="Whether the provided excluded items should be case sensitive or not.",
    default=False,
)
def merge(
    playlist_db: click.File,
    playlist1_name: Optional[str],
    playlist2_name: Optional[str],
    new_name: Optional[str],
    exclude_track: Tuple[str, ...],
    exclude_artist: Tuple[str, ...],
    case_sensitive: bool,
):
    """Create a new playlist by merging two existing ones.

    If no playlist names are given, then it will open the database and output
    all playlists found, prompting a selection.

    Existing playlists are not modified. Only new ones are created.
    """
    conn = get_connection(playlist_db.name)
    cursor = conn.cursor()
    try:
        playlist1 = Playlist(*find_playlist(playlist1_name, cursor), connection=conn)
        playlist2 = Playlist(*find_playlist(playlist2_name, cursor), connection=conn)
        if playlist1 == playlist2:
            click.echo(f"{Back.RED}Cannot merge same playlist.{Back.RESET}")
            return
        click.echo(
            f"\n{Style.BRIGHT}* {Fore.CYAN}{playlist1.name}{Fore.RESET} has "
            f"{Fore.RED}{len(playlist1.songs)}{Fore.RESET} tracks.\n"
            f"* {Fore.CYAN}{playlist2.name}{Fore.RESET} has "
            f"{Fore.RED}{len(playlist2.songs)}{Fore.RESET} tracks."
        )
        cursor.execute("SELECT id FROM Playlist")
        merged_playlist = Playlist(
            calculate_plpos([x[0] for x in cursor.fetchall()]), new_name or f"{playlist1.name} | {playlist2.name}"
        )

        def discrim(track: Song) -> bool:
            title = track.title
            artist = track.artist
            if not case_sensitive:
                nonlocal exclude_artist, exclude_track
                title = title.casefold()
                artist = artist.casefold()
                exclude_track = tuple(map(str.casefold, exclude_track))
                exclude_artist = tuple(map(str.casefold, exclude_artist))
            return title not in exclude_track and artist not in exclude_artist

        playlist_tracks = set(filter(discrim, playlist1.songs)) | set(filter(discrim, playlist2.songs))
        click.echo(
            f"{Style.BRIGHT}* Excluding {Fore.RED}{len(exclude_track)}{Fore.RESET} tracks and "
            f"{Fore.RED}{len(exclude_artist)}{Fore.RESET} artists"
            f"{f' {Fore.MAGENTA}(case sensitive){Fore.RESET}' if case_sensitive else ''}."
        )
        click.echo(
            f"{Style.BRIGHT}* Creating new playlist {Fore.YELLOW}{merged_playlist.name}{Fore.RESET} with "
            f"{Fore.RED}{len(playlist_tracks)}{Fore.RESET} total tracks."
        )
        cursor.execute("INSERT INTO Playlist VALUES (?, ?, NULL)", (merged_playlist.id, merged_playlist.name))
        cursor.executemany(
            "INSERT INTO SongPlaylistMap VALUES (?, ?, ?)",
            [(song.id, merged_playlist.id, idx) for idx, song in enumerate(playlist_tracks)],
        )
        conn.commit()
        click.echo(f"{Style.BRIGHT}{Fore.GREEN}Successfully created playlist.{Style.RESET_ALL}")
    finally:
        cursor.close()
        conn.close()


@click.command()
@click.argument("playlist_db", type=click.File("rb"))
@click.argument("new_name", nargs=-1)
@click.option("--playlist", "playlist_name", help="The name of the playlist that will be renamed.")
def rename(playlist_db: click.File, new_name: Tuple[str, ...], playlist_name: Optional[str]):
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
def delete(playlist_db: click.File, playlist_name: Optional[str]):
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


def calculate_plpos(current_ids: List[int], /) -> int:
    for i in range(1, len(current_ids) + 1):
        if i not in current_ids:
            return i
    return len(current_ids) + 1
