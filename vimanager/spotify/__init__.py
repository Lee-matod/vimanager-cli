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
import json
import re
import time
from typing import Dict, List, Optional

import click
import spotipy  # type: ignore
import ytmusicapi as ytm  # type: ignore
from colorama import Back, Fore, Style

from ..models import Song
from ..utils import get_connection
from .matching import get_best_match
from .models import Spotify, YouTube

_SPOTIFY_PLAYLIST_URL = re.compile(r"https?://open.spotify.com/playlist/(?P<id>[a-zA-Z0-9]+)")
_SPOTIFY = f"{Style.BRIGHT}{Fore.GREEN}[SPOTIFY]{Style.RESET_ALL} "
_YOUTUBE = f"{Style.BRIGHT}{Fore.RED}[YOUTUBE]{Style.RESET_ALL} "


@click.command()
@click.argument("playlist_db", type=click.File("rb"))
@click.argument("playlist_url")
@click.option("--client-id", help="Your Spotify client ID.")
@click.option("--client-secret", help="Your Spotify client secret.")
@click.option(
    "--config",
    type=click.File("rb"),
    help="The name of the configuration file where your client ID and secret are stored.",
)
def spotify(
    playlist_db: click.File,
    playlist_url: str,
    *,
    client_id: Optional[str],
    client_secret: Optional[str],
    config: Optional[click.File],
):
    """Copy a Spotify playlist and add it to your list.

    This requires a Spotify client ID and secret. For more information, see
    https://developer.spotify.com/documentation/web-api/concepts/apps.

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
        if config.name[-5:] != ".json":
            raise click.ClickException("expected a JSON config file with 'client_id' and 'client_secret' keys")
        with open(config.name) as fp:
            try:
                data = json.load(fp)
            except json.JSONDecodeError as exc:
                raise click.ClickException(f"could not decode config file: {exc}")
        try:
            client_id = data["client_id"]
            client_secret = data["client_secret"]
        except KeyError as exc:
            raise click.ClickException(f"could not locate {exc} in provided config file")
    assert client_id and client_secret
    conn = get_connection(playlist_db.name)
    cursor = conn.cursor()
    playlist_id = matched.groupdict()["id"]
    try:
        spotify_client = spotipy.Spotify(
            client_credentials_manager=spotipy.SpotifyClientCredentials(client_id, client_secret)
        )
        click.echo(f"{_SPOTIFY}Looking up playlist {Fore.YELLOW}{playlist_id}{Fore.RESET}.")
        try:
            data = spotify_client.playlist_items(playlist_id)  # type: ignore
        except spotipy.SpotifyException as exc:
            raise click.ClickException(f"{_SPOTIFY}{Back.RED}Could not find playlist items: {exc}")
        if not data:
            click.echo(f"{_SPOTIFY}{Back.RED}Playlist is empty or not found.")
            return
        tracks: List[Optional[Spotify]] = [Spotify.from_data(track) for track in data["items"]]
        while data["next"]:
            click.echo(f"    {_SPOTIFY}{Style.DIM}{Fore.BLUE}Found NEXT page in items data.")
            data = spotify_client.next(data)  # type: ignore
            if data is None:
                break
            tracks.extend([Spotify.from_data(track) for track in data["items"]])
        click.echo(f"{_SPOTIFY}Retrieved {Style.RESET_ALL}{Fore.RED}{len(tracks)}{Fore.RESET} tracks from playlist.")

        client = ytm.YTMusic()
        isrc_urls: List[str] = []
        songs: List[Song] = []
        for track in tracks:
            if track is None:
                continue
            time.sleep(1)
            incomplete_obj = Song(
                "", track.name, track.artist, duration=track.duration, thumbnail=track.cover_url or ""
            )
            click.echo(
                f"{_YOUTUBE}Searching for {Fore.CYAN}{track.name}{Fore.RESET}"
                f" by {Fore.YELLOW}{track.artist}{Fore.RESET}"
            )
            if track.isrc:
                click.echo(f"    {_SPOTIFY}{Style.DIM}Track has ISRC.")
                isrc_results: List[YouTube] = [
                    yt for yt in map(YouTube.from_data, client.search(track.isrc, "songs")) if yt  # type: ignore
                ]
                isrc_urls = [result.url for result in isrc_results]
                scores: Dict[YouTube, float] = {yt_track: track.compare(yt_track) for yt_track in isrc_results}
                if len(scores) > 0:
                    best_match = get_best_match(scores)
                    if best_match is not None:
                        incomplete_obj.id = best_match.video_id
                        songs.append(incomplete_obj)
                        click.echo(
                            f"    {_YOUTUBE}Found best match:{Style.RESET_ALL} {Fore.MAGENTA}{best_match.url}{Fore.RESET}"
                        )
                        continue
            if track.isrc:
                click.echo(f"    {_SPOTIFY}{Fore.RED}Unsuccessful ISRC.{Fore.RESET}")
            click.echo(f"{_YOUTUBE}Looking up using YouTube Music.")
            results: List[YouTube] = [
                yt
                for yt in map(YouTube.from_data, client.search(f"{', '.join(track.artists)} - {track.name}"))  # type: ignore
                if yt
            ]
            isrc_result = next((r for r in results if r.url in isrc_urls), None)
            if isrc_result:
                incomplete_obj.id = isrc_result.video_id
                songs.append(incomplete_obj)
                click.echo(
                    f"    {_SPOTIFY}{Style.DIM}Cached ISRC found:{Style.RESET_ALL} {Fore.MAGENTA}{isrc_result.url}"
                )
                continue
            filtered_results = {yt_track: track.compare(yt_track) for yt_track in results}

            if len(filtered_results) != 0:
                best_match = get_best_match(filtered_results, threshold=70)
                if best_match is not None:
                    incomplete_obj.id = best_match.video_id
                    songs.append(incomplete_obj)
                    click.echo(
                        f"    {_YOUTUBE}Found best match:{Style.RESET_ALL} {Fore.MAGENTA}{best_match.url}{Fore.RESET}"
                    )
                    continue
            click.echo(f"{_YOUTUBE}{Back.RED}No match found for {track.name} - {track.artist}{Back.RESET}")
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
