#!/usr/bin/env bash
rm -rf ./_dist
rm -rf ./_build
pyinstaller  --noconfirm --clean \
	--distpath=./_dist \
	--workpath=./_build \
	--upx-dir="/usr/bin/" \
	llspygui.spec