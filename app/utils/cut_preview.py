import os
import subprocess

from app.utils.system import play_audio
from app.utils.timestamps import format_timestamp, parse_timestamp

# Seconds of audio played on each side of a cut.
START_BEFORE, START_AFTER = 4.0, 6.0  # hear the excluded lead-in, then the sermon
END_BEFORE, END_AFTER = 6.0, 4.0  # hear the sermon's last words, then what is cut


def make_cut_preview(main_path, start, end, out_path, duration):
    """
    Writes one short wav that plays around the start cut, a one-second gap, then
    around the end cut. It is a few seconds of work instead of a full render, so
    a wrong cut is caught before the slow step.
    """
    windows = [
        (max(0.0, start - START_BEFORE), start + START_AFTER),
        (max(0.0, end - END_BEFORE), min(duration, end + END_AFTER)),
    ]
    command = ["ffmpeg", "-y", "-v", "error", "-hide_banner"]
    filters = []
    for index, (lo, hi) in enumerate(windows):
        command.extend(["-ss", f"{lo:.3f}", "-t", f"{hi - lo:.3f}", "-i", main_path])
        filters.append(
            f"[{index}:a]aresample=44100,aformat=channel_layouts=stereo[p{index}]"
        )
    filters.append("anullsrc=r=44100:cl=stereo,atrim=duration=1[gap]")
    filters.append("[p0][gap][p1]concat=n=3:v=0:a=1[out]")
    command.extend(
        ["-filter_complex", ";".join(filters), "-map", "[out]", "-c:a", "pcm_s16le", out_path]
    )
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    subprocess.run(command, check=True)
    return out_path


HELP = (
    "[Enter] looks right   [r] replay   [s TIME] new start   [e TIME] new end   "
    "[q] cancel"
)


def confirm_cuts(
    main_path,
    start,
    end,
    duration,
    workdir,
    input_fn=input,
    play_fn=play_audio,
    print_fn=print,
):
    """
    Plays the cut previews and lets the user accept or adjust them.

    Returns the accepted (start, end) in seconds, or None if cancelled. Typing
    "s 43:50" or "e 1:17:30" moves a cut and replays the preview.
    """
    preview_path = os.path.join(workdir, "cut-preview.wav")
    replay = True
    while True:
        if replay:
            print_fn(
                f"Preview: start cut {format_timestamp(start)}, "
                f"end cut {format_timestamp(end)}. Listen for: the first words of the "
                f"sermon right after the first cut, and its last words right before "
                f"the second."
            )
            make_cut_preview(main_path, start, end, preview_path, duration)
            play_fn(preview_path)
        replay = True

        answer = input_fn(f"{HELP}\n> ").strip()
        lowered = answer.lower()
        if lowered in ("", "y", "yes"):
            return start, end
        if lowered in ("q", "quit", "n", "no", "cancel"):
            return None
        if lowered == "r":
            continue

        command, _, value = answer.partition(" ")
        if command.lower() in ("s", "e") and value.strip():
            try:
                seconds = parse_timestamp(value)
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
