# tests.py

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from base.apps.user.models import User


class BuyerViewsTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        # Create a test user
        self.user = User.objects.create_user('testuser', 'testpassword')
        # URLs
        self.get_cart_url = reverse('get_cart')

    def test_get_cart_empty(self):
        """Test retrieving an empty cart."""
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(self.get_cart_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"message": "Cart is empty."})
