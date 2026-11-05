"""
`sermon audio <file>`: turn a recording of a service into the finished sermon
audio (trimmed, faded, loudness-matched, with intro and outro).

    sermon audio ~/Downloads/service.m4a                       # auto-finds the cuts
    sermon audio service.m4a --start 43:40 --end 1:17:24       # you pick the cuts

Either way you hear the two cuts and can nudge them before the full render.
"""

import argparse
import json
import os
import subprocess
import sys
import time

from app.data_models.pipeline_data import PipelineData
from app.steps.render_audio_step import probe_audio_duration, render_audio_step
from app.trim_suggester import SuggestionError, suggest_trim
from app.utils.cut_preview import confirm_cuts
from app.utils.dates import last_sunday, validate_date
from app.utils.download import download_file
from app.utils.ffmpeg_path import ensure_ffmpeg
from app.utils.prune import prune_cache
from app.utils.run_record import describe_input, write_run_record
from app.utils.system import notify, open_result
from app.utils.timestamps import format_timestamp, parse_timestamp

# Config, cache and output live in the project folder wherever the command is run.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(ROOT, "config", "pipeline_config.json")
CACHE_DIR = os.path.join(ROOT, "cache")
DEFAULT_OUTPUT_DIR = os.path.join(ROOT, "output")


class CliError(Exception):
    """A problem to report to the user in plain words (no traceback)."""


