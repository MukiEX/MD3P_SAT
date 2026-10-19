# Magical Drop III Paddle Edition: Sega Saturn

Patch for **Magical Drop III Toretate Zoukangou! (Japan, T-1313G)** that lets the clown be
driven by a virtual paddle:

- Shuttle Mouse
- Arcade Racer wheel
- 3D Control Pad or Mission Stick in analog mode
- JP3-style spinner (quadrature) on the d-pad or on Y/Z

It is the Saturn counterpart of the PS1 Paddle Edition: same paddle model, glide, pulsing
target column and optional magnet, adapted to SGL and the SH-2. Only `0.BIN` changes; the
CD audio tracks are untouched.

The full technical write-up is [docs/TECHNICAL.md](docs/TECHNICAL.md). It is also
the second tab of the browser patcher.

## Using it

- **Browser patcher:** download [`releases/MD3_SAT_PADDLE.html`](releases/MD3_SAT_PADDLE.html)
  and open it locally (one self-contained page, no server needed), drop in your Track 01
  `.bin`, the whole `.cue` set or a `.chd`, pick options (speed, glide, pulse, magnet,
  X pulls down) and download the patched image.
- **Patch files:** `releases/patches/... [Paddle].xdelta` or `.ppf`, applied to Track 01
  (Redump, CRC32 `97D3B2B2`). Patched Track 01 CRC32 is `1E76E4EC` with default options.

### Controls

| Device | Paddle input | Notes |
|---|---|---|
| Shuttle Mouse | X movement (relative) | left = catch, right = throw, middle = pull-down |
| Arcade Racer | wheel angle (absolute) | the wheel's own buttons |
| 3D pad / Mission Stick (analog) | stick X (absolute) | Y/Z JP3 check also active |
| Digital pad + JP3 on d-pad | LEFT = phase A, RIGHT = phase B | latches on the first LEFT+RIGHT read |
| Digital pad + JP3 on Y/Z | Y = phase A, Z = phase B | latches on the first Y+Z read; d-pad stays live |

The console reads the pad once per frame, so a JP3 spinner can deliver at most about two
edges per frame (two-edge jumps are taken in the last direction). Adapters that re-sample the
signal (USB to Saturn converters) lower that further; see the write-up.

## Input tester disc

`tester/` builds a small standalone Saturn disc that shows both controllers, lights pressed
buttons, and draws a per-frame bit stream of LEFT, RIGHT, Y and Z with simultaneous presses in
red. It is handy for checking what an adapter really sends. It boots with the game's
`IP.BIN`, so you need to run `tools/setup.py` first; the resulting disc is Japan region.

```sh
tester/build.sh            # -> tester/build/Saturn Input Tester.bin/.cue
```

A+B+C+START clears that port's both-held counters.

## Building

Requirements: Python 3 with Pillow and NumPy, SH binutils (`sh-elf-as`, `sh-elf-objcopy`,
`sh-elf-objdump`; no compiler or linker needed), and `xdelta3`.

```sh
python3 tools/setup.py "/path/to/Magical Drop III - Toretate Zoukangou (Japan) (2M) (Track 01).bin"
SH_PREFIX=sh-elf- tools/release.sh
```

`tools/setup.py` copies your dump into `work/` and extracts `0.BIN` and `IP.BIN`. Nothing from
the game is in this repository; `work/` and `build/` are git-ignored.

`release.sh` assembles `src/md3sat_paddle.s` into free space in `0.BIN` (`tools/build.py`),
checks delay slots (`tools/hazards.py`), rebuilds Track 01 with fresh EDC/ECC, and regenerates
the browser patcher in `releases/` and the PPF and xdelta in `releases/patches/`.

Environment overrides: `SH_PREFIX` (binutils prefix, default `sh-elf-`), `XDELTA`,
`YAB_CORE` (test emulator core), `LIBFLAC` (CHD fixture writer only).

The free-space map the packer uses is committed in `data/` (`free_valid.json`, produced by
`tools/freespace.py` from static reachability, code validation and emulator coverage in
`data/coverage.bin`).

### Toolchain notes

Only gas, objcopy and objdump are needed. Building binutils for `sh-elf` without docs:

```sh
../binutils/configure --target=sh-elf --prefix=$HOME/shtools --disable-nls --disable-werror
make MAKEINFO=true all-gas all-binutils && make MAKEINFO=true install-gas install-binutils
```

## Tests

The emulator tests use the libretro Yabause core with a small debug hook (breakpoints,
memory access, coverage). Build it from `libretro/yabause` at commit `8926b0c` with
`third_party/yabause-dbg.patch` applied and `third_party/yabause-dbg.c` copied to
`yabause/src/libretro/dbg.c`, then put `yabause_libretro.so` in `third_party/` (or set
`YAB_CORE`).

```sh
python3 test/mkorigstates.py      # savestates of the original disc
python3 test/devtest.py           # 33 checks: devices, glide, magnet, pulse, menus
node test/webtest.js              # browser patcher core (CRC, CHD, LZMA, FLAC, EDC/ECC)
python3 test/tester_check.py      # input tester disc
```

## Layout

| Path | What |
|---|---|
| `src/md3sat_paddle.s` | all patch code, split into placeable chunks |
| `tools/` | build, packer, disc/ISO/CHD/PPF tools, release script |
| `web/` | browser patcher sources (`patchcore.js`, generated `patchdata.js`, page template) |
| `releases/` | `MD3_SAT_PADDLE.html`; xdelta and PPF in `releases/patches/` |
| `docs/` | technical write-up (`TECHNICAL.md`) |
| `tester/` | input tester disc (SH-2 assembly + data generator + disc builder) |
| `test/` | ctypes libretro harness and test scripts |
| `data/` | free-space map and coverage used by the packer |
| `third_party/` | Yabause debug-hook patch for the test harness |
