#!/bin/bash
set -e
cd "$(dirname "$0")"
tectonic thesis.tex
echo "Successfully compiled thesis.pdf ($(date))"
