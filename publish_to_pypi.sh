#!/bin/bash

# cleanup
rm -fr ./dist
rm -fr ./mqtasks.egg-info

# exit on error
set -e

# install requirements
pip install --upgrade pip build twine

# make packet by build
python3 -m build

# upload to PyPI
twine upload dist/*

echo "PyPI done!"
