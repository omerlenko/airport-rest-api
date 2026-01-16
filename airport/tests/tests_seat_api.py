from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse

from rest_framework.test import APIClient
from airport.models import Seat
from airport.serializers import SeatListSerializer, SeatDetailSerializer
from airport.tests.utils import detail_url, sample_seat_class, sample_airplane, sample_seat, sample_airplane_type

SEAT_URL = reverse("airport:seat-list")


class UnauthenticatedSeatApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(SEAT_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedSeatApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_seat_list(self):
        sample_airplane(rows=1, seats_in_row=6)
        res = self.client.get(SEAT_URL)
        seats = Seat.objects.all()
        serializer = SeatListSerializer(seats, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_filter_seat_by_airplane(self):
        airplane_1 = sample_airplane(
            rows=1,
            seats_in_row=1,
            tail_number="N11111",
            airplane_type=sample_airplane_type(manufacturer="Test_1"),
        )
        airplane_2 = sample_airplane(
            rows=1,
            seats_in_row=1,
            tail_number="N22222",
            airplane_type=sample_airplane_type(manufacturer="Test_2"),
        )
        airplane_3 = sample_airplane(
            rows=1,
            seats_in_row=1,
            tail_number="N33333",
            airplane_type=sample_airplane_type(manufacturer="Test_3"),
        )

        seat_1 = sample_seat(airplane=airplane_1)
        seat_2 = sample_seat(airplane=airplane_2)
        seat_3 = sample_seat(airplane=airplane_3)

        serializer_seat_1 = SeatListSerializer(seat_1)
        serializer_seat_2 = SeatListSerializer(seat_2)
        serializer_seat_3 = SeatListSerializer(seat_3)

        res = self.client.get(SEAT_URL, data={"airplanes": f"{airplane_1.id}, {airplane_2.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)
        self.assertIn(serializer_seat_1.data, res.data["results"])
        self.assertIn(serializer_seat_2.data, res.data["results"])
        self.assertNotIn(serializer_seat_3.data, res.data["results"])

    def test_retrieve_seat_detail(self):
        seat = sample_seat()
        url = detail_url("seat", seat.id)
        serializer = SeatDetailSerializer(seat)

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_not_allowed(self):
        airplane = sample_airplane()
        seat_class = sample_seat_class()

        payload = {
            "airplane": airplane.id,
            "row": 1,
            "seat_number": 1,
            "seat_class": seat_class.id,
        }
        res = self.client.post(SEAT_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_not_allowed(self):
        seat = sample_seat()
        url = detail_url("seat", seat.id)

        payload = {
            "seat_number": 2,
        }
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_not_allowed(self):
        seat = sample_seat()
        url = detail_url("seat", seat.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class AdminSeatApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com",
            password="testpassword",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_not_allowed_if_staff(self):
        airplane = sample_airplane()
        seat_class = sample_seat_class()

        payload = {
            "airplane": airplane.id,
            "row": 1,
            "seat_number": 1,
            "seat_class": seat_class.id,
        }
        res = self.client.post(SEAT_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
