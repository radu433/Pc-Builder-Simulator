#!/bin/bash
cd /home/radu43/mds/pc-builder/backend-django
source backend/bin/activate

echo "=============================================" >> import_log.txt
echo "POPULARE BAZA DE DATE inceputa la: $(date)" >> import_log.txt
python manage.py import_all >> import_log.txt 2>&1
echo "POPULARE TERMINATA la: $(date)" >> import_log.txt
echo "=============================================" >> import_log.txt

deactivate