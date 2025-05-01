from django.test import TestCase
from django.urls import reverse
from django.core import mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient
from rest_framework import status
from users.models import User  # Import your User model

class PasswordResetTests(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            email='test@example.com',
            name='Test User',
            password='testpassword123'
        )
        self.client = APIClient()
    
    def test_forgot_password_valid_email(self):
        """Test that a password reset email is sent for a valid email"""
        url = reverse('forgot-password')
        response = self.client.post(url, {'email': 'test@example.com'}, format='json')
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Password reset email sent')
        
        # Check that email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Reset your AI Marketer password')
        self.assertEqual(mail.outbox[0].to, ['test@example.com'])
        
        # Verify email content contains reset link
        self.assertIn('/reset-password?uid=', mail.outbox[0].body)
        self.assertIn('token=', mail.outbox[0].body)
    
    def test_forgot_password_invalid_email(self):
        """Test that no email is sent for an invalid email"""
        url = reverse('forgot-password')
        response = self.client.post(url, {'email': 'nonexistent@example.com'}, format='json')
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Check that no email was sent
        self.assertEqual(len(mail.outbox), 0)
    
    def test_reset_password_valid_token(self):
        """Test password reset with valid token"""
        # Generate token
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        
        # Make reset request
        url = reverse('reset-password')
        response = self.client.post(url, {
            'uid': uid,
            'token': token,
            'new_password': 'newpassword123'
        }, format='json')
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Password has been reset')
        
        # Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpassword123'))
    
    def test_reset_password_invalid_token(self):
        """Test password reset with invalid token"""
        # Generate uid but use invalid token
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        invalid_token = "invalid-token"
        
        # Make reset request
        url = reverse('reset-password')
        response = self.client.post(url, {
            'uid': uid,
            'token': invalid_token,
            'new_password': 'newpassword123'
        }, format='json')
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Verify password was not changed
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password('newpassword123'))
    
    def test_reset_password_invalid_uid(self):
        """Test password reset with invalid uid"""
        # Generate token but use invalid uid
        token = default_token_generator.make_token(self.user)
        invalid_uid = "invalid-uid"
        
        # Make reset request
        url = reverse('reset-password')
        response = self.client.post(url, {
            'uid': invalid_uid,
            'token': token,
            'new_password': 'newpassword123'
        }, format='json')
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Verify password was not changed
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password('newpassword123'))
    
    def test_reset_password_weak_password(self):
        """Test password reset with weak password"""
        # Generate token
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        
        # Make reset request with weak password
        url = reverse('reset-password')
        response = self.client.post(url, {
            'uid': uid,
            'token': token,
            'new_password': '123'  # Too short
        }, format='json')
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Verify password was not changed
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password('123'))