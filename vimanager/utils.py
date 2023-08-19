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
import sqlite3
from typing import List

import click
from colorama import Back, Fore, Style


def prompt_playlist(cursor: sqlite3.Cursor, /) -> str:
    playlist_mapping: List[str] = []
    available_playlist = cursor.execute("SELECT name FROM Playlist").fetchall()
    click.echo(f"{Style.BRIGHT}{Fore.WHITE}Found {len(available_playlist)} playlists:")
    for idx, name in enumerate(available_playlist, start=1):
        name = name[0]
        click.echo(f"{Fore.BLACK}{idx}. {Fore.CYAN}{name}")
        playlist_mapping.append(name)
    response = int(
        click.prompt(
            f"{Back.GREEN}Choose the index of the playlist to inspect",
            type=click.Choice(tuple(map(str, range(1, len(playlist_mapping) + 1)))),
            show_choices=False,
        )
    )
    return playlist_mapping[response - 1]


def get_connection(db: str, /) -> sqlite3.Connection:
    if not db[-3:] == ".db":
        raise click.FileError(db, "not a valid backup database")
    try:
        conn = sqlite3.connect(db)
    except Exception as exc:
        raise click.FileError(db, str(exc)) from exc
    return conn
