from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from user.serializers import UserSerializer

USER_CREATE_URL = reverse("user:create")
TOKEN_URL = reverse("user:token_obtain_pair")
TOKEN_REFRESH_URL = reverse("user:token_refresh")
TOKEN_VERIFY_URL = reverse("user:token_verify")
USER_MANAGE_URL = reverse("user:manage")


class UnauthenticatedUserApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_create_user(self):
        payload = {
            "email": "user@test.com",
            "password": "test12345",
        }

        res = self.client.post(USER_CREATE_URL, payload, format="json")
        user = get_user_model().objects.get(email=payload["email"])
        serializer = UserSerializer(user)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(serializer.data, res.data)
        self.assertTrue(user.check_password(payload["password"]))
        self.assertNotIn("password", res.data)

    def test_duplicate_email_fails(self):
        get_user_model().objects.create_user(
            email="user@test.com", password="test12345"
        )

        payload = {
            "email": "user@test.com",
            "password": "test12345",
        }

        res = self.client.post(USER_CREATE_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_validation_fails(self):
        payload = {
            "email": "user@test.com",
            "password": "test",
        }
        user_count = get_user_model().objects.count()

        res = self.client.post(USER_CREATE_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(get_user_model().objects.count(), user_count)

    def test_me_requires_auth(self):
        res = self.client.get(USER_MANAGE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedUserApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.com", password="test12345"
        )

    def test_valid_credentials_returns_token(self):
        payload = {
            "email": "user@test.com",
            "password": "test12345",
        }
        res = self.client.post(TOKEN_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("refresh", res.data)
        self.assertIn("access", res.data)

    def test_invalid_credentials_rejected(self):
        payload = {
            "email": "user@test.com",
            "password": "wrong_password",
        }
        res = self.client.post(TOKEN_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("refresh", res.data)
        self.assertNotIn("access", res.data)

    def test_token_refresh_returns_new_access_token(self):
        payload = {
            "email": "user@test.com",
            "password": "test12345",
        }
        tokens = self.client.post(TOKEN_URL, payload)

        payload = {"refresh": tokens.data["refresh"]}
        res = self.client.post(TOKEN_REFRESH_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)

    def test_token_verify_accepts_valid_token(self):
        payload = {
            "email": "user@test.com",
            "password": "test12345",
        }
        tokens = self.client.post(TOKEN_URL, payload)

        payload = {"token": tokens.data["access"]}
        res = self.client.post(TOKEN_VERIFY_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_token_verify_rejects_invalid_token(self):
        payload = {"token": "invalid_token"}
        res = self.client.post(TOKEN_VERIFY_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_current_user(self):
        self.client.force_authenticate(self.user)
        serializer = UserSerializer(self.user)

        res = self.client.get(USER_MANAGE_URL, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)

    def test_me_with_jwt_token(self):
        payload = {"email": "user@test.com", "password": "test12345"}
        token_res = self.client.post(TOKEN_URL, payload, format="json")
        access = token_res.data["access"]

        res = self.client.get(
            USER_MANAGE_URL, HTTP_AUTHORIZATION=f"Bearer {access}"
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["email"], payload["email"])

    def test_me_updates_user_email(self):
        self.client.force_authenticate(self.user)
        payload = {"email": "updated_email@test.com"}
        res = self.client.patch(USER_MANAGE_URL, payload, format="json")
        self.user.refresh_from_db()
        serializer = UserSerializer(self.user)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data["email"], res.data["email"])

    def test_me_updates_user_password(self):
        self.client.force_authenticate(self.user)
        payload = {"password": "new_password"}
        res = self.client.patch(USER_MANAGE_URL, payload, format="json")
        self.user.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(self.user.check_password(payload["password"]))
