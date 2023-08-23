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
from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional

import click
from colorama import Fore, Style

from ..models import Playlist
from ..utils import find_playlist, get_connection

if TYPE_CHECKING:
    from typing_extensions import Annotated


@click.command()
@click.argument("playlist_db", type=click.File("rb"))
@click.argument("playlist_name", required=False)
@click.option(
    "--order-by",
    type=click.Choice(("artist", "duration", "title"), case_sensitive=False),
    default="title",
    help="How the playlist should be sorted.",
)
@click.option(
    "--sorting",
    type=click.Choice(("ASC", "DEC"), case_sensitive=False),
    default="DEC",
    help="The type of sorting to use: ascending or decending.",
)
def sort(
    playlist_db: click.File,
    playlist_name: Optional[str],
    order_by: Annotated[Literal["artist", "duration", "title"], click.Choice],
    sorting: Annotated[Literal["ASC", "DEC"], click.Choice],
):
    """Sort the order of songs in a playlist by different criteria.

    If no playlist names are given, then it will open the database and output
    all playlists found, prompting a selection.

    Order by defaults to the title of the song. Sorting defaults to decending.
    """
    conn = get_connection(playlist_db.name)
    cursor = conn.cursor()
    try:
        playlist = Playlist(*find_playlist(playlist_name, cursor), connection=conn)
        ordered = sorted(
            ((t.id, getattr(t, order_by), getattr(t, "title")) for t in playlist.songs),
            key=lambda x: x[1:],
            reverse=sorting == "ASC",
        )

        confirm = click.confirm(
            f"Are you sure you want to sort {Style.BRIGHT}{Fore.CYAN}{playlist.name}{Style.RESET_ALL} "
            f"by {Style.BRIGHT}{Fore.YELLOW}{order_by}{Style.RESET_ALL} "
            f"in {Style.BRIGHT}{Fore.RED}{sorting.lower()}ending{Style.RESET_ALL} order?\n"
            "This action cannot be undone."
        )
        if not confirm:
            raise click.Abort()
        cursor.executemany(
            "UPDATE SongPlaylistMap SET position=? WHERE songId=? AND playlistId=?",
            [(idx, song[0], playlist.id) for idx, song in enumerate(ordered)],
        )
        conn.commit()
        click.echo(f"{Style.BRIGHT}{Fore.GREEN}Successfully sorted playlist.{Fore.RESET}")

    finally:
        cursor.close()
        conn.close()
