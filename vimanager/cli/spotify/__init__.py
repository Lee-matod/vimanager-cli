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
import re
import time
from typing import List, Optional

import click
import ytmusicapi as ytm  # type: ignore
from colorama import Back, Fore, Style

from vimanager.models import Song
from vimanager.utils import get_connection

from .http import SpotifyClient
from .matching import add_best_match
from .models import YouTube

__all__ = ("spotify",)

_SPOTIFY_PLAYLIST_URL = re.compile(r"https?://open.spotify.com/playlist/(?P<id>[a-zA-Z0-9]+)")
_SPOTIFY = f"{Style.BRIGHT}{Fore.GREEN}[SPOTIFY]{Style.RESET_ALL} "
_YOUTUBE = f"{Style.BRIGHT}{Fore.RED}[YOUTUBE]{Style.RESET_ALL} "


@click.command()
@click.argument("playlist_db", type=click.File("rb"))
@click.argument("playlist_url")
@click.option("--client-id", default="5f573c9620494bae87890c0f08a60293", help="Your Spotify client ID.")
@click.option("--client-secret", default="212476d9b0f3472eaa762d90b19b0ba8", help="Your Spotify client secret.")
@click.option(
    "--config",
    type=click.File("rb"),
    help="The name of the configuration file where your client ID and secret are stored.",
)
def spotify(
    playlist_db: click.File, playlist_url: str, client_id: str, client_secret: str, config: Optional[click.File]
):
    """Copy a Spotify playlist and add it to your list.

    If provided with a config file, it should be JSON where the key that points to
    the client ID is named 'client_id', and the key that points to the client secret
    is named 'client_secret'.
    """
    matched = _SPOTIFY_PLAYLIST_URL.fullmatch(playlist_url.split("?")[0])
    if not matched:
        raise click.ClickException("invalid Spotify playlist URL")
    if not config and not (client_id and client_secret):
        raise click.ClickException("Spotify client ID and secret not provided")

    if config is not None:
        spotify_client = SpotifyClient.from_config(config.name)
    else:
        assert client_id and client_secret
        spotify_client = SpotifyClient(client_id, client_secret)

    conn = get_connection(playlist_db.name)
    cursor = conn.cursor()
    playlist_id = matched.groupdict()["id"]
    try:
        click.echo(f"{_SPOTIFY}Looking up playlist {Fore.YELLOW}{playlist_id}{Fore.RESET}.")
        tracks = spotify_client.playlist_items(playlist_id)
        if not tracks:
            raise click.ClickException(f"{_SPOTIFY}{Back.RED}Playlist not found or is empty.{Back.RESET}")
        click.echo(f"{_SPOTIFY}Retrieved {Style.RESET_ALL}{Fore.RED}{len(tracks)}{Fore.RESET} tracks from playlist.")

        yt_client = ytm.YTMusic()
        isrc_urls: List[str] = []
        songs: List[Song] = []
        for track in tracks:
            time.sleep(1)
            click.echo(
                f"{_SPOTIFY}Searching for {Fore.CYAN}{track.name}{Fore.RESET}"
                f" by {Fore.YELLOW}{track.artist}{Fore.RESET}"
            )
            if track.isrc:
                click.echo(f"    {_YOUTUBE}{Style.DIM}Track has ISRC. Looking it up with YouTube Music.")
                isrc_results: List[YouTube] = [
                    yt for yt in map(YouTube.from_data, yt_client.search(track.isrc, "songs")) if yt  # type: ignore
                ]
                isrc_urls = [result.url for result in isrc_results]
                success = add_best_match(track, isrc_results, songs)
                if success:
                    continue
                click.echo(f"    {_YOUTUBE}{Fore.RED}ISRC did not match.{Fore.RESET}")
            query = f"{', '.join(track.artists)} - {track.name}"
            click.echo(f"{_YOUTUBE}Looking up {Fore.YELLOW}{query}{Fore.RESET} with YouTube Music.")
            results: List[YouTube] = [
                yt for yt in map(YouTube.from_data, yt_client.search(query)) if yt  # type: ignore
            ]
            click.echo(f"    {_YOUTUBE}Retrieved {Fore.RED}{len(results)}{Fore.RESET} results.")
            isrc_result = next((r for r in results if r.url in isrc_urls), None)
            if isrc_result:
                minutes, seconds = divmod(isrc_result.duration, 60)
                songs.append(
                    Song(
                        isrc_result.video_id,
                        isrc_result.name,
                        isrc_result.author,
                        duration=f"{minutes}:{seconds}",
                        thumbnail=track.cover_url or "",
                    )
                )
                click.echo(
                    f"    {_SPOTIFY}{Style.DIM}One of the results had ISRC found in cache:{Style.RESET_ALL} "
                    f"{Fore.MAGENTA}{isrc_result.url}"
                )
                continue
            success = add_best_match(track, results, songs, 70)
            if success:
                continue
            click.echo(f"{_YOUTUBE}{Back.RED}No match found for {query}{Back.RESET}")
        click.echo(
            f"Creating new playlist {Fore.BLUE}{playlist_id}{Fore.RESET} "
            f"with {Fore.RED}{len(songs)}{Fore.RESET} tracks."
        )
        cursor.execute("SELECT id FROM Playlist")
        playlist_pos = calculate_plpos([x[0] for x in cursor.fetchall()])

        cursor.execute("INSERT INTO Playlist VALUES (?, ?, NULL)", (playlist_pos, playlist_id))
        cursor.executemany(
            "INSERT INTO SongPlaylistMap VALUES (?, ?, ?)",
            [(song.id, playlist_pos, idx) for idx, song in enumerate(songs)],
        )
        cursor.executemany(
            "INSERT OR IGNORE INTO Song VALUES (?, ?, ?, ?, ?, NULL, ?)",
            [(song.id, song.title, song.artist, song.duration, song.thumbnail_url, song.duration) for song in songs],
        )
        conn.commit()
        click.echo(f"{Style.BRIGHT}{Fore.GREEN}Successfully created playlist.{Style.RESET_ALL}")
    finally:
        cursor.close()
        conn.close()


def calculate_plpos(current_ids: List[int], /) -> int:
    for i in range(1, len(current_ids) + 1):
        if i not in current_ids:
            return i
    return len(current_ids) + 1
