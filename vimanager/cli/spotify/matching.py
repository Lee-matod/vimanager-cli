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

import re
import unicodedata
from functools import lru_cache
from html.entities import name2codepoint
from itertools import product, zip_longest
from typing import TYPE_CHECKING, List, Tuple

import click
from colorama import Fore, Style
from rapidfuzz import fuzz

from vimanager.models import Song

if TYPE_CHECKING:
    from .models import Spotify, YouTube

__all__ = (
    "add_best_match",
    "artists_fixup",
    "clean_string",
    "fill_string",
    "main_artist",
    "other_artists",
    "slugify",
    "sort_strings",
    "title",
)

FORBIDDEN_WORDS = (
    "8daudio",
    "acapella",
    "acoustic",
    "bassboost",
    "bassboosted",
    "concert",
    "cover",
    "instrumental",
    "live",
    "live",
    "remaster",
    "remastered",
    "remix",
    "remix",
    "reverb",
    "reverb",
    "slowed",
)
CHAR_ENTITY_PATTERN = re.compile(r"&(%s);" % "|".join(name2codepoint))
DECIMAL_PATTERN = re.compile(r"&#(\d+);")
HEX_PATTERN = re.compile(r"&#x([\da-fA-F]+);")
QUOTE_PATTERN = re.compile(r"[\']+")
DISALLOWED_CHARS_PATTERN = re.compile(r"[^-a-zA-Z0-9]+")
DISALLOWED_UNICODE_CHARS_PATTERN = re.compile(r"[\W_]+")
DUPLICATE_DASH_PATTERN = re.compile(r"-{2,}")
NUMBERS_PATTERN = re.compile(r"(?<=\d),(?=\d)")


def add_best_match(track: Spotify, scores: List[YouTube], /, tracks: List[Song], threshold: float = 80) -> bool:
    filtered_results = {yt_track: track.compare(yt_track) for yt_track in scores}
    if len(filtered_results) != 0:
        sorted_scores = sorted(
            filtered_results.items(),
            key=lambda x: x[1] + bool(x[0].song),  # Prioritize verified songs over videos
            reverse=True,
        )
        if len(sorted_scores) > 0:
            best_match = sorted_scores[0]
            if best_match[1] > threshold:
                minutes, seconds = divmod(best_match[0].duration, 60)
                tracks.append(
                    Song(
                        best_match[0].video_id,
                        best_match[0].name,
                        best_match[0].author,
                        duration=f"{minutes}:{seconds}",
                        thumbnail=track.cover_url or "",
                    )
                )
                click.echo(
                    f"    {Style.BRIGHT}{Fore.RED}[YOUTUBE]{Style.RESET_ALL} "
                    f"Found best match:{Style.RESET_ALL} {Fore.MAGENTA}{best_match[0].url}"
                )
                return True
    return False


@lru_cache
def slugify(text: str) -> str:
    text = QUOTE_PATTERN.sub("-", text)
    text = CHAR_ENTITY_PATTERN.sub(lambda m: chr(name2codepoint[m.group(1)]), text)

    try:
        text = DECIMAL_PATTERN.sub(lambda m: chr(int(m.group(1))), text)
        text = HEX_PATTERN.sub(lambda m: chr(int(m.group(1), 16)), text)
    except Exception:
        pass

    text = unicodedata.normalize("NFKD", text).lower()
    text = QUOTE_PATTERN.sub("", text)
    text = NUMBERS_PATTERN.sub("", text)
    text = DISALLOWED_CHARS_PATTERN.sub("-", text)
    text = DUPLICATE_DASH_PATTERN.sub("-", text).strip("-")

    return text


def sort_strings(strings: List[str], based_on: List[str]) -> Tuple[List[str], List[str]]:
    strings.sort()
    based_on.sort()

    list_map = {value: index for index, value in enumerate(based_on)}

    strings = sorted(strings, key=lambda x: list_map.get(x, -1), reverse=True)

    based_on.reverse()

    return strings, based_on


def clean_string(words: List[str], string: str) -> str:
    string = slugify(string).replace("-", "")
    final: List[str] = []
    for word in words:
        word = slugify(word).replace("-", "")
        if word in string:
            continue
        final.append(word)
    final.sort()
    return "-".join(final)


