from typing import Optional, TypedDict


class VideoPaths(TypedDict):
    raw: str
    compressed: str
    crossfaded: Optional[str]


class PathsDict(TypedDict, total=False):
    intro: VideoPaths
    base: VideoPaths
    outro: VideoPaths
