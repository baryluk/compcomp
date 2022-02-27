#!/usr/bin/env python3

import argparse
import dataclasses
import collections
import sys
import os
import re
import shutil
import subprocess
import time
import tempfile
from typing import Any, Dict, List, Optional, Tuple

verbose = False
debug = False

comps = [
      ("cp",                  ".copy",   ["cp", "FILE", "FILE.copy"]),  # dry-run
    *[(f"gzip-{level}",       ".gz",     ["gzip", "--keep", f"-{level}", "FILE"]) for level in [1, 3, 6, 9]],
    *[(f"zopfli-i{iters}",    ".gz",     ["zopfli", f"--i{iters}", "FILE"]) for iters in [15, 50]],
    *[(f"bz2-{level}",        ".bz2",    ["bzip2", "--keep", f"-{level}", "FILE"]) for level in [4, 6, 9]],
    *[(f"xz-{level}",         ".xz",     ["xz", "--keep", f"-{level}", "FILE"]) for level in [1, 3, 6, 9]],
    *[(f"lzma-{level}",       ".lzma",   ["lzma", "--keep", f"-{level}", "FILE"]) for level in [6, 9]],
    *[(f"zstd-{level}",       ".zst",    ["zstd", "--quiet", "--keep", f"-{level}", "FILE"]) for level in [1, 3, 14, 16, 19]],
    # See https://bugs.debian.org/998207
    *[(f"lz4-{level}",        ".lz4",    ["lz4", "--quiet", "--keep", f"-{level}", "FILE", "FILE.lz4"]) for level in [1, 4, 9, 12]],
    *[(f"lzop-{level}",       ".lzo",    ["lzop", "--keep", f"-{level}", "FILE"]) for level in [1, 3, 7, 9]],
    *[(f"br-{level}",         ".br",     ["brotli", "--keep", f"-{level}", "FILE"]) for level in [1, 3, 9]],
      ("br-best",             ".br",     ["brotli", "--keep", "--best", "FILE"]),
      ("7z-ultra",            ".7z",     ["7z", "a", "-bd", "-bb0", "-bso0", "-t7z", "-m0=lzma", "-mx=9", "-mfb=64", "-md=32m", "-ms=on", "BASE.7z", "FILE_OR_DIR"]),
      ("zip",                 ".zip",    ["zip", "--quiet", "BASE.zip", "FILE"]),   # To add directory, enable recurse mode (-r).
      ("rar",                 ".rar",    ["rar", "a", "-inul", "BASE.zip", "FILE"]),
      # ("compress",            ".Z",      ["compress", "FILE"]),
      # compress deletes the input file.
      ("arj-m1",              ".arj",    ["arj", "a", "-i", "-m1", "BASE.arj", "FILE"]),
      ("arj-jm",              ".arj",    ["arj", "a", "-i", "-jm", "BASE.arj", "FILE"]),
      # ("arc",                 ".arc",    ["arc", "a" + "n", "BASE.arc", "FILE"]),  # Recommended to put shar or tar inside.
      # arc truncates also the output filename. NOPE.
    *[(f"lrzip-{level}-bz2",  ".lrz",    ["lrzip", "--quiet", "-p", "1", "-L", f"{level}", "-N", "0", "--bzip2", "FILE"]) for level in [1, 9]],
    *[(f"lrzip-{level}-lzo",  ".lrz",    ["lrzip", "--quiet", "-p", "1", "-L", f"{level}", "-N", "0", "--lzo", "FILE"]) for level in [1, 9]],
    *[(f"lrzip-{level}-zpaq", ".lrz",    ["lrzip", "--quiet", "-p", "1", "-L", f"{level}", "-N", "0", "--zpaq", "FILE"]) for level in [1, 9]],
    # https://github.com/kubo/snzip
    *[(f"snappy-{level}",     ".sz",     ["snzip", "-k", "FILE"]) for level in [1, 6, 9]],
    # https://github.com/odeke-em/snappy-cli/tree/master/cmd/snappy-compress
    # *[(f"snappy-{level}-go", ".snappy",  ["snappy-compress", "FILE", "STDOUT"]) for level in [1, 6, 9]],
      ("dact",                ".dct",    ["dact", "FILE"]),

    # zpaq
    # pixz  - paralell xz, but xz has also -T option
    # plzip - parallel lzma
    # pigz - parallel gz
    # rar
    # lha
    # arc
]


