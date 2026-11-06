#!/bin/sh
set -eu
ziran=$(realpath "$1")
ziran_root=$(CDPATH= cd -- "$(dirname "$ziran")/../.." && pwd)
root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
cd "$root"
unset DISPLAY WAYLAND_DISPLAY XAUTHORITY DBUS_SESSION_BUS_ADDRESS SESSION_MANAGER
mkdir -p build/tests
work=$(mktemp -d "$root/build/tests/portable.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
export TMPDIR="$work" ZIRAN_NATIVE_DIR="$work" ZIRAN_NATIVE_CACHE=0 GOCACHE="$work/go-cache"
run_vm() {
    result=$("$@") || { printf '%s\n' "$result"; return 1; }
    test "$result" = 0 || { printf '%s\n' "$result"; return 1; }
}
"$ziran" check --root tools --module-path src --module-path tests --module-path "std=$ziran_root/std" tools/check.zi
"$ziran" ir --root tools --module-path src --module-path tests --module-path "std=$ziran_root/std" -o "$work/ir" tools/check.zi
for form in source saved; do
    if test "$form" = source; then
        input="$root/tools/check.zi"
        set -- --root tools --module-path src --module-path tests --module-path "std=$ziran_root/std"
    else
        input="$work/ir/check.zir"
        set -- --root "$work/ir" --module-path "$work/ir"
    fi
    "$ziran" bundle "$@" --entry check:main -o "$work/$form.zx" "$input"
    run_vm "$ziran" run "$work/$form.zx"
    run_vm "$(dirname "$ziran")/zi2zx" run --vm "$work/$form.zx"
    for target in c go; do
        output="$work/$form-$target"
        if test "$target" = go; then
            "$ziran" build "$@" --target=go --pkg main --exe --entry check:main -o "$output" "$input"
            GO111MODULE=off go run "$output"/*.go
        else
            "$ziran" build "$@" --target=c --exe --entry check:main -o "$output" "$input"
            "$output/check"
        fi
    done
done
cmp "$work/source.zx" "$work/saved.zx"
"$ziran" build --root tests --module-path src --module-path "std=$ziran_root/std" --target=c \
    -o "$work/lifetime" tests/tokenizer_lifetime.zi
"${CC:-cc}" -std=c99 -g -O1 -I"$work/lifetime" -I"$ziran_root/include" \
    "$work/lifetime"/*.c tests/allocations.c -Wl,--wrap=malloc -Wl,--wrap=calloc \
    -Wl,--wrap=realloc -Wl,--wrap=free -lm -o "$work/lifetime-test"
"$work/lifetime-test"
echo 'CLIP tokenizer: independent HF goldens, malformed inputs/models, reuse and source/saved C/Go/VM passed'
