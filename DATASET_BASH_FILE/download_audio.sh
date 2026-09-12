#!/bin/bash

set -u

ROOT="$HOME/AMI/audio"
URL="https://openslr.trmal.net/resources/16"

mkdir -p "$ROOT"
cd "$ROOT" || exit 1

echo "=========================================="
echo "       AMI AUDIO DOWNLOADER"
echo "=========================================="
echo ""
echo "Download directory:"
echo "$ROOT"
echo ""

# --------------------------------------------------
# HEADSET AUDIO
# --------------------------------------------------

echo "=========================================="
echo "Downloading AMI headset audio"
echo "Approximately 24 GB"
echo "=========================================="

wget \
    -c \
    --show-progress \
    "$URL/headset.tar.gz"

if [ $? -eq 0 ]; then
    echo "Headset download completed."
else
    echo "Headset download interrupted/failed."
fi


# --------------------------------------------------
# MICROPHONE ARRAY AUDIO
# --------------------------------------------------

echo ""
echo "=========================================="
echo "Downloading microphone-array audio"
echo "Approximately 60 GB total"
echo "=========================================="

ARRAYS=(
    "Array1-01.tar.gz"
    "Array1-02.tar.gz"
    "Array1-03.tar.gz"
    "Array1-04.tar.gz"
    "Array1-05.tar.gz"
    "Array1-06.tar.gz"
    "Array1-07.tar.gz"
    "Array1-08.tar.gz"
)

for FILE in "${ARRAYS[@]}"
do
    echo ""
    echo "------------------------------------------"
    echo "Downloading: $FILE"
    echo "------------------------------------------"

    wget \
        -c \
        --show-progress \
        "$URL/$FILE"

    if [ $? -eq 0 ]; then
        echo "$FILE completed."
    else
        echo "$FILE interrupted/failed."
    fi
done


echo ""
echo "=========================================="
echo "       AUDIO DOWNLOAD FINISHED"
echo "=========================================="
echo ""
echo "Files are located in:"
echo "$ROOT"
echo ""
