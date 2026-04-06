import os
import sys
import django

#conenctare script la django
def init_django():
    # logica de path
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    BACKEND_PATH = os.path.join(BASE_DIR, 'backend-django')

    # adaugam cale catre core
    if BACKEND_PATH not in sys.path:
        sys.path.append(BACKEND_PATH)

    # verifica daca e core
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

    try:
        django.setup()
        print("✅ Django setup finalizat cu succes.")
    except Exception as e:
        print(f"❌ Eroare la setup-ul Django: {e}")
        sys.exit(1)