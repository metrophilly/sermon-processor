"""
The "listen before you render" step.

It builds one short clip with a beep at exactly each cut, prints what you should
hear before and after each beep (from the transcript, when there is one), shows
a live position while the clip plays, and lets you move either cut.
"""

import os
import subprocess
import sys

from app.utils.system import play_audio
from app.utils.timestamps import format_timestamp, parse_timestamp

# Seconds of audio played on each side of a cut.
START_BEFORE, START_AFTER = 4.0, 7.0
END_BEFORE, END_AFTER = 7.0, 4.0
BEEP_SECONDS = 0.15
GAP_SECONDS = 1.0
_MIN_PIECE = 0.05


def make_cut_preview(main_path, start, end, out_path, duration):
    """
    Writes one short wav: a few seconds before the start cut, a BEEP, the first
    seconds of the sermon, a pause, the sermon's last seconds, a BEEP, then a few
    seconds of what is cut.

    Returns the timeline as a list of (offset_from, offset_to, label) so the
    caller can say what is playing at any moment.
    """
    pieces = []  # (kind, source_start, length, label)
    for cut, before, after, name in (
        (start, START_BEFORE, START_AFTER, "START"),
        (end, END_BEFORE, END_AFTER, "END"),
    ):
        lo = max(0.0, cut - before)
        hi = min(duration, cut + after)
        if name == "END":
            pieces.append(("gap", 0.0, GAP_SECONDS, ""))
        if cut - lo >= _MIN_PIECE:
            pieces.append(("audio", lo, cut - lo, f"before the {name} cut"))
        pieces.append(("beep", 0.0, BEEP_SECONDS, f"BEEP = the {name} cut"))
        if hi - cut >= _MIN_PIECE:
            pieces.append(("audio", cut, hi - cut, f"after the {name} cut"))

    command = ["ffmpeg", "-y", "-v", "error", "-hide_banner"]
    filters, labels, timeline, offset = [], [], [], 0.0
    for index, (kind, source_start, length, label) in enumerate(pieces):
        if kind == "audio":
            command.extend(["-ss", f"{source_start:.3f}", "-t", f"{length:.3f}", "-i", main_path])
            chain = "aresample=44100,aformat=channel_layouts=stereo"
        elif kind == "beep":
            command.extend(
                ["-f", "lavfi", "-i", f"sine=frequency=1000:duration={length}"]
            )
            # ffmpeg's sine source is very quiet (about -18 dB); lift it to ~-9 dB so
            # the beep is clearly audible over speech.
            chain = "volume=3,aresample=44100,aformat=channel_layouts=stereo"
        else:
            command.extend(["-f", "lavfi", "-t", str(length), "-i", "anullsrc=r=44100:cl=stereo"])
            chain = "aresample=44100,aformat=channel_layouts=stereo"
        filters.append(f"[{index}:a]{chain}[p{index}]")
        labels.append(f"[p{index}]")
        if kind != "gap":
            timeline.append((offset, offset + length, label))
        offset += length

    filters.append("".join(labels) + f"concat=n={len(pieces)}:v=0:a=1[out]")
    command.extend(
        ["-filter_complex", ";".join(filters), "-map", "[out]", "-c:a", "pcm_s16le", out_path]
    )
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    subprocess.run(command, check=True)
    return timeline


def _clock(seconds):
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes}:{secs:02d}"


def _make_ticker(timeline):
    """A callback that shows 'where you are' on one line while the clip plays."""
    if not sys.stdout.isatty() or not timeline:
        return None
    total = timeline[-1][1]

    def tick(elapsed):
        label = next((l for a, b, l in timeline if a <= elapsed < b), "")
        sys.stdout.write(f"\r  Playing {_clock(elapsed)} / {_clock(total)}   {label:<28}")
        sys.stdout.flush()

    return tick


