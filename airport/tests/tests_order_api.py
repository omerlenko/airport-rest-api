from datetime import UTC, datetime, timedelta

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from airport.models import Flight, Order, Ticket
from airport.serializers import OrderDetailSerializer, OrderListSerializer
from airport.tests.utils import (
    detail_url,
    sample_airplane,
    sample_flight,
    sample_order,
    sample_seat,
    sample_user,
)

ORDER_URL = reverse("airport:order-list")


class UnauthenticatedOrderApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(ORDER_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedOrderApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_order_list(self):
        sample_order(user=self.user)
        res = self.client.get(ORDER_URL)

        orders = Order.objects.filter(user=self.user).annotate(
            total_price=Sum("tickets__price")
        )
        serializer = OrderListSerializer(orders, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_orders_list_scoped_to_correct_user(self):
        user_1 = self.user
        user_2 = sample_user(email="another_user@test.com")

        flight = sample_flight()
        airplane = flight.airplane
        seat_1 = sample_seat(airplane=airplane, row=1, seat_number=1)
        seat_2 = sample_seat(airplane=airplane, row=1, seat_number=2)

        tickets_1 = [{"flight": flight, "seat": seat_1}]
        tickets_2 = [{"flight": flight, "seat": seat_2}]

        sample_order(user=user_1, tickets=tickets_1)
        sample_order(user=user_2, tickets=tickets_2)
        res = self.client.get(ORDER_URL)

        orders_1 = Order.objects.filter(user=self.user).annotate(
            total_price=Sum("tickets__price")
        )
        serializer_order_1 = OrderListSerializer(orders_1, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"], serializer_order_1.data)

    def test_retrieve_order_detail(self):
        order = sample_order(user=self.user)
        url = detail_url("order", order.id)

        order = (
            Order.objects.filter(user=self.user)
            .annotate(total_price=Sum("tickets__price"))
            .get(id=order.id)
        )
        serializer = OrderDetailSerializer(order)

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_another_user_order_not_allowed(self):
        another_user = sample_user(email="another_user@test.com")
        another_users_order = sample_order(user=another_user)
        url = detail_url("order", another_users_order.id)

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_if_authenticated(self):
        flight = sample_flight()
        airplane = flight.airplane
        seat_1 = sample_seat(airplane=airplane, row=1, seat_number=1)
        seat_2 = sample_seat(airplane=airplane, row=1, seat_number=2)

        payload = {
            "tickets": [
                {
                    "flight": flight.id,
                    "seat": seat_1.id,
                },
                {
                    "flight": flight.id,
                    "seat": seat_2.id,
                },
            ]
        }

        res = self.client.post(ORDER_URL, payload, format="json")
        order = Order.objects.annotate(total_price=Sum("tickets__price")).get(
            id=res.data["id"]
        )
        serializer = OrderDetailSerializer(order)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data, serializer.data)
        self.assertEqual(order.user, self.user)

    def test_cant_create_order_with_seat_on_another_plane(self):
        airplane_a = sample_airplane(tail_number="N11111")
        airplane_b = sample_airplane(tail_number="N22222")
        flight_a = sample_flight(airplane=airplane_a)

        seat_b = sample_seat(airplane=airplane_b, row=1, seat_number=1)

        payload = {
            "tickets": [
                {
                    "flight": flight_a.id,
                    "seat": seat_b.id,
                }
            ]
        }

        res = self.client.post(ORDER_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cant_create_order_with_duplicate_seats_in_payload(self):
        flight = sample_flight()
        seat_1 = sample_seat(airplane=flight.airplane, row=1, seat_number=1)

        payload = {
            "tickets": [
                {
                    "flight": flight.id,
                    "seat": seat_1.id,
                },
                {
                    "flight": flight.id,
                    "seat": seat_1.id,
                },
            ]
        }

        res = self.client.post(ORDER_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cant_create_order_with_ticket_that_already_exists(self):
        flight = sample_flight()
        seat_1 = sample_seat(airplane=flight.airplane, row=1, seat_number=1)

        tickets = [
            {
                "flight": flight,
                "seat": seat_1,
            }
        ]
        sample_order(user=self.user, tickets=tickets)

        payload = {
            "tickets": [
                {
                    "flight": flight.id,
                    "seat": seat_1.id,
                },
            ]
        }

        res = self.client.post(ORDER_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cant_create_order_with_empty_tickets(self):
        payload = {"tickets": []}

        res = self.client.post(ORDER_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cant_create_order_with_past_flight(self):
        departure_time = datetime(2000, 1, 1, 10, 0, tzinfo=UTC)
        arrival_time = departure_time + timedelta(hours=1)
        flight = sample_flight(
            departure_time=departure_time, arrival_time=arrival_time
        )
        seat_1 = sample_seat(airplane=flight.airplane, row=1, seat_number=1)

        payload = {
            "tickets": [
                {
                    "flight": flight.id,
                    "seat": seat_1.id,
                },
            ]
        }
        res = self.client.post(ORDER_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cant_create_order_with_flight_that_is_not_scheduled(self):
        flight = sample_flight(status=Flight.Status.CANCELED)
        seat_1 = sample_seat(airplane=flight.airplane, row=1, seat_number=1)

        payload = {
            "tickets": [
                {
                    "flight": flight.id,
                    "seat": seat_1.id,
                },
            ]
        }
        res = self.client.post(ORDER_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_order_atomicity(self):
        flight = sample_flight()
        airplane = flight.airplane
        wrong_airplane = sample_airplane(tail_number="N11111")
        seat_correct = sample_seat(airplane=airplane, row=1, seat_number=1)
        seat_invalid = sample_seat(
            airplane=wrong_airplane, row=1, seat_number=2
        )

        payload = {
            "tickets": [
                {
                    "flight": flight.id,
                    "seat": seat_correct.id,
                },
                {
                    "flight": flight.id,
                    "seat": seat_invalid.id,
                },
            ]
        }

        order_count = Order.objects.count()
        ticket_count = Ticket.objects.count()

        res = self.client.post(ORDER_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), order_count)
        self.assertEqual(Ticket.objects.count(), ticket_count)
        self.assertNotIn("id", res.data)

    def test_update_not_allowed_if_authenticated(self):
        flight = sample_flight()
        airplane = flight.airplane
        seat_1 = sample_seat(airplane=airplane, row=1, seat_number=1)
        seat_2 = sample_seat(airplane=airplane, row=1, seat_number=2)

        tickets = [
            {
                "flight": flight,
                "seat": seat_1,
            },
        ]
        order = sample_order(user=self.user, tickets=tickets)
        url = detail_url("order", order.id)

        payload = {
            "tickets": [
                {
                    "flight": flight.id,
                    "seat": seat_2.id,
                },
            ]
        }

        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_not_allowed_if_authenticated(self):
        order = sample_order(user=self.user)
        url = detail_url("order", order.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
