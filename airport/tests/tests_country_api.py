from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from airport.models import Country
from airport.serializers import CountrySerializer
from airport.tests.utils import detail_url, sample_country

COUNTRY_URL = reverse("airport:country-list")


class UnauthenticatedCountryApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_not_required(self):
        res = self.client.get(COUNTRY_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_read_only_if_unauthorized(self):
        payload = {"name": "Test Country", "iso_code": "TC"}
        res = self.client.post(COUNTRY_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedCountryApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_country_list(self):
        sample_country()

        res = self.client.get(COUNTRY_URL)
        countries = Country.objects.all()
        serializer = CountrySerializer(countries, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_retrieve_country_detail(self):
        country = sample_country()
        url = detail_url("country", country.id)
        serializer = CountrySerializer(country)

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_forbidden_if_not_staff(self):
        payload = {"name": "Test Country", "iso_code": "TC"}
        res = self.client.post(COUNTRY_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_forbidden_if_not_staff(self):
        country = sample_country()
        url = detail_url("country", country.id)
        payload = {
            "name": "Updated Test Country",
        }
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_forbidden_if_not_staff(self):
        country = sample_country()
        url = detail_url("country", country.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminCountryApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com", password="testpassword", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_allowed_if_staff(self):
        payload = {"name": "Test Country", "iso_code": "TC"}
        res = self.client.post(COUNTRY_URL, payload)
        country = Country.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(country, key))

    def test_update_allowed_if_staff(self):
        country = sample_country()
        url = detail_url("country", country.id)
        payload = {
            "name": "Updated Test Country",
        }
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], payload["name"])

    def test_delete_allowed_if_staff(self):
        country = sample_country()
        url = detail_url("country", country.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_create_with_bad_input_iso_code(self):
        payload = {"name": "Test Country", "iso_code": "TEST"}
        res = self.client.post(COUNTRY_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
