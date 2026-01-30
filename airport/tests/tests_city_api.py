from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from airport.models import City
from airport.serializers import (
    CityDetailSerializer,
    CityListSerializer,
    CitySerializer,
)
from airport.tests.utils import detail_url, sample_city, sample_country

CITY_URL = reverse("airport:city-list")


class UnauthenticatedCityApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_not_required(self):
        res = self.client.get(CITY_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_read_only_if_unauthorized(self):
        country = sample_country()
        payload = {
            "name": "Test City",
            "country": country.id,
            "timezone": "Europe/Warsaw",
        }
        res = self.client.post(CITY_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedCityApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_city_list(self):
        sample_city()

        res = self.client.get(CITY_URL)
        cities = City.objects.all()
        serializer = CityListSerializer(cities, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_filter_cities_by_country(self):
        country_1 = sample_country(iso_code="AA")
        country_2 = sample_country(iso_code="BB")
        country_3 = sample_country(iso_code="CC")

        city_1 = sample_city(name="Test City 1", country=country_1)
        city_2 = sample_city(name="Test City 2", country=country_2)
        city_3 = sample_city(name="Test City 3", country=country_3)

        serializer_city_1 = CityListSerializer(city_1)
        serializer_city_2 = CityListSerializer(city_2)
        serializer_city_3 = CityListSerializer(city_3)

        res = self.client.get(
            CITY_URL, data={"countries": f"{country_1.id}, {country_2.id}"}
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)
        self.assertIn(serializer_city_1.data, res.data["results"])
        self.assertIn(serializer_city_2.data, res.data["results"])
        self.assertNotIn(serializer_city_3.data, res.data["results"])

    def test_retrieve_city_detail(self):
        city = sample_city()
        url = detail_url("city", city.id)
        serializer = CityDetailSerializer(city)

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_forbidden_if_not_staff(self):
        country = sample_country()
        payload = {
            "name": "Test City",
            "country": country.id,
            "timezone": "Europe/Warsaw",
        }
        res = self.client.post(CITY_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_forbidden_if_not_staff(self):
        city = sample_city()
        url = detail_url("city", city.id)
        payload = {
            "name": "Updated Test City",
        }
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_forbidden_if_not_staff(self):
        city = sample_city()
        url = detail_url("city", city.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminCityApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com", password="testpassword", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_allowed_if_staff(self):
        country = sample_country()
        payload = {
            "name": "Test City",
            "country": country.id,
            "timezone": "Europe/Warsaw",
        }
        res = self.client.post(CITY_URL, payload)
        city = City.objects.get(id=res.data["id"])
        serializer = CitySerializer(city)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data, serializer.data)

    def test_update_allowed_if_staff(self):
        city = sample_city()
        url = detail_url("city", city.id)
        payload = {
            "name": "Updated Test City",
        }
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], payload["name"])

    def test_delete_allowed_if_staff(self):
        city = sample_city()
        url = detail_url("city", city.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_create_with_bad_input_country(self):
        payload = {
            "name": "Test City",
            "country": "Bad Country",
            "timezone": "Europe/Warsaw",
        }
        res = self.client.post(CITY_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_bad_input_timezone(self):
        country = sample_country()
        payload = {
            "name": "Test City",
            "country": country.id,
            "timezone": "Bad Timezone",
        }
        res = self.client.post(CITY_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
