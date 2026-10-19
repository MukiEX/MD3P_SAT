set -e
cd "$(dirname "$0")"
SH=${SH_PREFIX:-sh-elf-}
python3 gen.py
${SH}as --isa=sh2 -big -o build/tester.o tester.s
${SH}objcopy -O binary -j .text build/tester.o build/0.BIN
python3 mkdisc.py
