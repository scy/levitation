#!/bin/bash

# Author: BenBE <BenBE@geshi.org>
# Description: Reads maximum ID values from MediaWiki history dumps

#Check if one argument AND that file given there exists; usage otherwise ...
if ! [ 1 -eq $# -a -f $1 ]; then
        echo Usage: $0 dump.xml.bz2
        echo
        echo This will read dump.xml.bz2 and output the necessary meta data for MAXPAGE, MAXREV and MAXUSER.
        exit;
fi

echo Cleaning up from previous runs ...
# Remove a tempfile of previous runs if it exists ...
[ -f $1.tmp ] && rm -f $1.tmp

echo Doing pre-filtering on the bz-compressed dumpfile ...
# Prefilter the dump file for lines containing any IDs ... and remove their surrounding tags
# The six blanks in the search pattern of grep are for broad pre-filtering
# To ease the post-processing for the second pass an unique pattern which can be ignored when numerically sorting is prepended
bzgrep "      <id>" $1 | sed "s/<id>/0/" | sed "s/<\/id>//" > $1.tmp

echo "Looking up the maximum page id ..."
# Query the value for MAXPAGE (six spaces before <id> node) ...
MAXPAGE=`grep "^      0" $1.tmp | sort -nr | head -n 1`

echo "Looking up the maximum revision id ..."
# Query the value for MAXREV (eight spaces before <id> node) ...
MAXREV=`grep "^        0" $1.tmp | sort -nr | head -n 1`

echo "Looking up number of users (not implemented yet) ..."
MAXUSER="(not implemented)"

echo Cleaning up ...
rm $1.tmp

echo
echo Processing done.
echo
echo "Found:"
echo "  - MAXPAGE:    ${MAXPAGE}"
echo "  - MAXREV:     ${MAXREV}"
echo "  - MAXUSER:    ${MAXUSER}"

echo
echo "Have a nice day!"
