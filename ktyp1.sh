#!/bin/sh
# KT-TYP1 harness: build, runtime gates, compile-fail gates.
# Transcript lines are deterministic; the harness exits nonzero on any gate failure.
set -u
export PATH="$HOME/.cargo/bin:$PATH"
LLD=$(find "$HOME/.rustup/toolchains" -name rust-lld | head -1)
export RUSTFLAGS="-C linker-flavor=ld.lld -C linker=$LLD -C link-self-contained=yes"
cd /home/user/evilswarm || exit 1
T=x86_64-unknown-linux-musl
cargo build --target $T --bin gates >/dev/null 2>build_err.txt || { echo "BUILD FAILED"; cat build_err.txt; exit 1; }
echo "build: ok (rustc 1.99.1, musl self-contained)"
./target/$T/debug/gates || exit 1
RLIB=$(ls -1 target/$T/debug/deps/libevilswarm-*.rlib 2>/dev/null | head -1)
if [ -z "$RLIB" ]; then echo "no rlib found"; exit 1; fi
fail=0
for f in cf/g*.rs; do
  exp=$(grep -o 'expect: .*' "$f" | sed 's/expect: //')
  if rustc --edition 2021 --target $T --deny unused_must_use --extern evilswarm="$RLIB" "$f" --emit=metadata --out-dir /tmp/cf-out >/dev/null 2>cf_err.txt; then
    echo "CF $f: COMPILED - FAIL (expected compile error)"
    fail=1
  else
    if grep -q "$exp" cf_err.txt; then
      echo "CF $f: refused as expected ($exp)"
    else
      echo "CF $f: failed but wrong error (expected: $exp)"
      fail=1
    fi
  fi
done
if [ $fail -ne 0 ]; then exit 1; fi
echo "KT-TYP1 HARNESS GREEN"