def find_exeuctable(x: str) -> Optional[str]:
    if not x:
        return None
    if x[0] == "/" or x.startswith("./"):
        return x if os.path.isfile(x) else None
    for path in os.environ["PATH"].split(":"):
        full_path = os.path.join(path, x)
        if os.path.isfile(full_path):
             if debug:
                 print(f"Found {x} at {full_path}", file=sys.stderr)
             return full_path

    if debug:
        print(f"Did not found {x} in PATH", file=sys.stderr)
    return None


def run_one(filename: str, comp: Tuple[str, str, str]) -> Optional[str]:
    key, suffix, command = comp

    command = [arg.replace("FILE_OR_DIR", filename).replace("FILE", filename) for arg in command]
    assert suffix
    assert suffix.startswith(".")
    output = f"{filename}{suffix}"
    if any("BASE" in arg for arg in command):
        output = f"{filename}_output_{key}{suffix}"
        command = [arg.replace("BASE", f"{filename}_output_{key}") for arg in command]
    try:
        os.unlink(output)
    except FileNotFoundError:
        pass

    try:
        if debug:
            print("Running:", command, file=sys.stderr)
        if debug:
            completed_process = subprocess.run(command)
        else:
            completed_process = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError as e:
        # print("error", e)
        # Program not installed.
        return None

    return output


def test_file(original_filename: str) -> Dict[str, Any]:
    results = {}
    input_size = os.stat(original_filename).st_size
    # Add custom suffix, so we do not accidently use "_z" which gzip does not like.
    with tempfile.NamedTemporaryFile(suffix="compcomp") as tmp:
        filename = tmp.name
        shutil.copyfile(original_filename, filename)
        for key, suffix, command in comps:
            input_size = os.stat(filename).st_size

            if verbose:
                print(f"{key:20s}", original_filename, end=" ")

            t0 = time.monotonic()
            output = run_one(filename, (key, suffix, command))
            t1 = time.monotonic()

            if output is None:
                continue

            try:
                output_size = os.stat(output).st_size
            except FileNotFoundError as e:
                print("error", e)
                continue

            if verbose:
                print(f"{t1 - t0:.3f}s", output_size, f"{input_size / (t1 - t0) / 1e6:.2f}MB/s")

            try:
                os.unlink(output)
            except FileNotFoundError:
                print(f"{key}: Cannot unlink output {output}", file=sys.stderr)
                continue
            results[key] = (t1 - t0, input_size, output_size)
        return results

def process_iterable(filenames):
    for filename in filenames:
        stats_for_file = test_file(filename)
        for key, stat in stats_for_file.items():
            yield key, stat

def roundup(x, b = 4096):
    return (x + b - 1) // b * b

@dataclasses.dataclass
class Stats:
    total_files_count: int = 0
    total_input_size: int = 0
    total_input_size_4k: int = 0
    total_compressed_size: int = 0
    total_compressed_size_4k: int = 0
    total_time: int = 0
    min_ratio: float = float("inf")
    max_ratio: float = float("-inf")
    min_ratio4k: float = float("inf")
    max_ratio4k: float = float("-inf")

def file_scanner(d):
    if os.path.isfile(d):
        yield d
        return
    for root, dirs, files in os.walk(d, followlinks=False):
        yield from (os.path.join(root, name) for name in files)

