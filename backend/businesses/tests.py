# businesses/tests.py

import requests
from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from rest_framework import status

User = get_user_model()

class GoogleMapsAPITest(TestCase):
    def test_api_key_is_configured(self):
        """Check if the Google Maps API key is configured"""
        self.assertTrue(hasattr(settings, 'GOOGLE_MAPS_API_KEY'), 
                        "GOOGLE_MAPS_API_KEY is not defined in settings")
        self.assertTrue(bool(settings.GOOGLE_MAPS_API_KEY), 
                        "GOOGLE_MAPS_API_KEY is empty")
        
        # Print the key (masked) for debugging
        api_key = settings.GOOGLE_MAPS_API_KEY
        masked_key = f"{api_key[:5]}...{api_key[-5:]}" if len(api_key) > 10 else "***"
        print(f"Using API key: {masked_key}")
    
    def test_api_key_works(self):
        """Test if the Google Maps API key works by making a simple request"""
        api_key = settings.GOOGLE_MAPS_API_KEY
        place_id = "ChIJj61dQgK6j4AR4GeTYWZsKWw"  # Google HQ
        
        url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=name&key={api_key}"
        
        try:
            response = requests.get(url)
            data = response.json()
            
            print(f"Google API response: {data}")
            
            self.assertEqual(response.status_code, 200, "API request failed")
            self.assertEqual(data.get('status'), 'OK', f"API returned error: {data.get('error_message', 'Unknown error')}")
            self.assertIn('result', data, "No result in API response")
            self.assertIn('name', data['result'], "Name not found in result")
            
        except Exception as e:
            self.fail(f"API request raised an exception: {str(e)}")


class GooglePlaceLookupViewTest(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            email='test@example.com', 
            password='testpassword',
            name='Test User',  # Add the name field
            is_active=True
        )
        
        # Set up the API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # URL for the API endpoint
        self.url = reverse('place-lookup')
    
    def test_place_lookup_valid_id(self):
        """Test lookup with valid place ID"""
        # Google HQ place ID
        place_id = "ChIJj61dQgK6j4AR4GeTYWZsKWw"
        
        # Make the request
        response = self.client.post(self.url, {'place_id': place_id}, format='json')
        
        # Print the response for debugging
        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.data}")
        
        # Check if the request was successful
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check if we got some basic data back
        self.assertIn('name', response.data)
        self.assertIn('category', response.data)
    
    def test_place_lookup_invalid_id(self):
        """Test lookup with invalid place ID"""
        response = self.client.post(self.url, {'place_id': 'invalid_id'}, format='json')
        
        # Print the response for debugging
        print(f"Invalid ID - Response status: {response.status_code}")
        print(f"Invalid ID - Response data: {response.data}")
        
        # Should return some kind of error, not a 500
        self.assertNotEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def test_place_lookup_missing_id(self):
        """Test lookup with missing place ID"""
        response = self.client.post(self.url, {}, format='json')
        
        # Print the response for debugging
        print(f"Missing ID - Response status: {response.status_code}")
        print(f"Missing ID - Response data: {response.data}")
        
        # Should return a bad request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)