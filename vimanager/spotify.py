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
from typing import Any, Dict, List, Optional

import click
import spotdl  # type: ignore
import spotipy  # type: ignore
from colorama import Back, Fore, Style

from .utils import get_connection

_SPOTIFY_PLAYLIST_URL = re.compile(r"https?://open.spotify.com/playlist/(?P<id>[a-zA-Z0-9]+)")


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
        try:
            data = spotify_client.playlist_items(playlist_id)  # type: ignore
        except spotipy.SpotifyException as exc:
            raise click.ClickException(f"Could not find playlist items: {exc}")
        if not data:
            click.echo(f"{Back.RED}Playlist is empty or not found.")
            return
        tracks: List[Dict[str, Any]] = data["items"]
        while data["next"]:
            click.echo(f"{Style.DIM}{Fore.BLUE}Received NEXT page in items data.{Style.RESET_ALL}")
            data = spotify_client.next(data)  # type: ignore
            if data is None:
                break
            tracks.extend(data["items"])
        click.echo(
            f"Retrieved {Style.RESET_ALL}{Fore.RED}{len(tracks)}{Fore.RESET} tracks from playlist.{Style.RESET_ALL}"
        )

        client = spotdl.Spotdl(client_id, client_secret)
        songs = [to_song(track_data) for track_data in tracks]
        for song in songs.copy():
            if not song:
                songs.remove(song)
                continue
            url = client.get_download_urls([song])
            if url and url[0]:
                # We don't actually need the URL, just the ID
                song.download_url = url[0].split("=")[1]
                click.echo(
                    f"{Style.DIM}Found download URL for {Style.RESET_ALL}{Fore.CYAN}{song.name}{Fore.RESET}: "
                    f"{Fore.MAGENTA}{url[0]}{Style.RESET_ALL}"
                )
            else:
                # SpotDL throws an error whenever an exception occurs, so no need to echo it
                songs.remove(song)

        click.echo(
            f"Creating new playlist {Fore.BLUE}{playlist_id}{Fore.RESET} "
            f"with {Fore.RED}{len(songs)}{Fore.RESET} tracks."
        )
        cursor.execute("SELECT id FROM Playlist")
        playlist_pos = calculate_plpos([x[0] for x in cursor.fetchall()])

        cursor.execute("INSERT INTO Playlist VALUES (?, ?, NULL)", (playlist_pos, playlist_id))
        cursor.executemany(
            "INSERT INTO SongPlaylistMap VALUES (?, ?, ?)",
            # This `if song` check is purely for type checkers not to complain
            [(song.download_url, playlist_pos, idx) for idx, song in enumerate(songs) if song],
        )
        cursor.executemany(
            "INSERT OR IGNORE INTO Song VALUES (?, ?, ?, ?, ?, NULL, ?)",
            [
                (
                    song.download_url,
                    song.name,
                    song.artist,
                    f"{(song.duration // 1000) // 60}:{(song.duration // 1000) % 60}",
                    song.cover_url,
                    song.duration,
                )
                for song in songs
                if song  # Same as above
            ],
        )
        conn.commit()
        click.echo(f"{Style.BRIGHT}{Fore.GREEN}Successfully created playlist.{Style.RESET_ALL}")
    finally:
        click.echo(f"\033[?25h")  # get_download_urls hides the cursor
        cursor.close()
        conn.close()


def calculate_plpos(current_ids: List[int], /) -> int:
    for i in range(1, len(current_ids) + 1):
        if i not in current_ids:
            return i
    return len(current_ids) + 1


def to_song(data: Dict[str, Any]) -> Optional[spotdl.Song]:
    meta = data.get("track", {})
    track_id = meta.get("id")
    if not meta or not track_id:
        return

    album_meta = meta.get("album", {})
    artists = [artist["name"] for artist in meta.get("artists", [])]
    release_date = album_meta.get("release_date")

    return spotdl.Song.from_missing_data(  # type: ignore
        name=meta["name"],
        artists=artists,
        artist=artists[0],
        album_id=album_meta.get("id"),
        album_name=album_meta.get("name"),
        album_artist=album_meta.get("artists", [])[0]["name"] if album_meta.get("artists") else None,
        disc_number=meta["disc_number"],
        duration=meta["duration_ms"],
        year=release_date[:4] if release_date else None,
        date=release_date,
        track_number=meta["track_number"],
        tracks_count=album_meta.get("total_tracks"),
        song_id=meta["id"],
        explicit=meta["explicit"],
        url=meta["external_urls"]["spotify"],
        isrc=meta.get("external_ids", {}).get("isrc"),
        cover_url=max(album_meta["images"], key=lambda i: i["width"] * i["height"])["url"]
        if (len(album_meta.get("images", [])) > 0)
        else None,
    )
