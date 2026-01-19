from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from airport.models import AirplaneType
from airport.serializers import AirplaneTypeSerializer
from airport.tests.utils import detail_url, sample_airplane_type

AIRPLANE_TYPE_URL = reverse("airport:airplanetype-list")


class UnauthenticatedAirplaneTypeApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_not_required(self):
        res = self.client.get(AIRPLANE_TYPE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_read_only_if_unauthorized(self):
        payload = {"manufacturer": "Test_Manufacturer", "model": "Test_Model"}
        res = self.client.post(AIRPLANE_TYPE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedAirplaneTypeApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_airplane_type_list(self):
        sample_airplane_type()
        res = self.client.get(AIRPLANE_TYPE_URL)
        airplane_types = AirplaneType.objects.all()
        serializer = AirplaneTypeSerializer(airplane_types, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_retrieve_airplane_type_detail(self):
        airplane_type = sample_airplane_type()
        url = detail_url("airplanetype", airplane_type.id)
        serializer = AirplaneTypeSerializer(airplane_type)

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_forbidden_if_not_staff(self):
        payload = {"manufacturer": "Test_Manufacturer", "model": "Test_Model"}
        res = self.client.post(AIRPLANE_TYPE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_forbidden_if_not_staff(self):
        airplane_type = sample_airplane_type()
        url = detail_url("airplanetype", airplane_type.id)
        payload = {
            "manufacturer": "Updated_Manufacturer",
        }
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_forbidden_if_not_staff(self):
        airplane_type = sample_airplane_type()
        url = detail_url("airplanetype", airplane_type.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminAirplaneTypeApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com", password="testpassword", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_allowed_if_staff(self):
        payload = {"manufacturer": "Test_Manufacturer", "model": "Test_Model"}
        res = self.client.post(AIRPLANE_TYPE_URL, payload)
        airplane_type = AirplaneType.objects.get(id=res.data["id"])
        serializer = AirplaneTypeSerializer(airplane_type)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data, serializer.data)

    def test_update_allowed_if_staff(self):
        airplane_type = sample_airplane_type()
        url = detail_url("airplanetype", airplane_type.id)
        payload = {
            "manufacturer": "Updated_Manufacturer",
        }
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["manufacturer"], payload["manufacturer"])

    def test_delete_allowed_if_staff(self):
        airplane_type = sample_airplane_type()
        url = detail_url("airplanetype", airplane_type.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_create_with_bad_input_manufacturer(self):
        payload = {"manufacturer": "", "model": "Test_Model"}

        res = self.client.post(AIRPLANE_TYPE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
