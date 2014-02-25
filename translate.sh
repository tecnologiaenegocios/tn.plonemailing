#!/bin/sh

DOMAIN=tn.plonemailing
BASEDIR=src/tn/plonemailing

# Synchronise the templates and scripts with the .pot.
# All on one line normally:
bin/i18ndude rebuild-pot --pot ${BASEDIR}/locales/${DOMAIN}.pot \
    --merge ${BASEDIR}/locales/manual.pot \
    --create ${DOMAIN} \
    ${BASEDIR}

# Synchronise the resulting .pot with all .po files
for po in ${BASEDIR}/locales/*/LC_MESSAGES/${DOMAIN}.po; do
    bin/i18ndude sync --pot ${BASEDIR}/locales/${DOMAIN}.pot $po
done
