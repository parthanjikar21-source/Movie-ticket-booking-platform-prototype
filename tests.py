from django.utils.crypto import get_random_string
TEST_PASSWORD = get_random_string(24)
from django.contrib.auth.models import User
from django.test import TestCase, Client
class AccountTests(TestCase):
    def test_login_logout(self):
        User.objects.create_user(username="u",password="TEST_PASSWORD",email="u@example.com"); c=Client(); self.assertEqual(c.post("/accounts/login/", {"username":"u","password":"TEST_PASSWORD"}).status_code,302); self.assertEqual(c.post("/accounts/logout/").status_code,302)
