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
import pathlib
import shutil
import tempfile
from typing import Any, Dict, Literal, Optional

import click
from colorama import Back, Fore, Style
from yt_dlp import YoutubeDL  # type: ignore

from vimanager.models import Playlist
from vimanager.utils import find_playlist, get_connection

from .ffmpeg import convert


@click.command()
@click.argument("playlist_db", type=click.File("rb"))
@click.argument("playlist_name", required=False)
@click.option(
    "--audio-format",
    "-a",
    type=click.Choice(["flac", "m4a", "mp3", "ogg", "opus", "wav"]),
    default="mp3",
    help="The audio format in which",
)
@click.option("--output-dir", "-o", help="Directory where downloaded songs will be saved.")
def download(
    playlist_db: click.File,
    playlist_name: str,
    audio_format: Literal["flac", "m4a", "mp3", "ogg", "opus", "wav"],
    output_dir: Optional[str],
):
    """Download a playlist using the track ID and YouTube Music.

    FFmpeg is required to be installed for this to work. For more information, see https://ffmpeg.org/.

    If no playlist names are given, then it will open the database and output
    all playlists found, prompting a selection.
    """
    if not shutil.which("ffmpeg"):
        click.echo(f"{Fore.RED}FFmpeg executable not detected. Please install through https://ffmpeg.org/download.")
        return
    conn = get_connection(playlist_db.name)
    cursor = conn.cursor()
    try:
        playlist = Playlist(*find_playlist(playlist_name, cursor), connection=conn)
    finally:
        cursor.close()
        conn.close()

    output_folder = pathlib.Path(output_dir or playlist.name)
    if not output_folder.exists():
        output_folder.mkdir()
    if not output_folder.is_dir():
        click.echo(f"{Fore.RED}Provided output folder ({output_folder}) is not a directory.")
        return
    if audio_format == "m4a":
        ytdl_format = "bestaudio[ext=m4a]/bestaudio/best"
    elif audio_format == "opus":
        ytdl_format = "bestaudio[ext=webm]/bestaudio/best"
    else:
        ytdl_format = "bestaudio"

    click.echo(f"{Style.BRIGHT}* Starting track download. Saving output to {Fore.YELLOW}{output_folder.absolute()}")

    with tempfile.TemporaryDirectory() as tmpfolder:
        tmpdir = pathlib.Path(tmpfolder)
        handler = YoutubeDL(
            {
                "outtmpl": f"{tmpfolder}/%(id)s.%(ext)s",
                "format": ytdl_format,
                "quiet": True,
                "no_warnings": True,
                "encoding": "UTF-8",
                "retries": 5,
            }
        )
        for track in playlist.songs:
            click.echo(
                f"\nDownloading {Fore.YELLOW}{track.title}{Fore.RESET} - "
                f"{Fore.GREEN}{track.artist}{Fore.RESET} ({Fore.BLUE}{track.id}{Fore.RESET})."
            )
            data = download_track(handler, f"https://music.youtube.com/watch?v={track.id}")
            if not data:
                click.echo(f"  {Style.DIM}Retrying with www.youtube.com.")
                data = download_track(handler, f"https://www.youtube.com/watch?v={track.id}")
                if not data:
                    continue
            click.echo(f"  {Style.BRIGHT}{Fore.GREEN}Successfully downloaded data.")
            click.echo(
                f"  {Style.DIM}Converting downloaded file to desired audio format: "
                f"{Fore.MAGENTA}{audio_format}{Fore.RESET}"
            )
            temp_file = tmpdir / f"{data['id']}.{data['ext']}"
            success = convert(temp_file, output_folder / f"{track.title} - {track.artist}.{audio_format}", audio_format)
            if success:
                click.echo(f"  {Back.GREEN}Successfully downloaded track.{Back.RESET}")
            else:
                click.echo(f"  {Back.RED}Converting file failed.{Back.RESET}")


def download_track(handler: YoutubeDL, url: str, /) -> Optional[Dict[str, Any]]:
    try:
        data: Optional[Dict[str, Any]] = handler.extract_info(url, download=True)  # type: ignore
        if not data:
            raise RuntimeError("no download info found")
    except Exception as exc:
        click.echo(f"{Back.RED}Failed to download track:{Back.RESET} {exc}")
        return
    return data  # type: ignore
