#!/bin/bash

set -u

BASE_URL="https://groups.inf.ed.ac.uk/ami/AMICorpusMirror/amicorpus"
DEST="$HOME/AMI/amicorpus"

mkdir -p "$DEST"

echo "=========================================="
echo "        AMI SLIDES DOWNLOADER"
echo "=========================================="
echo ""

# Get AMI meeting directories from the mirror
wget -qO- "$BASE_URL/" > /tmp/ami_index.html

grep -oP 'href="\K[^"]+(?=/")' /tmp/ami_index.html \
    | grep -E '^[A-Z]{2}[0-9]{4}[a-d]?$' \
    | sort -u > /tmp/ami_meetings.txt

echo "Meetings detected:"
wc -l /tmp/ami_meetings.txt

echo ""

while read -r MEETING
do

    echo "------------------------------------------"
    echo "Downloading slides: $MEETING"
    echo "------------------------------------------"

    mkdir -p "$DEST/$MEETING/slides"

    cd "$DEST/$MEETING/slides" || continue

    wget \
        -r \
        -np \
        -nH \
        --cut-dirs=5 \
        -c \
        -nc \
        -A "*.jpg,*.jpeg,*.txt,*.xml,*.html" \
        "$BASE_URL/$MEETING/slides/"

done < /tmp/ami_meetings.txt

echo ""
echo "=========================================="
echo "        SLIDE DOWNLOAD FINISHED"
echo "=========================================="