def _spoken(text):
    """Quotes spoken words; notes like "(quiet...)" and "(nothing spoken)" stay unquoted."""
    if not text:
        return "(nothing spoken)"
    return text if text.startswith("(") else f'"{text}"'


def describe_preview(print_fn, start, end, timeline, context_fn=None):
    """Says in words what the clip is about to play and what to listen for."""
    total = timeline[-1][1] if timeline else 0
    print_fn("")
    print_fn(
        f"  Listening check: about {int(round(total))} seconds, with a short BEEP "
        f"exactly at each cut."
    )
    for number, (name, cut, before_hint, after_hint, windows) in enumerate(
        (
            ("START", start, "should be before the sermon (announcements, setup)",
             "should be the first words of the scripture reading / sermon",
             (START_BEFORE, START_AFTER)),
            ("END", end, "should be the last words of the sermon's closing prayer",
             "should be cut (singing or silence)",
             (END_BEFORE, END_AFTER)),
        ),
        start=1,
    ):
        print_fn("")
        print_fn(f"  {number}. {name} cut at {format_timestamp(cut)}")
        context = context_fn(cut, *windows) if context_fn else None
        if context:
            before, after = context
            print_fn(f"       before the beep: {_spoken(before)}")
            print_fn(f'                        {before_hint}')
            print_fn(f"       after the beep:  {_spoken(after)}")
            print_fn(f'                        {after_hint}')
        else:
            print_fn(f"       before the beep {before_hint}")
            print_fn(f"       after the beep  {after_hint}")
    print_fn("")


PROMPT = (
    "  Does it sound right?\n"
    "    [Enter]     yes, render it            [r]  hear it again\n"
    "    [s 40:55]   move the START to 40:55   [s +2] later  [s -0.5] earlier (any amount)\n"
    "    [e 1:17:30] move the END to 1:17:30   [e +2] later  [e -0.5] earlier (any amount)\n"
    "    [q]         cancel\n"
    "  > "
)


def _new_time(current, value):
    """Absolute time ("40:55") or a nudge in seconds ("+2", "-1.5")."""
    value = value.strip()
    if value[:1] in "+-" and len(value) > 1:
        try:
            return current + float(value)
        except ValueError:
            pass
    return parse_timestamp(value)


def confirm_cuts(
    main_path,
    start,
    end,
    duration,
    workdir,
    input_fn=input,
    play_fn=play_audio,
    print_fn=print,
    context_fn=None,
):
    """
    Plays the cut previews and lets the user accept or adjust them.

    `context_fn(seconds)` may return (words_before, words_after) from the
    transcript. Returns the accepted (start, end) in seconds, or None if
    cancelled.
    """
    preview_path = os.path.join(workdir, "cut-preview.wav")
    replay = True
    while True:
        if replay:
            timeline = make_cut_preview(main_path, start, end, preview_path, duration)
            describe_preview(print_fn, start, end, timeline, context_fn)
            play_fn(preview_path, on_tick=_make_ticker(timeline))
            if sys.stdout.isatty():
                print_fn("")
        replay = True

        answer = input_fn(PROMPT).strip()
        lowered = answer.lower()
        if lowered in ("", "y", "yes"):
            return start, end
        if lowered in ("q", "quit", "n", "no", "cancel"):
            return None
        if lowered == "r":
            continue

        command, _, value = answer.partition(" ")
        if command.lower() in ("s", "e") and value.strip():
            current = start if command.lower() == "s" else end
            try:
                seconds = _new_time(current, value)
            except ValueError as error:
                print_fn(str(error))
                replay = False
                continue
            new_start = seconds if command.lower() == "s" else start
            new_end = seconds if command.lower() == "e" else end
            if not 0 <= new_start < new_end <= duration:
                print_fn(
                    f"That would put the cuts out of order or past the file "
                    f"({format_timestamp(duration)} long). Try again."
                )
                replay = False
                continue
            start, end = new_start, new_end
            continue

        print_fn("Didn't understand that.")
        replay = False
