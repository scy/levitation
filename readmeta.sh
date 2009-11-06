#!/bin/sh

hexdump -e '"%08_ax " 4/4 "%08x " 1/1 " %02x" "\n"' "$@" | less
