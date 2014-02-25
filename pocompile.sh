#!/bin/sh

for po in $(find . -path '*/LC_MESSAGES/*.po'); do
    msgfmt -o ${po/%po/mo} $po;
done
