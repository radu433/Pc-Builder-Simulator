# PC Builder Simulator

Acesta este proiectul principal pentru o aplicație full-stack de configurare PC.
Repo-ul conține backend Django, frontend Vue și un serviciu de scraping Python.

---

## Ce conține proiectul

- `backend-django/` - API Django + Django REST Framework pentru autentificare, componente, build-uri și gestiunea datelor.
- `frontend-vue/` - Aplicație Vue 3 + Vite pentru interfața utilizatorului.
- `scraper-service/` - Serviciu Python care colectează informații despre componente.
- `docker-compose.yml` - Definirea serviciului MySQL necesar backend-ului.

---

## Descriere

Proiectul permite crearea, optimizarea și vizualizarea configurațiilor PC.
Backend-ul gestionează datele și logica, frontend-ul oferă un dashboard interactiv, iar serviciul de scraping populă baza de date cu componente.

---

## Structura proiect

- `backend-django/`
  - `manage.py`
  - `requirements.txt`
  - aplicații Django pentru `accounts`, `builder`, `components`, etc.
- `frontend-vue/`
  - aplicație Vue 3 cu `package.json`, `vite.config.js`, și fișierele sursă.
- `scraper-service/`
  - cod Python pentru colectarea datelor despre componente.
- `docker-compose.yml`
  - configurare MySQL 8.0.

---

## Tehnologii principale

- Django 6 + Django REST Framework
- Vue 3 + Vite
- MySQL 8.0
- Playwright + BeautifulSoup
- JWT pentru autentificare

---

## Configurare și rulare

### 1. Pornire MySQL

```bash
docker-compose up -d
```

### 2. Backend Django

```bash
cd backend-django
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Backend-ul va fi disponibil la `http://localhost:8000`.

### 3. Scraper Service

```bash
cd ../scraper-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

### 4. Frontend Vue

```bash
cd ../frontend-vue
npm install
npm run dev
```

Frontend-ul va fi disponibil la `http://localhost:5173`.

---

## Observații

- Verifică `docker-compose.yml` pentru setările MySQL.
- Asigură-te că `backend-django` are fișierul `.env` corect configurat pentru conexiunea la baza de date.
- `scraper-service` rulează independent și oferă date de componente pentru backend.
- `frontend-vue` comunică cu backend-ul Django prin API REST.
