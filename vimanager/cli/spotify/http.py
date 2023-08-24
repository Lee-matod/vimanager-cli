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

import base64
import json
import pathlib
import time
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional

import click
import requests

from .models import Spotify

if TYPE_CHECKING:
    from typing_extensions import Self

__all__ = ("SpotifyClient",)

HERE = pathlib.Path(__file__).parent


class SpotifyClient:
    TOKEN_CACHE: ClassVar[pathlib.Path] = HERE / ".cache"

    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id: str = client_id
        self._client_secret: str = client_secret
        self._token: Optional[str] = None
        self._token_expires: Optional[float] = None

    def playlist_items(self, playlist_id: str, /) -> Optional[List[Spotify]]:
        response = requests.get(
            f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks",
            params={
                "additional_types": "track",
                "fields": "next,items(track(id,duration_ms,album,artists,name,external_urls))",
            },
            headers={"Authorization": self.token},
        )
        if not (300 > response.status_code >= 200):
            return
        tracks = response.json()
        track_items: List[Optional[Spotify]] = list(map(Spotify.from_data, tracks["items"]))
        while tracks["next"]:
            tracks = requests.get(tracks["next"], headers={"Authorization": self.token}).json()
            if tracks is None:
                break
            track_items.extend(map(Spotify.from_data, tracks["items"]))
        return [t for t in track_items if t]

    @classmethod
    def from_config(cls, filename: str, /) -> Self:
        path = pathlib.Path(filename)
        if not path.exists():
            raise click.ClickException(f"FileNotFound: {filename}")
        with path.open() as fp:
            try:
                data = json.load(fp)
            except json.JSONDecodeError:
                raise click.ClickException(f"file {filename} is not JSON decodable")
        try:
            client_id = data["client_id"]
            client_secret = data["client_secret"]
        except KeyError as exc:
            raise click.ClickException(f"KeyNotFound: {exc}")
        return cls(client_id, client_secret)

    @property
    def token(self) -> str:
        try:
            token = self._load_from_cache()
        except Exception:
            token = None
        if token is None or (self._token_expires is not None and self._token_expires > time.time()):
            auth = base64.b64encode((self._client_id + ":" + self._client_secret).encode("utf-8")).decode("utf-8")
            headers = {"Authorization": "Basic " + auth, "Content-Type": "application/x-www-form-urlencoded"}
            data = {"grant_type": "client_credentials"}

            js = requests.post("https://accounts.spotify.com/api/token", headers=headers, data=data).json()
            token = self._save_cache(js)
        self._token = token
        return token

    def _save_cache(self, data: Dict[str, Any]) -> str:
        token = data["access_token"]
        token_type = data["token_type"]
        expires_in = data["expires_in"] + time.time()
        with self.TOKEN_CACHE.open("w+") as fp:
            json.dump({"token": token, "expires_in": expires_in, "token_type": token_type}, fp)
        return f"{token_type} {token}"

    def _load_from_cache(self) -> Optional[str]:
        if self.TOKEN_CACHE.exists():
            with self.TOKEN_CACHE.open() as fp:
                data = json.load(fp)
            token = data["token"]
            token_type = data["token_type"]
            expires_at = data["expires_at"]
            if expires_at < time.time():
                self._token = token
                self._token_expires = expires_at
                return f"{token_type} {token}"
