import sqlite3
#creaza daca nu exista baze de date de tampon
def asigura_tabel_exista():
    conn = sqlite3.connect('tampon.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produse_brute (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_nume TEXT,
            categorie TEXT,
            nume_produs TEXT,
            pret_numeric REAL,
            status_stoc TEXT,
            link TEXT
        )
    ''')
    conn.commit()
    conn.close()

#salveaza in tampon
def salveaza_in_tampon(date):
    conn = sqlite3.connect('tampon.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO produse_brute (site_nume, categorie, nume_produs, pret_numeric, link)
        VALUES (?, ?, ?, ?, ?)
    ''', date)
    conn.commit()
    conn.close()