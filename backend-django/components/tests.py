from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from .models import CPU, SaveBuild

class CPUApiTests(APITestCase):
    def setUp(self):
        # Cream cateva procesoare pentru testare
        self.cpu1 = CPU.objects.create(
            nume="Intel Core i9-14900K",
            brand="Intel",
            pret=2800.00,
            socket="LGA1700",
            serie="Core i9",
            nuclee=24,
            threaduri=32,
            frecventa_ghz=3.2,
            consum_tdp=125,
            stoc=True
        )
        self.cpu2 = CPU.objects.create(
            nume="AMD Ryzen 7 7800X3D",
            brand="AMD",
            pret=1900.00,
            socket="AM5",
            serie="Ryzen 7",
            nuclee=8,
            threaduri=16,
            frecventa_ghz=4.2,
            consum_tdp=120,
            stoc=True
        )

    def test_get_cpu_list(self):
        """
        Testam daca putem prelua lista de procesoare si daca datele returnate sunt corecte
        """
        url = reverse('cpu-list') # presupunem ca router-ul creeaza numele default pentru url
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # response.data e paginat daca am setat StandardPagination, verificam 'results'
        if 'results' in response.data:
            self.assertEqual(len(response.data['results']), 2)
        else:
            self.assertEqual(len(response.data), 2)

    def test_cpu_search_and_filter(self):
        """
        Testam daca filtrarea pe baza de brand functioneaza.
        """
        url = reverse('cpu-list')
        response = self.client.get(url, {'brand': 'AMD'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['nume'], "AMD Ryzen 7 7800X3D")


class SaveBuildApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.url = reverse('saved-builds-list')
        
        # Cream componente dummy pentru build
        self.cpu = CPU.objects.create(
            nume="Test CPU", brand="Test", pret=100.0, socket="Test", serie="Test",
            nuclee=4, frecventa_ghz=3.0, consum_tdp=65
        )

    def test_save_build_unauthorized(self):
        """
        Un utilizator neautentificat nu ar trebui sa poata salva un build.
        """
        data = {
            "nume": "My First Build",
            "cpu": self.cpu.id,
            "pret_total": 100.0
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_save_build_authorized(self):
        """
        Un utilizator autentificat ar trebui sa poata salva un build cu succes.
        """
        self.client.force_authenticate(user=self.user)
        data = {
            "nume": "My First Build",
            "cpu": self.cpu.id,
            "pret_total": 100.0
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verificam daca user-ul a fost asociat build-ului
        build = SaveBuild.objects.get(id=response.data['id'])
        self.assertEqual(build.user, self.user)
