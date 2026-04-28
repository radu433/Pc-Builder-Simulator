#!/bin/bash
cd /home/radu43/mds/pc-builder/backend-django
source backend/bin/activate

echo "=============================================" >> price_log.txt
echo "UPDATE PRETURI inceput la: $(date)" >> price_log.txt
python manage.py update_pret >> price_log.txt 2>&1
echo "UPDATE PRETURI terminat la: $(date)" >> price_log.txt
echo "=============================================" >> price_log.txt

deactivate