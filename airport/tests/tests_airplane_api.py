from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from airport.models import Airplane
from airport.serializers import (
    AirplaneDetailSerializer,
    AirplaneListSerializer,
    AirplaneSerializer,
)
from airport.tests.utils import (
    create_basic_three_seat_classes,
    detail_url,
    sample_airplane,
    sample_airplane_type,
)

AIRPLANE_URL = reverse("airport:airplane-list")


class UnauthenticatedAirplaneApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_not_required(self):
        res = self.client.get(AIRPLANE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_read_only_if_unauthorized(self):
        airplane_type = sample_airplane_type()

        payload = {
            "tail_number": 1,
            "rows": 10,
            "seats_in_row": 6,
            "airplane_type": airplane_type,
        }
        res = self.client.post(AIRPLANE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedAirplaneApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_airplane_list(self):
        sample_airplane()
        res = self.client.get(AIRPLANE_URL)
        airplanes = Airplane.objects.all()
        serializer = AirplaneListSerializer(airplanes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_filter_airplane_by_airplane_type(self):
        airplane_type_1 = sample_airplane_type(
            manufacturer="Test_Manufacturer_1"
        )
        airplane_type_2 = sample_airplane_type(
            manufacturer="Test_Manufacturer_2"
        )
        airplane_type_3 = sample_airplane_type(
            manufacturer="Test_Manufacturer_3"
        )

        airplane_1 = sample_airplane(
            tail_number="N11111", airplane_type=airplane_type_1
        )
        airplane_2 = sample_airplane(
            tail_number="N22222", airplane_type=airplane_type_2
        )
        airplane_3 = sample_airplane(
            tail_number="N33333", airplane_type=airplane_type_3
        )

        serializer_airplane_1 = AirplaneListSerializer(airplane_1)
        serializer_airplane_2 = AirplaneListSerializer(airplane_2)
        serializer_airplane_3 = AirplaneListSerializer(airplane_3)

        res = self.client.get(
            AIRPLANE_URL,
            data={
                "airplane_types": f"{airplane_type_1.id}, {airplane_type_2.id}"
            },
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)
        self.assertIn(serializer_airplane_1.data, res.data["results"])
        self.assertIn(serializer_airplane_2.data, res.data["results"])
        self.assertNotIn(serializer_airplane_3.data, res.data["results"])

    def test_retrieve_airplane_detail(self):
        airplane = sample_airplane()
        url = detail_url("airplane", airplane.id)
        serializer = AirplaneDetailSerializer(airplane)

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_forbidden_if_not_staff(self):
        airplane_type = sample_airplane_type()
        payload = {
            "tail_number": "N12345",
            "rows": 10,
            "seats_in_row": 6,
            "airplane_type": airplane_type,
        }
        res = self.client.post(AIRPLANE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_forbidden_if_not_staff(self):
        airplane = sample_airplane()
        url = detail_url("airplane", airplane.id)
        payload = {"tail_number": "N00000"}
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_forbidden_if_not_staff(self):
        airplane = sample_airplane()
        url = detail_url("airplane", airplane.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminAirplaneApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com", password="testpassword", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_allowed_if_staff(self):
        create_basic_three_seat_classes()
        airplane_type = sample_airplane_type()
        payload = {
            "tail_number": "N12345",
            "rows": 10,
            "seats_in_row": 6,
            "airplane_type": airplane_type.id,
        }
        res = self.client.post(AIRPLANE_URL, payload)
        airplane = Airplane.objects.get(id=res.data["id"])
        serializer = AirplaneSerializer(airplane)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data, serializer.data)

    def test_update_allowed_if_staff(self):
        airplane = sample_airplane()
        url = detail_url("airplane", airplane.id)
        payload = {"tail_number": "N00000"}
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["tail_number"], payload["tail_number"])

    def test_delete_allowed_if_staff(self):
        airplane = sample_airplane()
        url = detail_url("airplane", airplane.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_create_with_bad_input_tail_number(self):
        airplane_type = sample_airplane_type()
        payload = {
            "tail_number": "12345BAD",
            "rows": 10,
            "seats_in_row": 6,
            "airplane_type": airplane_type.id,
        }
        res = self.client.post(AIRPLANE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
