import csv
from playwright.sync_api import sync_playwright
from config import MAGAZINE
from scraper_universal import extrage_produse_magazin

def ruleaza_scannere():
    print("========================================")
    print("🚀 SCRAPER MULTI-MAGAZIN (eMAG, PC Garage, Altex, Vexio)")
    print("========================================")

    # 1. Citim ce vrem să căutăm
    termen_cautare = input("👉 Ce componentă cauți? (ex: RTX 4090, Ryzen 7): ").strip()
    if not termen_cautare:
        print("❌ Nu ai introdus nimic. Ieșire.")
        return

    toate_produsele_gasite = []

    # 2. Pornim browserul O SINGURĂ DATĂ pentru toate magazinele
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # 3. Trecem prin fiecare magazin definit în config.py
        for nume_magazin, setari in MAGAZINE.items():
            rezultate_magazin = extrage_produse_magazin(page, nume_magazin, setari, termen_cautare)
            toate_produsele_gasite.extend(rezultate_magazin)

        browser.close()

    # 4. Salvăm totul într-un singur CSV
    if toate_produsele_gasite:
        nume_fisier = f"rezultate_{termen_cautare.replace(' ', '_')}.csv"
        
        with open(nume_fisier, mode='w', newline='', encoding='utf-8') as fisier_csv:
            fieldnames = ['Magazin', 'Nume Produs', 'Pret (Lei)', 'Status Stoc', 'Link']
            writer = csv.DictWriter(fisier_csv, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerows(toate_produsele_gasite)
            
        print(f"\n🏁 Gata! Am salvat {len(toate_produsele_gasite)} produse în: {nume_fisier}")
        
        # ==========================================
        # 5. NOU: ANALIZA CELUI MAI IEFTIN PRODUS
        # ==========================================
        print("\n📊 ANALIZĂ REZULTATE:")
        
        # Păstrăm doar produsele care sunt în stoc (sau precomandă) și au un preț mai mare ca 0
        produse_valabile = [p for p in toate_produsele_gasite if p['Status Stoc'] != 'Epuizat' and p['Pret (Lei)'] > 0]
        
        if produse_valabile:
            # Găsim produsul cu prețul cel mai mic
            cel_mai_ieftin = min(produse_valabile, key=lambda x: x['Pret (Lei)'])
            
            print("🏆 CEL MAI IEFTIN PRODUS GĂSIT ESTE:")
            print(f"   💰 Preț:    {cel_mai_ieftin['Pret (Lei)']} Lei")
            print(f"   🛒 Magazin: {cel_mai_ieftin['Magazin']}")
            print(f"   📦 Produs:  {cel_mai_ieftin['Nume Produs']}")
            print(f"   🔗 Link:    {cel_mai_ieftin['Link']}")
            print("========================================\n")
        else:
            print("❌ Nu am găsit niciun produs în stoc pentru a face o comparație de preț.")

    else:
        print("\n🏁 Nu s-a găsit niciun produs pe niciun magazin.")

if __name__ == "__main__":
    ruleaza_scannere()