from django.core.management.base import BaseCommand
from components.models import (
    CPU, GPU, Motherboard, RAM, PSU, Case, Cooler, 
    Storage, Monitor, Fan, NetworkAdapter, Blacklist
)

class Command(BaseCommand):
    help = "Adaugă toate componentele cu preț NULL în tabela Blacklist."

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Șterge automat componentele din tabelele lor inițiale după ce le trece în Blacklist',
        )

    def handle(self, *args, **options):
        # Lista tuturor componentelor noastre din baza de date
        models_list = [
            CPU, GPU, Motherboard, RAM, PSU, Case, Cooler, 
            Storage, Monitor, Fan, NetworkAdapter
        ]
        
        delete_after = True # setat mereu pe True
        total_added = 0
        total_deleted = 0

        self.stdout.write("Începe scanarea componentelor fără preț (NULL)...\n")

        for ModelClass in models_list:
            items_no_price = ModelClass.objects.filter(pret__isnull=True)
            
            for item in items_no_price:
                # Încercăm să o adăugăm în Blacklist folosind part_number (dacă există) sau numele
                if hasattr(item, 'part_number') and item.part_number:
                    bl_item, created = Blacklist.objects.get_or_create(
                        part_number=item.part_number,
                        defaults={"nume": item.nume}
                    )
                else:
                    bl_item, created = Blacklist.objects.get_or_create(
                        nume=item.nume
                    )
                
                if created:
                    total_added += 1
                    self.stdout.write(f"  [+] Adăugat în Blacklist: {item.nume} [{ModelClass.__name__}]")
                else:
                    self.stdout.write(f"  [~] Deja în Blacklist: {item.nume}")
                    
                if delete_after:
                    item.delete()
                    total_deleted += 1

        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS(f"Finalizat! Au fost adăugate {total_added} componente noi în Blacklist."))
        self.stdout.write(self.style.WARNING(f"Au fost șterse {total_deleted} componente (fără preț) din tabelele principale."))
        self.stdout.write("="*50 + "\n")
