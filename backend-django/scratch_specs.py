import sys
import os
import django

sys.path.append('/home/radu43/mds/pc-builder/backend-django')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from scrapling.fetchers import DynamicSession
from components.management.commands.populeaza_storage_emag import _extract_specs

URLS = [
    "https://www.emag.ro/procesor-amd-ryzentm-5-7600-3-8ghz-32mb-socket-am5-box-100-100001015box/pd/DPD2G8MBM/",
    "https://www.emag.ro/placa-video-gigabyte-geforce-rtxtm-4060-windforce-oc-8gb-gddr6-128-bit-dlss-3-gv-n4060wf2oc-8gd/pd/DZ2M3MYBM/",
    "https://www.emag.ro/placa-de-baza-gigabyte-b650m-ds3h-socket-am5-b650m-ds3h/pd/DDK728MBM/"
]

with DynamicSession(headless=True) as session:
    for url in URLS:
        print(f"Fetching: {url}")
        try:
            page = session.fetch(url)
            specs = _extract_specs(page)
            print("Specs:")
            for k, v in specs.items():
                print(f"  {k}: {v}")
            print("-" * 50)
        except Exception as e:
            print(f"Error: {e}")