def build_parser():
    parser = argparse.ArgumentParser(
        prog="sermon", description="Prepare sermon audio from a service recording."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    audio = commands.add_parser(
        "audio", help="Trim, fade, normalize and add intro/outro to a recording"
    )
    audio.add_argument("input", help="Audio file (wav, mp3, m4a, ...) from anywhere")
    audio.add_argument("--start", help="Where the sermon starts, e.g. 43:40 or 1:02:10")
    audio.add_argument("--end", help="Where the sermon ends, e.g. 1:17:24")
    audio.add_argument(
        "--date",
        help="Sermon date as YYYY-MM-DD (default: the most recent Sunday)",
    )
    audio.add_argument("--format", choices=["wav", "mp3"], help="Output format")
    audio.add_argument("--fade", type=float, default=1.0, help="Fade seconds (default 1)")
    audio.add_argument("--stream-id", help="Output subfolder (default: from config)")
    audio.add_argument(
        "--output-dir", default=DEFAULT_OUTPUT_DIR, help="Where results go"
    )
    audio.add_argument("--config", default=DEFAULT_CONFIG, help="Config with intro/outro URLs")
    audio.add_argument("-y", "--yes", action="store_true", help="Skip the listen-and-confirm step")
    audio.add_argument("--no-preview", action="store_true", help="Don't play the cut previews")
    audio.add_argument(
        "--plan-only",
        action="store_true",
        help="Find and show the cuts, then stop without rendering",
    )
    audio.add_argument("--no-open", action="store_true", help="Don't open the result when done")
    audio.add_argument(
        "--keep-days",
        type=int,
        default=28,
        help="Delete cached downloads and transcripts older than this (0 = never)",
    )
    return parser


def load_settings(config_path):
    """
    Reads only what the CLI needs from the config. It is deliberately lenient so
    that an out-of-date layout elsewhere in the file cannot block this command.
    """
    try:
        with open(config_path) as handle:
            config = json.load(handle)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as error:
        raise CliError(f"{config_path} is not valid JSON: {error}")
    audio = config.get("audio", {})
    return {
        "stream_id": config.get("stream_id"),
        "intro_url": audio.get("intro_url"),
        "outro_url": audio.get("outro_url"),
        "output_format": audio.get("output_format"),
    }


def fetch_clip(url, filename):
    """Downloads an intro/outro once and reuses the cached copy afterwards."""
    try:
        return download_file(url, os.path.join(CACHE_DIR, "s3", filename))
    except OSError as error:  # URLError and friends are OSErrors
        raise CliError(f"Could not download {url}: {error}")


def unique_output_path(output_dir, stream_id, date, fmt):
    """Never overwrites an earlier result: a second run on one date becomes -2, -3..."""
    folder = os.path.join(output_dir, stream_id)
    candidate, number = f"{date}.{fmt}", 2
    while os.path.exists(os.path.join(folder, candidate)) or os.path.exists(
        os.path.join(folder, f"{os.path.splitext(candidate)[0]}.json")
    ):
        candidate = f"{date}-{number}.{fmt}"
        number += 1
    return os.path.join(folder, candidate)


def _length(seconds):
    return format_timestamp(seconds).split(".")[0]


def resolve_trim(args, input_path, duration, print_fn):
    """Returns (start, end, suggestion_or_None) from the flags or from auto-trim."""
    if bool(args.start) != bool(args.end):
        raise CliError("Give both --start and --end, or neither to find them automatically.")
    if args.start:
        try:
            return parse_timestamp(args.start), parse_timestamp(args.end), None
        except ValueError as error:
            raise CliError(str(error))
    suggestion = suggest_trim(
        input_path,
        duration,
        cache_dir=os.path.join(CACHE_DIR, "transcripts"),
        progress=print_fn,
    )
    return suggestion.start, suggestion.end, suggestion


def print_plan(print_fn, input_path, duration, start, end, suggestion, intro, outro, output):
    print_fn("")
    print_fn(f"  File:    {input_path} ({_length(duration)} long)")
    source = "you chose" if suggestion is None else f"auto, {suggestion.confidence} confidence"
    print_fn(
        f"  Trim:    {format_timestamp(start)} to {format_timestamp(end)} "
        f"({_length(end - start)})  [{source}]"
    )
    if suggestion:
        print_fn(f'  Starts:  "{suggestion.start_quote}"')
        print_fn(f'  Ends:    "{suggestion.end_quote}"')
        if suggestion.reasoning:
            print_fn(f"  Why:     {suggestion.reasoning}")
        for alternative in suggestion.alternatives:
            print_fn(
                f"  Or:      {alternative['which']} at {format_timestamp(alternative['time'])} "
                f'("{alternative["quote"]}") {alternative["note"]}'.rstrip()
            )
        for warning in suggestion.warnings:
            print_fn(f"  WARNING: {warning}")
    print_fn(f"  Intro:   {'yes' if intro else 'none'}    Outro: {'yes' if outro else 'none'}")
    print_fn(f"  Output:  {output}")
    print_fn("")


def run_audio(args, input_fn=input, print_fn=print):
    started = time.time()
    settings = load_settings(args.config)

    input_path = os.path.expanduser(args.input)
    if not os.path.isfile(input_path):
        raise CliError(f"File not found: {input_path}")

    date = validate_date(args.date) if args.date else last_sunday()
    fmt = args.format or settings.get("output_format") or "wav"
    stream_id = args.stream_id or settings.get("stream_id") or "sermon"

    removed = prune_cache(CACHE_DIR, args.keep_days)
    if removed:
        print_fn(f"Cleaned {len(removed)} cached file(s) older than {args.keep_days} days.")

    duration = probe_audio_duration(input_path)
    start, end, suggestion = resolve_trim(args, input_path, duration, print_fn)
    output_path = unique_output_path(args.output_dir, stream_id, date, fmt)

    intro = fetch_clip(settings["intro_url"], "audio_intro.wav") if settings.get("intro_url") else None
    outro = fetch_clip(settings["outro_url"], "audio_outro.wav") if settings.get("outro_url") else None

    print_plan(print_fn, input_path, duration, start, end, suggestion, intro, outro, output_path)
    if args.plan_only:
        return 0

    if args.yes:
        if suggestion and (suggestion.warnings or suggestion.confidence.lower() == "low"):
            raise CliError(
                "Not running unattended: the automatic cut could not be fully verified. "
                "Run again without --yes to check it, or pass --start and --end."
            )
    elif args.no_preview:
        if input_fn("Render with these cuts? [Y/n] ").strip().lower() in ("n", "no", "q"):
            raise CliError("Cancelled.")
    else:
        accepted = confirm_cuts(
            input_path, start, end, duration,
            workdir=os.path.join(CACHE_DIR, "previews"),
            input_fn=input_fn, print_fn=print_fn,
        )
        if accepted is None:
            raise CliError("Cancelled.")
        start, end = accepted

    data = PipelineData(
        main_file_path=input_path,
        active_file_path=input_path,
        intro_file_path=intro,
        outro_file_path=outro,
    )
    render_audio_step(
        data,
        start_time=format_timestamp(start),
        end_time=format_timestamp(end),
        output_format=fmt,
        fade_duration=args.fade,
        output_path=output_path,
    )

    record = {
        "input": describe_input(input_path),
        "date": date,
        "format": fmt,
        "fade_seconds": args.fade,
        "trim": {
            "start": start,
            "end": end,
            "start_formatted": format_timestamp(start),
            "end_formatted": format_timestamp(end),
            "chosen_by": "you" if suggestion is None else "auto",
        },
        "auto_trim": None
        if suggestion is None
        else {
            "suggested_start": suggestion.start,
            "suggested_end": suggestion.end,
            "start_quote": suggestion.start_quote,
            "end_quote": suggestion.end_quote,
            "confidence": suggestion.confidence,
            "reasoning": suggestion.reasoning,
            "warnings": suggestion.warnings,
            "alternatives": suggestion.alternatives,
            "model": suggestion.model,
            "adjusted_by_you": (abs(start - suggestion.start) > 0.01 or abs(end - suggestion.end) > 0.01),
        },
        "intro_url": settings.get("intro_url"),
        "outro_url": settings.get("outro_url"),
        "output": os.path.abspath(output_path),
        "output_seconds": probe_audio_duration(output_path),
        "render_elapsed_seconds": round(time.time() - started, 1),
    }
    record_path = write_run_record(output_path, record)

    print_fn(f"Done: {output_path}")
    print_fn(f"Record: {record_path}")
    notify("Sermon audio is ready", os.path.basename(output_path))
    if not args.no_open:
        opened = open_result(os.path.abspath(output_path))
        if opened:
            print_fn(opened + ".")
    return 0


def main(argv=None, input_fn=input, print_fn=print):
    args = build_parser().parse_args(argv)
    try:
        ensure_ffmpeg()
        return run_audio(args, input_fn=input_fn, print_fn=print_fn)
    except KeyboardInterrupt:
        print_fn("\nCancelled.")
        return 130
    except (CliError, SuggestionError, ValueError, RuntimeError) as error:
        print_fn(f"\n{error}")
        if str(error) != "Cancelled.":
            notify("Sermon audio failed", str(error).splitlines()[0][:100])
        return 1
    except ImportError as error:
        package = getattr(error, "name", None) or "a required package"
        print_fn(f"\nMissing Python package '{package}'. Install it with: pip install {package}")
        return 1
    except subprocess.CalledProcessError as error:
        detail = (error.output or "").strip() or "no details"
        print_fn(f"\nffmpeg failed:\n{detail}")
        notify("Sermon audio failed", "ffmpeg reported an error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
