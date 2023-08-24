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
from typing import Callable, Optional, Tuple, TypeVar

import click
from colorama import Back, Fore, Style

from ..models import Playlist
from ..utils import find_playlist, get_connection

T = TypeVar("T")
ItemT = TypeVar("ItemT")
COMPARE_FMT = f"  {Style.BRIGHT}{{0}}:  \t{Fore.RED}{{1}}{Fore.RESET} / {Fore.BLUE}{{2}}{Style.RESET_ALL}"
VERBOSE_FMT = (
    f"  [{Fore.BLUE}{{0.id}}{Fore.RESET}] {Style.BRIGHT}{{0.title}}"
    f"{Style.RESET_ALL} - {Fore.GREEN}{{0.title}}{Fore.RESET}"
)


@click.command()
@click.argument("playlist_db", type=click.File("rb"))
@click.argument("playlist_name", required=False)
@click.option(
    "--mobile",
    "-m",
    help="Whether to display the output in a simplified manner for small screens.",
    is_flag=True,
    default=False,
    type=bool,
)
def inspect(playlist_db: click.File, playlist_name: Optional[str], mobile: bool):
    """Inspect a playlist.

    If no playlist names are given, then it will open the database and output
    all playlists found, prompting a selection.

    Liked songs are highlighted in red.
    """
    conn = get_connection(playlist_db.name)
    cursor = conn.cursor()
    try:
        playlist = Playlist(*find_playlist(playlist_name, cursor), connection=conn)
        tracks = playlist.songs
        if not tracks:
            click.echo(f"{Back.RED}Playlist is empty.{Back.RESET}")
            return

        # Playlist info
        click.echo(f"\n{Style.BRIGHT}-*- {Fore.MAGENTA}#{playlist.id} {Fore.BLUE}{playlist.name}{Fore.RESET} -*-")
        click.echo(
            f"Found {Style.BRIGHT}{Fore.RED}{len(tracks)}{Style.RESET_ALL} total tracks in playlist; "
            f"{Style.BRIGHT}{Fore.RED}{len(set([t.artist.lower() for t in tracks]))}{Style.RESET_ALL} unique artists.\n"
        )
        if mobile:
            # Padding
            index_padding = len(str(len(tracks)))
            # Track headers
            click.echo(
                f"  {' ' * index_padding}  {Style.BRIGHT}{Back.BLACK}{Fore.CYAN}"
                f"Song - Artist [Song ID]{Style.RESET_ALL}"
            )
            # Track info
            click.echo(
                "\n".join(
                    [
                        f"  {Fore.YELLOW}{idx:{index_padding}}. "
                        + (f"{Style.BRIGHT}{Fore.RED}" if track.liked else f"{Fore.WHITE}")
                        + f"{track.title}{Style.RESET_ALL} - "
                        + f"{Fore.GREEN}{track.artist}{Fore.RESET} "
                        + f"{Style.DIM}[{Fore.BLUE}{track.id}{Fore.RESET}]{Style.RESET_ALL}"
                        for idx, track in enumerate(tracks, start=1)
                    ]
                )
            )
            return
        # Padding
        max_artist_name = len(max([t.artist for t in tracks], key=len))
        max_song_name = len(max([t.title for t in tracks], key=len))
        index_padding = len(str(len(tracks)))

        # Track column headers
        click.echo(
            f"  {' ':{index_padding}}  "
            f"{Style.BRIGHT}{Fore.CYAN}{Back.BLACK}{'Song':^{max_song_name}}{Back.RESET} "
            f"{Back.BLACK}{'Artist':^{max_artist_name}}{Back.RESET} "
            f"{Back.BLACK}{'Song ID':^11}{Style.RESET_ALL}"
        )

        # Track info
        for idx, track in enumerate(tracks, start=1):
            click.echo(
                f"  {Fore.YELLOW}{idx:{index_padding}}. "
                + (f"{Style.BRIGHT}{Fore.RED}" if track.liked else f"{Fore.WHITE}")
                + f"{track.title:{max_song_name}}{Style.RESET_ALL} "
                + f"{Fore.GREEN}{track.artist:{max_artist_name}} "
                + f"{Fore.BLUE}{track.id}"
            )
    finally:
        cursor.close()
        conn.close()


