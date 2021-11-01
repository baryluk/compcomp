#!/usr/bin/env python3

import collections
import sys
import os
import subprocess
import time
from typing import Any, Dict, List

comps = [
    # ("cat",                   ".cat",    ["cat", "FILE"]),  # dry-run
    ("wc",                    ".wc",     ["wc", "FILE"]),  # dry-run
    *[(f"gzip-{level}",       ".gz",     ["gzip", "--keep", f"-{level}", "FILE"]) for level in [6, 9]],
    *[(f"zopfli-i{iters}",    ".gz",     ["zopfli", f"--i{iters}", "FILE"]) for iters in [15, 50]],
    *[(f"bz2-{level}",        ".bz2",    ["bzip2", "--keep", f"-{level}", "FILE"]) for level in [4, 9]],
    *[(f"xz-{level}",         ".xz",     ["xz", "--keep", f"-{level}", "FILE"]) for level in [6, 9]],
    *[(f"lzma-{level}",       ".lzma",   ["lzma", "--keep", f"-{level}", "FILE"]) for level in [6, 9]],
    *[(f"zstd-{level}",       ".zst",    ["zstd", "--quiet", "--keep", f"-{level}", "FILE"]) for level in [3, 14, 16]],
    *[(f"lz4-{level}",        ".lz4",    ["lz4", "--quiet", "--keep", f"-{level}", "FILE"]) for level in [1, 4, 9, 12]],
    *[(f"lzop-{level}",       ".lzo",    ["lzop", "--keep", f"-{level}", "FILE"]) for level in [1, 3, 7, 9]],
    *[(f"br-{level}",         ".br",     ["brotli", "--keep", f"-{level}", "FILE"]) for level in [3, 9]],
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
    *[(f"snappy-{level}",     ".sz", ["snzip", "-k", "FILE"]) for level in [1, 6, 9]],
    # https://github.com/odeke-em/snappy-cli/tree/master/cmd/snappy-compress
    # *[(f"snappy-{level}-go", ".snappy", ["snappy-compress", "FILE", "STDOUT"]) for level in [1, 6, 9]],
      ("dact",                ".dct",    ["dact", "FILE"]),

    # zpaq
    # pixz  - paralell xz, but xz has also -T option
    # plzip - parallel lzma
    # pigz - parallel gz
    # rar
    # lha
    # arc
]

def test_file(filename: str) -> Dict[str, Any]:
    results = {}
    input_size = os.stat(filename).st_size
    for key, suffix, command in comps:

        input_size = os.stat(filename).st_size

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
        t0 = time.time()
        print(f"{key:20s}", filename, end=" ")
        try:
            completed_process = subprocess.run(command) #, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError as e:
            print("error", e)
            # Program not installed.
            continue
        t1 = time.time()
        output_size = None
        try:
            output_size = os.stat(output).st_size
        except FileNotFoundError as e:
            print("error", e)
            continue
        print(f"{t1 - t0:.3f}s", output_size, f"{input_size / (t1 - t0) / 1e6:.2f}MB/s")

        try:
            os.unlink(output)
        except FileNotFoundError:
            print(f"{key}: Cannot unlink output {output}", file=sys.stderr)
            continue
        results[key] = (t1 - t0, input_size, output_size)
    return results

def main() -> None:
    all_stats = collections.defaultdict(list)

    for filename in sys.argv[1:]:
        stats_for_file = test_file(filename)
        for key, stat in stats_for_file.items():
            all_stats[key].append(stat)

    print()
    print("Stats:")
    longest_key = max(len(key) for key in all_stats.keys())
    for key, stats in all_stats.items():
        print(f"{key:{longest_key}s}", end="")
        for stat in stats:
            print(f" {stat[2] / max(1, stat[1]):.3f} {stat[0]:8.3f}s {max(1, stat[1]) / max(0.001, stat[0]) / 1e6:.2f}MB/s", end="")
        print()


if __name__ == '__main__':
    main()

# To report versions of packages on Debian:
# dpkg -l | awk '{ print $2, $3; }' | egrep 'zip|7z|tar|xz|brotli|zopfli|zstd|lz4|lzop|gzip|rar|bzip|zutils|zpaq|ncompress|dact' | grep -v ^lib
