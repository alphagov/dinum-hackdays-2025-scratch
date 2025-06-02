#!/usr/bin/env bash
set -euo pipefail

cd flask-app/

rm ./*.zip || echo "No ZIPs to delete"
rm -rf .target || echo "No .target/ to delete"
mkdir .target

PYTHON="python3.12"
if [ -z "$(command -v $PYTHON)" ]; then
  PYTHON="python"
fi

PYTHON_VERSION=$($PYTHON -V 2>&1 | sed 's/.* \([0-9].[0-9]*\).*/\1/' | tr -d '\n')
if [ "$PYTHON_VERSION" != "3.12" ]; then
    echo "This script requires python 3.12, found $PYTHON_VERSION"
    exit 1
fi

$PYTHON -m venv .venv
ls -a
source .venv/bin/activate

$PYTHON -m pip install --upgrade pip
$PYTHON -m pip install \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --only-binary=:all: \
  --upgrade \
  --python-version "3.12" \
  --target .target/ \
  --no-user \
  -r requirements.txt

cp ./*.py .target/
cp -r templates/ .target/
cp -r assets/ .target/

cd .target/ || exit 1

find . -type f -exec chmod 0644 {} \;
find . -type d -exec chmod 0755 {} \;

zip -r ../GovGroupsLambda.zip .

cd ../