@click.command()
@click.argument("playlist_db", type=click.File("rb"))
@click.argument("playlist1_name", required=False)
@click.argument("playlist2_name", required=False)
@click.option("--verbose", "-v", is_flag=True, default=False, help="Whether unique and common items should be shown.")
def compare(playlist_db: click.File, playlist1_name: Optional[str], playlist2_name: Optional[str], verbose: bool):
    conn = get_connection(playlist_db.name)
    cursor = conn.cursor()
    try:
        if not playlist1_name:
            click.echo(f"{Style.DIM}Main playlist not provided. Please select one below.")
        playlist1 = Playlist(*find_playlist(playlist1_name, cursor), connection=conn)
        if not playlist2_name:
            click.echo(f"{Style.DIM}Target playlist not provided. Please select one below.")
        playlist2 = Playlist(*find_playlist(playlist2_name, cursor), connection=conn)
        if playlist1 == playlist2:
            click.echo(f"{Style.BRIGHT}* Cannot compare same playlist.")
            return
        click.echo(
            f"\n{Style.BRIGHT}-*- {Fore.MAGENTA}#{playlist1.id} {Fore.RED}{playlist1.name}{Fore.RESET} "
            f"vs {Fore.MAGENTA}#{playlist2.id} {Fore.BLUE}{playlist2.name}{Fore.RESET} -*-"
        )

        # TODO: This is a mess. I'll clean it up sometime in the future.

        # Track info
        songs1 = set(playlist1.songs)
        songs2 = set(playlist2.songs)
        common_songs = songs1 & songs2
        unique_songs1 = songs1 - songs2
        unique_songs2 = songs2 - songs1
        liked1, liked2 = compare_items(playlist1.songs, playlist2.songs, lambda i: filter(lambda s: s.liked, i))
        playtime1, playtime2 = compare_items(playlist1, playlist2, lambda i: sum([s.duration_seconds for s in i.songs]))
        avg_duration1 = playtime1 / len(playlist1.songs)
        avg_duration2 = playtime2 / len(playlist2.songs)
        click.echo(f"\n{Style.BRIGHT}{Back.BLACK}{Fore.CYAN}{'Tracks':^48}{Style.RESET_ALL}")
        click.echo(
            "\n".join(
                (
                    COMPARE_FMT.format("Total count", len(playlist1.songs), len(playlist2.songs)),
                    COMPARE_FMT.format("Unique songs", len(unique_songs1), len(unique_songs2)),
                    f"{Style.BRIGHT}  Common songs:  \t{Fore.YELLOW}{len(common_songs)}{Style.RESET_ALL}",
                    COMPARE_FMT.format("Liked songs", len(tuple(liked1)), len(tuple(liked2))),
                    COMPARE_FMT.format("Total playtime", largest_unit(playtime1), largest_unit(playtime2)),
                    COMPARE_FMT.format(
                        "Avg. song duration",
                        f"{round(avg_duration1 / 60, 2)}".replace(".", ":"),
                        f"{round(avg_duration2 / 60, 2)}".replace(".", ":"),
                    ),
                )
            )
        )
        if verbose:
            if unique_songs1:
                click.echo(f"\n{Style.BRIGHT}{Back.BLACK}{Fore.RED}{'Unique Tracks':^48}{Style.RESET_ALL}")
                click.echo("\n".join(map(VERBOSE_FMT.format, unique_songs1)))
            if unique_songs2:
                click.echo(f"\n{Style.BRIGHT}{Back.BLACK}{Fore.BLUE}{'Unique Tracks':^48}{Style.RESET_ALL}")
                click.echo("\n".join(map(VERBOSE_FMT.format, unique_songs2)))
            if common_songs:
                click.echo(f"\n{Style.BRIGHT}{Back.BLACK}{Fore.YELLOW}{'Common Tracks':^48}{Style.RESET_ALL}")
                click.echo("\n".join(map(VERBOSE_FMT.format, common_songs)))

        # Artist info
        artists1 = set(map(lambda s: s.artist, playlist1.songs))
        artists2 = set(map(lambda s: s.artist, playlist2.songs))
        common_artists = artists1 & artists2
        unique_artists1 = artists1 - artists2
        unique_artists2 = artists2 - artists1
        click.echo(f"\n{Style.BRIGHT}{Back.BLACK}{Fore.CYAN}{'Artists':^48}{Style.RESET_ALL}")
        click.echo(
            "\n".join(
                (
                    COMPARE_FMT.format("Total count", len(artists1), len(artists2)),
                    COMPARE_FMT.format("Unique artists", len(unique_artists1), len(unique_artists2)),
                    f"{Style.BRIGHT}  Common artists:  \t{Fore.YELLOW}{len(common_artists)}{Style.RESET_ALL}",
                )
            )
        )
        if verbose:
            if unique_artists1:
                click.echo(f"\n{Style.BRIGHT}{Back.BLACK}{Fore.RED}{'Unique Artists':^48}{Style.RESET_ALL}")
                click.echo("\n".join(unique_artists1))
            if unique_artists2:
                click.echo(f"\n{Style.BRIGHT}{Back.BLACK}{Fore.BLUE}{'Unique Artists':^48}{Style.RESET_ALL}")
                click.echo("\n".join(unique_artists2))
            if common_artists:
                click.echo(f"\n{Style.BRIGHT}{Back.BLACK}{Fore.YELLOW}{'Common Artists':^48}{Style.RESET_ALL}")
                click.echo("\n".join(common_artists))

    finally:
        cursor.close()
        conn.close()


def compare_items(item1: ItemT, item2: ItemT, /, callback: Callable[[ItemT], T]) -> Tuple[T, T]:
    return callback(item1), callback(item2)


def largest_unit(seconds: int, /) -> str:
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    unit = f"{seconds} seconds"
    if minutes:
        unit = f"{minutes}.{str(seconds)[:1]} minutes"
    if hours:
        unit = f"{hours}.{str(minutes)[:1]} hours"
    return unit