def main_artist(song: Spotify, result: YouTube) -> float:
    if not result.artists:
        return 0
    song_artists = list(map(slugify, song.artist))
    result_artists = sort_strings(song_artists, list(map(slugify, result.artists)))[1]

    song_main_artist = slugify(song_artists[0])
    result_main_artist = result_artists[0]
    main_artist_match = 0

    if len(song.artists) > 1 and len(result.artists) == 1:
        for artist in map(slugify, song.artists[1:]):
            artist = "-".join(sorted(slugify(artist).split("-")))
            res_main_artist = "-".join(sorted(result_main_artist.split("-")))

            if artist in res_main_artist:
                main_artist_match += 100 / len(song.artists)

        return main_artist_match

    main_artist_match = fuzz.ratio(song_main_artist, result_main_artist)
    if main_artist_match < 50 and len(song_artists) > 1:
        for song_artist, result_artist in product(song_artists[:2], result_artists[:2]):
            new_artist_match = fuzz.ratio(song_artist, result_artist)

            if new_artist_match > main_artist_match:
                main_artist_match = new_artist_match

    return main_artist_match


def other_artists(song: Spotify, result: YouTube) -> float:
    if len(song.artists) == 1 or not result.artists:
        return 0

    song_artists, result_artists = sort_strings(list(map(slugify, song.artists)), list(map(slugify, result.artists)))
    song_artists = song_artists[1:]
    result_artists = result_artists[1:]

    artists_match = 0
    for song_art, res_art in zip_longest(song_artists, result_artists):
        art_match = fuzz.ratio(song_art, res_art)
        artists_match += art_match

    return artists_match / len(song_artists)


def artists_fixup(song: Spotify, result: YouTube, score: float) -> float:
    if score < 70 and len(result.artists) > 1 and len(song.artists) == 1:
        fixup = fuzz.ratio(slugify(result.name), slugify(f"{song.artist} - {song.name}"))
        if fixup >= 80:
            score = (score + fixup) / 2

    score = min(score, 100)

    if score > 70:
        return score

    channel_match = fuzz.ratio(slugify(song.artist), slugify(", ".join(result.artists)))
    if channel_match > score:
        score = channel_match
    if score <= 50:
        aritst_title_match = 0
        for artist in song.artists:
            slugged_artist = slugify(artist).replace("-", "")
            if slugged_artist in slugify(result.name).replace("-", ""):
                aritst_title_match += 1
        aritst_title_match = (aritst_title_match / len(song.artists)) * 100
        if aritst_title_match > score:
            score = aritst_title_match

    if score > 70:
        return score

    song_name = slugify(song.name)
    result_name = slugify(result.name)
    song_title = slugify(f"{', '.join(song.artists)} - {song.name}")

    has_main_artist = (score / (2 if len(song.artists) > 1 else 1)) > 50

    test1 = fill_string(song.artists, result_name, song_title)
    test2 = fill_string(song.artists, song_title, result_name)

    match_str = "-".join(sort_strings(test1.split("-"), test2.split("-"))[1]).replace("-", "")

    artists_to_check = song.artists[int(has_main_artist) :]
    for artist in artists_to_check:
        artist = slugify(artist).replace("-", "")
        if artist in match_str:
            score += 5

    if score <= 70:
        artist_match = fuzz.ratio(
            clean_string(song.artists, song_name), clean_string(list(result.artists), result_name)
        )
        if artist_match > score:
            score = artist_match
    return score


def title(song: Spotify, result: YouTube) -> float:
    song_name = slugify(song.name)
    test_song_name = song_name if result.song else f"{', '.join(song.artists)} - {song.name}"
    result_name = slugify(result.name)

    test1 = fill_string(song.artists, result_name, test_song_name)
    test2 = fill_string(song.artists, test_song_name, result_name)

    test_list1, test_list2 = sort_strings(test1.split("-"), test2.split("-"))
    match_str1, match_str2 = "-".join(test_list1), "-".join(test_list2)

    res_list, song_list = sort_strings(result_name.split("-"), song_name.split("-"))
    result_name, song_name = "-".join(res_list), "-".join(song_list)

    name_match = fuzz.ratio(result_name, song_name)

    if name_match <= 75:
        second_name_match = fuzz.ratio(match_str1, match_str2)

        if second_name_match > name_match:
            name_match = second_name_match

    for word in FORBIDDEN_WORDS:
        if word in result_name and word not in song.name:
            name_match -= 15

    return name_match


def fill_string(strings: List[str], main_string: str, string_to_check: str) -> str:
    final_str = main_string
    test_str = final_str.replace("-", "")
    simple_test_str = string_to_check.replace("-", "")
    for string in strings:
        slug_str = slugify(string).replace("-", "")

        if slug_str in simple_test_str and slug_str not in test_str:
            final_str += f"-{slug_str}"
            test_str += slug_str

    return final_str
