compcomp - compression comparator


`./compcomp.py` takes as input list of files, and test various
compression algorithms on them. For each file it will compute the time,
compression speed and compression ratio.

Can test individual files or directories recursively:

```
$ ./compcomp.py --methods="gzip-6|lz4-9|zstd.*|xz.*" --progress .
Methods: gzip-6 xz-1 xz-3 xz-6 xz-9 zstd-1 zstd-3 zstd-14 zstd-16 zstd-19 lz4-9
. 53 files 66506 bytes
100%|████████████████████████████████████████████████| 66.5k/66.5k [00:01<00:00, 34.2kB/s]
| comp    |   count |   in_size |   out_size |   ratio |       min-max |   in_size4k |   out_size4k |   ratio |       min-max |          speed |
|:--------|--------:|----------:|-----------:|--------:|--------------:|------------:|-------------:|--------:|--------------:|---------------:|
| gzip-6  |      53 |     66506 |      38634 |  58.09% | 18.8 - 273.9% |      241664 |       221184 |  91.53% | 25.0 - 100.0% | 0.671033 MiB/s |
| xz-1    |      53 |     66506 |      40984 |  61.62% | 21.3 - 347.8% |      241664 |       221184 |  91.53% | 25.0 - 100.0% | 0.302411 MiB/s |
| xz-3    |      53 |     66506 |      40912 |  61.52% | 21.3 - 347.8% |      241664 |       221184 |  91.53% | 25.0 - 100.0% | 0.245949 MiB/s |
| xz-6    |      53 |     66506 |      40360 |  60.69% | 21.3 - 347.8% |      241664 |       221184 |  91.53% | 25.0 - 100.0% | 0.219425 MiB/s |
| xz-9    |      53 |     66506 |      40360 |  60.69% | 21.3 - 347.8% |      241664 |       221184 |  91.53% | 25.0 - 100.0% | 0.198036 MiB/s |
| zstd-1  |      53 |     66506 |      38475 |  57.85% | 16.6 - 156.5% |      241664 |       225280 |  93.22% | 50.0 - 100.0% | 0.532512 MiB/s |
| zstd-3  |      53 |     66506 |      38123 |  57.32% | 16.6 - 156.5% |      241664 |       225280 |  93.22% | 50.0 - 100.0% | 0.579296 MiB/s |
| zstd-14 |      53 |     66506 |      37276 |  56.05% | 16.6 - 156.5% |      241664 |       221184 |  91.53% | 25.0 - 100.0% | 0.548926 MiB/s |
| zstd-16 |      53 |     66506 |      37233 |  55.98% | 16.6 - 156.5% |      241664 |       221184 |  91.53% | 25.0 - 100.0% | 0.514238 MiB/s |
| zstd-19 |      53 |     66506 |      37219 |  55.96% | 16.6 - 156.5% |      241664 |       221184 |  91.53% | 25.0 - 100.0% | 0.500920 MiB/s |
| lz4-9   |      53 |     66506 |      44921 |  67.54% | 17.6 - 182.6% |      241664 |       225280 |  93.22% | 50.0 - 100.0% | 0.641763 MiB/s |
```

Columns with "4k" suffix, do have all input and output byte sizes of each
file rounded up to 4KiB first, this is useful, for example for estimating
compression ration of small files on file systems with built-in
compression, like zfs, btrfs, or squashfs.

```
$ ./compcomp.py --list
cp
gzip-6
gzip-9
zopfli-i15
zopfli-i50
bz2-4
bz2-9
xz-6
xz-9
lzma-6
lzma-9
zstd-3
zstd-14
zstd-16
zstd-19
lz4-1
lz4-4
lz4-9
lz4-12
lzop-1
lzop-3
lzop-7
lzop-9
br-3
br-9
br-best
7z-ultra
zip
rar
arj-m1
arj-jm
lrzip-1-bz2
lrzip-9-bz2
lrzip-1-lzo
lrzip-9-lzo
lrzip-1-zpaq
lrzip-9-zpaq
snappy-1
snappy-6
snappy-9
dact
```



Pass `--progress` to show progress bar, useful when processing big directories.

Pass `--verbose` to show compression stats for every file being processed
in real time. Should not be combined with `--progress`.

Pass `--debug` to show even more details.

Files before being passed to compressed are copied to `/tmp` (or `TEMP`
if configured), so the file is in cache, and prevent any risk of
potentially corrupting data in passed original files or directories.

Installation: Just run `compcomp.py` directly. `tabulate` and `tqdm`
packages are recommended to enable nicer output and progress bar, but not
required.
