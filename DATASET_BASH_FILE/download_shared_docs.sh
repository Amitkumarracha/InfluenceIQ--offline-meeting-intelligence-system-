#!/bin/bash

set -u

BASE_URL="https://groups.inf.ed.ac.uk/ami/AMICorpusMirror/amicorpus"
DEST="$HOME/AMI/amicorpus"

mkdir -p "$DEST"

echo "=========================================="
echo "       AMI SHARED DOCS DOWNLOADER"
echo "=========================================="
echo ""

if [ ! -f /tmp/ami_meetings.txt ]; then

    echo "Meeting list not found."
    echo "Creating it..."

    wget -qO- "$BASE_URL/" > /tmp/ami_index.html

    grep -oP 'href="\K[^"]+(?=/")' /tmp/ami_index.html \
        | grep -E '^[A-Z]{2}[0-9]{4}[a-d]?$' \
        | sort -u > /tmp/ami_meetings.txt
fi

while read -r MEETING
do

    echo ""
    echo "------------------------------------------"
    echo "Downloading shared documents: $MEETING"
    echo "------------------------------------------"

    mkdir -p "$DEST/$MEETING/shared-doc"

    cd "$DEST/$MEETING/shared-doc" || continue

    wget \
        -r \
        -np \
        -nH \
        --cut-dirs=5 \
        -c \
        -nc \
        "$BASE_URL/$MEETING/shared-doc/"

done < /tmp/ami_meetings.txt

echo ""
echo "=========================================="
echo "      SHARED DOCUMENTS FINISHED"
echo "=========================================="
