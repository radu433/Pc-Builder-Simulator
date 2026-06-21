from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from .models import UserProfile


class RegisterTests(APITestCase):
    def test_register_success(self):
        url = reverse('register')
        data = {'username': 'newuser', 'password': 'StrongPass123!', 'email': 'new@test.com'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_register_duplicate_username(self):
        User.objects.create_user(username='existing', password='pass123')
        url = reverse('register')
        data = {'username': 'existing', 'password': 'AnotherPass123!'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserProfileTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='profileuser', password='testpass123')

    def test_profile_unauthenticated(self):
        url = reverse('profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_get_authenticated(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_profile_update(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('profile')
        data = {'buget_max': '5000.00', 'rezolutie_dorita': '1440p'}
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(str(profile.buget_max), '5000.00')
        self.assertEqual(profile.rezolutie_dorita, '1440p')
