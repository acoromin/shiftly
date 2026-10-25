from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import SecurityThrottle
from .throttling import consume_attempt


class LoginThrottlingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ana', password='secret-password')

    def test_application_login_blocks_repeated_attempts_and_recovers_after_window(self):
        url = reverse('login')
        self.assertEqual(self.client.post(url, {'username': 'ana', 'password': 'wrong'}).status_code, 200)
        user_counter = SecurityThrottle.objects.order_by('-pk').first()
        user_counter.attempts = 10
        user_counter.save(update_fields=['attempts'])
        response = self.client.post(url, {'username': 'ana', 'password': 'secret-password'})
        self.assertContains(response, 'Demasiados intentos')
        self.assertNotIn('_auth_user_id', self.client.session)
        user_counter.window_started_at = timezone.now() - timedelta(minutes=6)
        user_counter.save(update_fields=['window_started_at'])
        self.assertRedirects(self.client.post(url, {
            'username': 'ana', 'password': 'secret-password',
        }), reverse('dashboard:index'))

    def test_spoofed_forwarded_header_does_not_bypass_login_limit(self):
        url = reverse('login')
        for _ in range(10):
            consume_attempt('login-user', '127.0.0.1\0ana', limit=10, window_seconds=300)
        response = self.client.post(url, {'username': 'ana', 'password': 'secret-password'},
                                    HTTP_X_FORWARDED_FOR='203.0.113.10')
        self.assertContains(response, 'Demasiados intentos')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_technical_admin_login_is_limited_too(self):
        technician = User.objects.create_superuser(username='technician', password='secret-password')
        for _ in range(10):
            consume_attempt('login-user', '127.0.0.1\0technician', limit=10, window_seconds=300)
        response = self.client.post(reverse('admin:login'), {
            'username': technician.username, 'password': 'secret-password',
        })
        self.assertContains(response, 'Demasiados intentos')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_qr_fragment_can_resume_after_login_via_posted_next(self):
        url = reverse('timeclock:scan') + '#workplace=123e4567-e89b-12d3-a456-426614174000&token=securetoken1234567890'
        response = self.client.post(reverse('login'), {
            'username': 'ana', 'password': 'secret-password', 'next': url,
        })
        self.assertRedirects(response, url, fetch_redirect_response=False)
