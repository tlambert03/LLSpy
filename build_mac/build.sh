#!/usr/bin/env bash
export DYLD_LIBRARY_PATH="/Users/talley/DropboxHMS/Python/llspy/lib/:/Users/talley/DropboxHMS/Python/llspylibs/lib/:$DYLD_LIBRARY_PATH"
rm -rf ./_dist
rm -rf ./_build
pyinstaller  --noconfirm --clean \
	--distpath=./_dist \
	--workpath=./_build \
	--upx-dir="/usr/local/bin/" \
	llspygui.spec