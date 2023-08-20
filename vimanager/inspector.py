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
from typing import Optional

import click
from colorama import Back, Fore, Style

from .models import Playlist
from .utils import find_playlist, get_connection


@click.command()
@click.argument("playlist_db", type=click.File("rb"))
@click.argument("playlist_name", required=False)
def inspect(playlist_db: click.File, playlist_name: Optional[str]):
    """Inspect a ViMusic playlist from its backup database.
    
    If no playlist names are given, then it will open the database and output
    all playlists found, prompting a selection.
    """
    conn = get_connection(playlist_db.name)
    cursor = conn.cursor()
    try:
        playlist = Playlist(*find_playlist(playlist_name, cursor), connection=conn)
        tracks = playlist.songs
        if not tracks:
            click.echo(f"{Back.RED}Playlist is empty.{Back.RESET}")
            return
        max_artist_name = len(max([t.artist for t in tracks], key=len))
        max_song_name = len(max([t.title for t in tracks], key=len))
        index_padding = len(str(len(tracks)))

        fmt = (
            f"  {Fore.YELLOW}{{0:{index_padding}}}. "
            f"{Fore.GREEN}{{1.artist:{max_artist_name}}}{Fore.RESET} "
            f"{Fore.WHITE}{{1.title:{max_song_name}}} "
            f"{Fore.RED}{{1.id}}"
        )
        click.echo(f"\n{Style.BRIGHT}-*- {Fore.MAGENTA}#{playlist.id} {Fore.BLUE}{playlist.name}{Fore.RESET} -*-")
        click.echo(
            f"Found {Style.BRIGHT}{Fore.RED}{len(tracks)}{Style.RESET_ALL} total tracks in playlist; "
            f"{Style.BRIGHT}{Fore.RED}{len(set([t.artist.lower() for t in tracks]))}{Style.RESET_ALL} unique artists.\n"
        )
        click.echo(
            f"  {' ':{index_padding}}  "
            f"{Style.BRIGHT}{Back.BLACK}{Fore.CYAN}{'Artist':^{max_artist_name}}{Back.RESET} "
            f"{Back.BLACK}{'Song':^{max_song_name}}{Back.RESET} "
            f"{Back.BLACK}{'Song ID':^11}{Style.RESET_ALL}"
        )
        click.echo("\n".join(fmt.format(idx, t) for idx, t in enumerate(tracks, start=1)))
    finally:
        cursor.close()
        conn.close()