def main() -> None:
    parser = argparse.ArgumentParser(description="Compression comparator")
    parser.add_argument("--methods", default=".*", help="Regular expression of which methods to use.")
    parser.add_argument("--list", action="store_true", help="List supported compressions methods and exit")
    parser.add_argument("--progress", action="store_true", help="Precompute size of input and then show progress bar during compression")
    parser.add_argument("--verbose", action="store_true", help="Show each file being processed and its statistics")
    parser.add_argument("--debug", action="store_true", help="Show output of executed commands and other details")
    parser.add_argument("paths", metavar="paths", type=str, nargs='*', help="Files or directories to process recursively")
    args = parser.parse_args()

    global comps

    if args.list:
        for comp in comps:
            print(comp[0])
        return

    if not args.paths:
        parser.print_help()
        print()
        print("Need at least one 'paths' positional argument or run with --list", file=sys.stderr)
        sys.exit(1)


    methods_re = re.compile(args.methods)

    comps = [comp for comp in comps if methods_re.match(comp[0])]
    if not comps:
        print("No compression method matched", file=sys.stderr)
        sys.exit(1)

    comps = [comp for comp in comps if find_exeuctable(comp[2][0]) is not None]
    if not comps:
        print("No compression method matched or executables not found", file=sys.stderr)
        sys.exit(1)

    print("Methods:", " ".join(comp[0] for comp in comps))

    global verbose, debug
    verbose = args.verbose
    debug = args.debug

    all_stats = collections.defaultdict(list)

    stats = collections.defaultdict(Stats)

    total_count = 0
    total_bytes = 0
    if args.progress:
        for file_or_dir in args.paths:
            input_list = file_scanner(file_or_dir)
            sub_total_count = 0
            sub_total_bytes = 0
            for filename in input_list:
                sub_total_count += 1
                sub_total_bytes += os.path.getsize(filename)
            print(file_or_dir, sub_total_count, "files", sub_total_bytes, "bytes")
            total_count += sub_total_count
            total_bytes += sub_total_bytes

        import tqdm
        progress_bar = tqdm.tqdm(total=total_bytes, unit='B', unit_scale=True, unit_divisor=1000, miniters=1)
    else:
        progress_bar = None

    next_progress_bytes = 0
    last_reported_progress_value = -1
    previous_progress_bytes = 0

    # input_list = sys.argv[1:]
    for file_or_dir in args.paths:
        input_list = file_scanner(file_or_dir)
        for key, stat in process_iterable(input_list):
            # all_stats[key].append(stat)
            s = stats[key]
            s.total_files_count += 1
            s.total_input_size += stat[1]
            if args.progress:
                if s.total_input_size > previous_progress_bytes:
                     progress_bar.update(s.total_input_size - previous_progress_bytes)
                     previous_progress_bytes = s.total_input_size
                #     x = f"{s.total_input_size / total_bytes * 100.0:.0f}%"
                #     if x != last_reported_progress_value:
                #         print(x, file=sys.stderr)
                #         last_reported_progress_value = x
            s.total_input_size_4k += roundup(stat[1])
            s.total_compressed_size += stat[2]
            s.total_compressed_size_4k += roundup(stat[2])
            s.total_time += stat[0]
            if stat[1]:
                ratio = stat[2] / stat[1]
                s.min_ratio = min(s.min_ratio, ratio)
                s.max_ratio = max(s.max_ratio, ratio)
                ratio4k = roundup(stat[2]) / roundup(stat[1])
                s.min_ratio4k = min(s.min_ratio4k, ratio4k)
                s.max_ratio4k = max(s.max_ratio4k, ratio4k)
    if progress_bar:
        progress_bar.close()


    longest_key = max(len(key) for key in stats.keys())

    tab = []
    for key, s in stats.items():
        tab.append([
            key,
            s.total_files_count,
            s.total_input_size,
            s.total_compressed_size, f"{s.total_compressed_size / s.total_input_size * 100.0:.2f}%",
            f"{s.min_ratio * 100.0:.1f} - {s.max_ratio * 100.0:.1f}%",
            s.total_input_size_4k,
            s.total_compressed_size_4k, f"{s.total_compressed_size_4k / s.total_input_size_4k * 100.0:.2f}%",
            f"{s.min_ratio4k * 100.0:.1f} - {s.max_ratio4k * 100.0:.1f}%",
            f"{s.total_input_size / s.total_time / 1024 / 1024:2f} MiB/s",
        ])

    headers =  ["comp", "count", "in_size", "out_size", "ratio", "min-max", "in_size4k", "out_size4k", "ratio", "min-max", "speed"]
    colalign = ["left", "right", "right",   "right",    "right", "right",   "right",     "right",      "right", "right",   "right"]

    try:
        import tabulate
        print(tabulate.tabulate(tab, headers=headers, colalign=colalign, tablefmt="pipe"))
        print()
    except Exception:
        for key, s in stats.items():
            print(f"{key:{longest_key}s}",
                  f"count: {s.total_files_count}",
                  f"input: {s.total_input_size}",
                  f"input4k: {s.total_input_size_4k}",
                  f"comp: {s.total_compressed_size} ({s.total_compressed_size / s.total_input_size * 100.0:.2f}%)",
                  f"comp4k: {s.total_compressed_size_4k} ({s.total_compressed_size_4k / s.total_input_size_4k * 100.0:.2f}%)")


    #print()
    #print("Stats:")
    #for key, stats in all_stats.items():
    #    print(f"{key:{longest_key}s}", end="")
    #    for stat in stats:
    #        print(f" {stat[2] / max(1, stat[1]):.3f} {stat[0]:8.3f}s {max(1, stat[1]) / max(0.001, stat[0]) / 1e6:.2f}MB/s", end="")
    #    print()


if __name__ == '__main__':
    main()

# To report versions of packages on Debian:
# dpkg -l | awk '{ print $2, $3; }' | egrep 'zip|7z|tar|xz|brotli|zopfli|zstd|lz4|lzop|gzip|rar|bzip|zutils|zpaq|ncompress|dact' | grep -v ^lib
