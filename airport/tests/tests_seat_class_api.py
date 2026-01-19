from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from airport.models import SeatClass
from airport.serializers import SeatClassSerializer
from airport.tests.utils import detail_url, sample_seat_class

SEAT_CLASS_URL = reverse("airport:seatclass-list")


class UnauthenticatedSeatClassApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_not_required(self):
        res = self.client.get(SEAT_CLASS_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_requires_auth(self):
        payload = {
            "name": "Economy",
            "priority": 0,
            "multiplier": 1.00,
        }
        res = self.client.post(SEAT_CLASS_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedSeatClassApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_seat_class_list(self):
        sample_seat_class()
        res = self.client.get(SEAT_CLASS_URL)
        seat_classes = SeatClass.objects.all()
        serializer = SeatClassSerializer(seat_classes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_retrieve_seat_class_detail(self):
        seat_class = sample_seat_class()
        url = detail_url("seatclass", seat_class.id)
        serializer = SeatClassSerializer(seat_class)

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_forbidden_if_not_staff(self):
        payload = {
            "name": "Economy",
            "priority": 0,
            "multiplier": 1.00,
        }
        res = self.client.post(SEAT_CLASS_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_forbidden_if_not_staff(self):
        seat_class = sample_seat_class()
        url = detail_url("seatclass", seat_class.id)
        payload = {
            "name": "Business",
        }
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_forbidden_if_not_staff(self):
        seat_class = sample_seat_class()
        url = detail_url("seatclass", seat_class.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminSeatClassApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com", password="testpassword", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_allowed_if_staff(self):
        payload = {
            "name": "Economy",
            "priority": 0,
            "multiplier": 1.00,
        }
        res = self.client.post(SEAT_CLASS_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_validate_seat_class_priority(self):
        payload = {
            "name": "Economy",
            "priority": -1,
            "multiplier": 1.00,
        }
        res = self.client.post(SEAT_CLASS_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_validate_seat_class_multiplier(self):
        payload = {
            "name": "Economy",
            "priority": 0,
            "multiplier": 0.01,
        }
        res = self.client.post(SEAT_CLASS_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_allowed_if_staff(self):
        seat_class = sample_seat_class()
        url = detail_url("seatclass", seat_class.id)
        payload = {
            "name": "Business",
        }
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_delete_allowed_if_staff(self):
        seat_class = sample_seat_class()
        url = detail_url("seatclass", seat_class.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
