import pandas as pd
import sqlite3
import os

def populeaza_tampon():
    print("========================================")
    print("🛠️ FAZA 1: CREARE BAZĂ DE DATE TAMPON")
    print("========================================")

    # Ne conectăm la SQLite (dacă nu există, fișierul se creează automat)
    conn = sqlite3.connect('tampon.db')
    
    # Găsim folderul unde este scriptul
    cale_folder = os.path.dirname(os.path.abspath(__file__))
    
    # Dicționar cu numele CSV-ului și numele tabelului pe care îl vrem în baza de date
    fisiere_de_import = {
        'cpu.csv': 'CPU',
        'video-card.csv': 'GPU',
        'motherboard.csv': 'Motherboard',
        'memory.csv': 'RAM',
        'power-supply.csv': 'PSU',
        'case.csv': 'Carcase',
        'internal-hard-drive.csv': 'Stocare',
        'cpu-cooler.csv': 'Coolere'
    }

    for fisier, nume_tabel in fisiere_de_import.items():
        # AICI schimbi 'pc-part-dataset/data' cu calea exactă dacă ai pus fișierele într-un sub-folder
        # Dacă le-ai pus direct lângă script, lasă doar: cale_completa = os.path.join(cale_folder, fisier)
        cale_completa = os.path.join(cale_folder, 'pc-part-dataset', 'data','csv', fisier)
        
        if os.path.exists(cale_completa):
            print(f"📥 Importăm {fisier} în tabelul '{nume_tabel}'...")
            try:
                df = pd.read_csv(cale_completa)
                
                # O mică curățenie de bază (scăpăm de piesele care nu au nume deloc)
                if 'name' in df.columns:
                    df = df.dropna(subset=['name'])
                
                # Adăugăm noi 2 coloane speciale pentru Faza 2 (Scraperul)
                df['pret_ro'] = 0.0
                df['link_ro'] = ""
                df['verificat'] = 0 # 0 = nu a trecut scraperul pe aici, 1 = a trecut
                
                # Exportăm în SQLite
                df.to_sql(nume_tabel, conn, if_exists='replace', index=False)
                print(f"   ✅ Succes: {len(df)} piese băgate în carantină.\n")
            except Exception as e:
                print(f"   ❌ Eroare la citirea {fisier}: {e}\n")
        else:
            print(f"⚠️ Nu am găsit {fisier} la calea: {cale_completa}\n")

    conn.close()
    print("🏁 FAZA 1 FINALIZATĂ! Fişierul 'tampon.db' este gata de procesare.")

if __name__ == "__main__":
    populeaza_tampon()