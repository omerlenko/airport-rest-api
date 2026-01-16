from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse

from rest_framework.test import APIClient
from airport.models import Airport
from airport.serializers import AirportListSerializer, AirportDetailSerializer, AirportSerializer
from airport.tests.utils import sample_city, sample_airport, sample_country, detail_url

AIRPORT_URL = reverse("airport:airport-list")


class UnauthenticatedAirportApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_not_required(self):
        res = self.client.get(AIRPORT_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_read_only_if_unauthorized(self):
        city = sample_city()
        payload = {
            "name": "Test Airport",
            "city": city.id,
            "code": "TSA",
        }
        res = self.client.post(AIRPORT_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedAirportApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_airport_list(self):
        sample_airport()
        res = self.client.get(AIRPORT_URL)
        airports = Airport.objects.all()
        serializer = AirportListSerializer(airports, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_filter_airports_by_city(self):
        country = sample_country()

        city_1 = sample_city(name="Test City 1", country=country)
        city_2 = sample_city(name="Test City 2", country=country)
        city_3 = sample_city(name="Test City 3", country=country)

        airport_1 = sample_airport(name="Test Airport 1", city=city_1, code="TTT")
        airport_2 = sample_airport(name="Test Airport 2", city=city_2, code="EEE")
        airport_3 = sample_airport(name="Test Airport 3", city=city_3, code="SSS")

        serializer_airport_1 = AirportListSerializer(airport_1)
        serializer_airport_2 = AirportListSerializer(airport_2)
        serializer_airport_3 = AirportListSerializer(airport_3)

        res = self.client.get(AIRPORT_URL, data={"cities": f"{city_1.id}, {city_2.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)
        self.assertIn(serializer_airport_1.data, res.data["results"])
        self.assertIn(serializer_airport_2.data, res.data["results"])
        self.assertNotIn(serializer_airport_3.data, res.data["results"])


    def test_retrieve_airport_detail(self):
        airport = sample_airport()
        url = detail_url("airport", airport.id)
        serializer = AirportDetailSerializer(airport)

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_forbidden_if_not_staff(self):
        city = sample_city()
        payload = {
            "name": "Test Airport",
            "city": city.id,
            "code": "TSA",
        }
        res = self.client.post(AIRPORT_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_forbidden_if_not_staff(self):
        airport = sample_airport()
        url = detail_url("airport", airport.id)
        payload = {
            "name":  "Updated Test Airport",
        }
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_forbidden_if_not_staff(self):
        airport = sample_airport()
        url = detail_url("airport", airport.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminAirportApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com",
            password="testpassword",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_allowed_if_staff(self):
        city = sample_city()
        payload = {
            "name": "Test Airport",
            "city": city.id,
            "code": "TSA",
        }
        res = self.client.post(AIRPORT_URL, payload)
        airport = Airport.objects.get(id=res.data["id"])
        serializer = AirportSerializer(airport)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data, serializer.data)

    def test_update_allowed_if_staff(self):
        airport = sample_airport()
        url = detail_url("airport", airport.id)
        payload = {
            "name": "Updated Test Airport",
        }
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], payload["name"])

    def test_delete_allowed_if_staff(self):
        airport = sample_airport()
        url = detail_url("airport", airport.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_create_with_bad_input_city(self):
        payload = {
            "name": "Test Airport",
            "city": "Bad City",
            "code": "TSA",
        }
        res = self.client.post(AIRPORT_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_bad_input_code(self):
        city = sample_city()
        payload = {
            "name": "Test Airport",
            "city": city.id,
            "code": "BADCODE",
        }
        res = self.client.post(AIRPORT_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)