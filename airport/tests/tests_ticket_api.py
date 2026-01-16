from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from airport.models import Ticket
from airport.serializers import TicketListSerializer, TicketDetailSerializer
from airport.tests.utils import detail_url, sample_flight, sample_seat, sample_order, sample_user, sample_airplane, \
    sample_seat_class

TICKET_URL = reverse("airport:ticket-list")


class UnauthenticatedTicketApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(TICKET_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_requires_auth(self):
        flight = sample_flight()
        seat = sample_seat(airplane=flight.airplane, row=1, seat_number=1)
        payload = {
            "tickets": [
                {
                    "flight": flight.id,
                    "seat": seat.id,
                },
            ]
        }

        res = self.client.post(TICKET_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedTicketApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_ticket_list(self):
        flight = sample_flight()
        seat = sample_seat(airplane=flight.airplane, row=1, seat_number=1)
        tickets = [
            {
                "flight": flight,
                "seat": seat,
            },
        ]
        sample_order(user=self.user, tickets=tickets)

        res = self.client.get(TICKET_URL)
        tickets = Ticket.objects.filter(order__user=self.user)
        serializer = TicketListSerializer(tickets, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_filter_tickets_by_order(self):
        flight = sample_flight()
        seat_1 = sample_seat(airplane=flight.airplane, row=1, seat_number=1)
        tickets_1 = [
            {
                "flight": flight,
                "seat": seat_1,
            },
        ]
        order_1 = sample_order(user=self.user, tickets=tickets_1)

        seat_2 = sample_seat(airplane=flight.airplane, row=1, seat_number=2)
        tickets_2 = [
            {
                "flight": flight,
                "seat": seat_2,
            },
        ]
        order_2 = sample_order(user=self.user, tickets=tickets_2)

        res = self.client.get(TICKET_URL, data={"orders": f"{order_1.id}"})
        tickets_1 = order_1.tickets.all()
        tickets_2 = order_2.tickets.all()
        serializer_1 = TicketListSerializer(tickets_1, many=True)
        serializer_2 = TicketListSerializer(tickets_2, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertIn(serializer_1.data[0], res.data["results"])
        self.assertNotIn(serializer_2.data[0], res.data["results"])

    def test_filter_tickets_by_flight(self):
        airplane_1 = sample_airplane(tail_number="N11111")
        airplane_2 = sample_airplane(tail_number="N22222")

        flight_1 = sample_flight(airplane=airplane_1)
        flight_2 = sample_flight(airplane=airplane_2)

        seat_1 = sample_seat(airplane=flight_1.airplane, row=1, seat_number=1)
        seat_2 = sample_seat(airplane=flight_2.airplane, row=1, seat_number=1)

        tickets = [
            {
                "flight": flight_1,
                "seat": seat_1,
            },
            {
                "flight": flight_2,
                "seat": seat_2,
            },
        ]
        sample_order(user=self.user, tickets=tickets)

        res = self.client.get(TICKET_URL, data={"flights": f"{flight_1.id}"})
        ticket_1 = Ticket.objects.get(flight_id=flight_1.id, seat_id=seat_1.id)
        ticket_2 = Ticket.objects.get(flight_id=flight_2.id, seat_id=seat_2.id)
        serializer_1 = TicketListSerializer(ticket_1)
        serializer_2 = TicketListSerializer(ticket_2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertIn(serializer_1.data, res.data["results"])
        self.assertNotIn(serializer_2.data, res.data["results"])

    def test_filter_tickets_by_seat_class(self):
        airplane = sample_airplane(rows=20)
        flight = sample_flight(airplane=airplane)

        first_class = sample_seat_class(name="First", priority=0, multiplier=Decimal("3.00"))
        business_class = sample_seat_class(name="Business", priority=1, multiplier=Decimal("2.00"))
        economy_class = sample_seat_class(name="Economy", priority=2, multiplier=Decimal("1.00"))

        seat_1 = sample_seat(airplane=flight.airplane, row=1, seat_number=1, seat_class=first_class)
        seat_2 = sample_seat(airplane=flight.airplane, row=10, seat_number=1, seat_class=business_class)
        seat_3 = sample_seat(airplane=flight.airplane, row=20, seat_number=1, seat_class=economy_class)

        tickets = [
            {
                "flight": flight,
                "seat": seat_1,
            },
            {
                "flight": flight,
                "seat": seat_2,
            },
            {
                "flight": flight,
                "seat": seat_3,
            },
        ]
        sample_order(user=self.user, tickets=tickets)

        res = self.client.get(TICKET_URL, data={"seat_classes": f"{first_class.id}"})
        ticket_1 = Ticket.objects.get(flight_id=flight.id, seat_id=seat_1.id)
        ticket_2 = Ticket.objects.get(flight_id=flight.id, seat_id=seat_2.id)
        ticket_3 = Ticket.objects.get(flight_id=flight.id, seat_id=seat_3.id)
        serializer_1 = TicketListSerializer(ticket_1)
        serializer_2 = TicketListSerializer(ticket_2)
        serializer_3 = TicketListSerializer(ticket_3)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertIn(serializer_1.data, res.data["results"])
        self.assertNotIn(serializer_2.data, res.data["results"])
        self.assertNotIn(serializer_3.data, res.data["results"])

    def test_filter_tickets_by_price_min(self):
        airplane = sample_airplane(rows=20)
        flight = sample_flight(airplane=airplane)

        first_class = sample_seat_class(name="First", priority=0, multiplier=Decimal("3.00"))
        economy_class = sample_seat_class(name="Economy", priority=2, multiplier=Decimal("1.00"))

        seat_1 = sample_seat(airplane=flight.airplane, row=1, seat_number=1, seat_class=first_class)
        seat_2 = sample_seat(airplane=flight.airplane, row=20, seat_number=1, seat_class=economy_class)

        tickets = [
            {
                "flight": flight,
                "seat": seat_1,
            },
            {
                "flight": flight,
                "seat": seat_2,
            },
        ]
        sample_order(user=self.user, tickets=tickets)

        ticket_1 = Ticket.objects.get(flight_id=flight.id, seat_id=seat_1.id)
        ticket_2 = Ticket.objects.get(flight_id=flight.id, seat_id=seat_2.id)

        res = self.client.get(TICKET_URL, data={"price_min": f"{(ticket_1.price-Decimal("10.0"))}"})

        serializer_1 = TicketListSerializer(ticket_1)
        serializer_2 = TicketListSerializer(ticket_2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertIn(serializer_1.data, res.data["results"])
        self.assertNotIn(serializer_2.data, res.data["results"])

    def test_filter_tickets_by_price_max(self):
        airplane = sample_airplane(rows=20)
        flight = sample_flight(airplane=airplane)

        first_class = sample_seat_class(name="First", priority=0, multiplier=Decimal("3.00"))
        economy_class = sample_seat_class(name="Economy", priority=2, multiplier=Decimal("1.00"))

        seat_1 = sample_seat(airplane=flight.airplane, row=1, seat_number=1, seat_class=first_class)
        seat_2 = sample_seat(airplane=flight.airplane, row=20, seat_number=1, seat_class=economy_class)

        tickets = [
            {
                "flight": flight,
                "seat": seat_1,
            },
            {
                "flight": flight,
                "seat": seat_2,
            },
        ]
        sample_order(user=self.user, tickets=tickets)

        ticket_1 = Ticket.objects.get(flight_id=flight.id, seat_id=seat_1.id)
        ticket_2 = Ticket.objects.get(flight_id=flight.id, seat_id=seat_2.id)

        res = self.client.get(TICKET_URL, data={"price_max": f"{(ticket_2.price+Decimal("10.0"))}"})

        serializer_1 = TicketListSerializer(ticket_1)
        serializer_2 = TicketListSerializer(ticket_2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertNotIn(serializer_1.data, res.data["results"])
        self.assertIn(serializer_2.data, res.data["results"])

    def test_filter_tickets_by_price_min_and_price_max(self):
        airplane = sample_airplane(rows=20)
        flight = sample_flight(airplane=airplane)

        first_class = sample_seat_class(name="First", priority=0, multiplier=Decimal("3.00"))
        business_class = sample_seat_class(name="Business", priority=1, multiplier=Decimal("2.00"))
        economy_class = sample_seat_class(name="Economy", priority=2, multiplier=Decimal("1.00"))

        seat_1 = sample_seat(airplane=flight.airplane, row=1, seat_number=1, seat_class=first_class)
        seat_2 = sample_seat(airplane=flight.airplane, row=10, seat_number=1, seat_class=business_class)
        seat_3 = sample_seat(airplane=flight.airplane, row=20, seat_number=1, seat_class=economy_class)

        tickets = [
            {
                "flight": flight,
                "seat": seat_1,
            },
            {
                "flight": flight,
                "seat": seat_2,
            },
            {
                "flight": flight,
                "seat": seat_3,
            },
        ]
        sample_order(user=self.user, tickets=tickets)

        ticket_1 = Ticket.objects.get(flight_id=flight.id, seat_id=seat_1.id)
        ticket_2 = Ticket.objects.get(flight_id=flight.id, seat_id=seat_2.id)
        ticket_3 = Ticket.objects.get(flight_id=flight.id, seat_id=seat_3.id)

        res = self.client.get(TICKET_URL, data={
            "price_min": f"{(ticket_3.price + Decimal("10.0"))}",
            "price_max": f"{(ticket_1.price - Decimal("10.0"))}",
        })

        serializer_1 = TicketListSerializer(ticket_1)
        serializer_2 = TicketListSerializer(ticket_2)
        serializer_3 = TicketListSerializer(ticket_3)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertNotIn(serializer_1.data, res.data["results"])
        self.assertIn(serializer_2.data, res.data["results"])
        self.assertNotIn(serializer_3.data, res.data["results"])

    def test_filter_tickets_price_min_cant_be_bigger_than_price_max(self):
        airplane = sample_airplane(rows=20)
        flight = sample_flight(airplane=airplane)

        first_class = sample_seat_class(name="First", priority=0, multiplier=Decimal("3.00"))
        business_class = sample_seat_class(name="Business", priority=1, multiplier=Decimal("2.00"))
        economy_class = sample_seat_class(name="Economy", priority=2, multiplier=Decimal("1.00"))

        seat_1 = sample_seat(airplane=flight.airplane, row=1, seat_number=1, seat_class=first_class)
        seat_2 = sample_seat(airplane=flight.airplane, row=10, seat_number=1, seat_class=business_class)
        seat_3 = sample_seat(airplane=flight.airplane, row=20, seat_number=1, seat_class=economy_class)

        tickets = [
            {
                "flight": flight,
                "seat": seat_1,
            },
            {
                "flight": flight,
                "seat": seat_2,
            },
            {
                "flight": flight,
                "seat": seat_3,
            },
        ]
        sample_order(user=self.user, tickets=tickets)

        ticket_1 = Ticket.objects.get(flight_id=flight.id, seat_id=seat_1.id)
        ticket_3 = Ticket.objects.get(flight_id=flight.id, seat_id=seat_3.id)

        res = self.client.get(TICKET_URL, data={
            "price_min": f"{(ticket_1.price + Decimal("10.0"))}",
            "price_max": f"{(ticket_3.price - Decimal("10.0"))}",
        })

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ticket_list_returns_only_correct_user_ticket(self):
        user_a = self.user
        user_b = sample_user(email="user_b@test.com")

        flight = sample_flight()
        seat_a = sample_seat(airplane=flight.airplane, row=1, seat_number=1)
        seat_b = sample_seat(airplane=flight.airplane, row=1, seat_number=2)
        tickets_a = [
            {
                "flight": flight,
                "seat": seat_a,
            },
        ]
        tickets_b = [
            {
                "flight": flight,
                "seat": seat_b,
            },
        ]
        user_a_order = sample_order(user=user_a, tickets=tickets_a)
        user_b_order = sample_order(user=user_b, tickets=tickets_b)

        res = self.client.get(TICKET_URL)
        tickets_a = user_a_order.tickets
        tickets_b = user_b_order.tickets
        serializer_a = TicketListSerializer(tickets_a, many=True)
        serializer_b = TicketListSerializer(tickets_b, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer_a.data)
        self.assertIn(serializer_a.data[0], res.data["results"])
        self.assertNotIn(serializer_b.data[0], res.data["results"])

    def test_retrieve_ticket_detail(self):
        flight = sample_flight()
        seat = sample_seat(airplane=flight.airplane, row=1, seat_number=1)
        tickets = [
            {
                "flight": flight,
                "seat": seat,
            },
        ]
        sample_order(user=self.user, tickets=tickets)
        ticket = Ticket.objects.get(flight_id=flight.id, seat_id=seat.id)

        url = detail_url("ticket", ticket.id)
        serializer = TicketDetailSerializer(ticket)

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_cant_retrieve_another_user_ticket_detail(self):
        other_user = sample_user(email="other_user@test.com")

        flight = sample_flight()
        seat = sample_seat(airplane=flight.airplane, row=1, seat_number=1)
        tickets = [
            {
                "flight": flight,
                "seat": seat,
            },
        ]
        sample_order(user=other_user, tickets=tickets)
        ticket = Ticket.objects.get(flight_id=flight.id, seat_id=seat.id)

        url = detail_url("ticket", ticket.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_forbidden(self):
        flight = sample_flight()
        seat = sample_seat(airplane=flight.airplane, row=1, seat_number=1)
        payload = {
            "tickets": [
                {
                    "flight": flight.id,
                    "seat": seat.id,
                },
            ]
        }
        res = self.client.post(TICKET_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_forbidden(self):
        flight = sample_flight()
        seat_1 = sample_seat(airplane=flight.airplane, row=1, seat_number=1)
        seat_2 = sample_seat(airplane=flight.airplane, row=1, seat_number=2)
        tickets = [
            {
                "flight": flight,
                "seat": seat_1,
            },
        ]
        sample_order(user=self.user, tickets=tickets)
        ticket = Ticket.objects.get(flight_id=flight.id, seat_id=seat_1.id)

        url = detail_url("ticket", ticket.id)
        payload = {
            "seat": seat_2.id,
        }
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_forbidden(self):
        flight = sample_flight()
        seat = sample_seat(airplane=flight.airplane, row=1, seat_number=1)
        tickets = [
            {
                "flight": flight,
                "seat": seat,
            },
        ]
        sample_order(user=self.user, tickets=tickets)
        ticket = Ticket.objects.get(flight_id=flight.id, seat_id=seat.id)

        url = detail_url("ticket", ticket.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class AdminTicketApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com",
            password="testpassword",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_list_returns_all_tickets_if_staff(self):
        user_a = sample_user(email="user_a@test.com")
        user_b = sample_user(email="user_b@test.com")

        flight = sample_flight()
        seat_a = sample_seat(airplane=flight.airplane, row=1, seat_number=1)
        seat_b = sample_seat(airplane=flight.airplane, row=1, seat_number=2)
        tickets_a = [
            {
                "flight": flight,
                "seat": seat_a,
            },
        ]
        tickets_b = [
            {
                "flight": flight,
                "seat": seat_b,
            },
        ]
        user_a_order = sample_order(user=user_a, tickets=tickets_a)
        user_b_order = sample_order(user=user_b, tickets=tickets_b)

        res = self.client.get(TICKET_URL)
        tickets_a = user_a_order.tickets
        tickets_b = user_b_order.tickets
        all_tickets = Ticket.objects.all()
        serializer_a = TicketListSerializer(tickets_a, many=True)
        serializer_b = TicketListSerializer(tickets_b, many=True)
        serializer_all = TicketListSerializer(all_tickets, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer_all.data, res.data["results"])
        self.assertIn(serializer_a.data[0], res.data["results"])
        self.assertIn(serializer_b.data[0], res.data["results"])

    def test_staff_can_filter_tickets_by_user(self):
        user_a = sample_user(email="user_a@test.com")
        user_b = sample_user(email="user_b@test.com")

        flight = sample_flight()
        seat_a = sample_seat(airplane=flight.airplane, row=1, seat_number=1)
        seat_b = sample_seat(airplane=flight.airplane, row=1, seat_number=2)
        tickets_a = [
            {
                "flight": flight,
                "seat": seat_a,
            },
        ]
        tickets_b = [
            {
                "flight": flight,
                "seat": seat_b,
            },
        ]
        user_a_order = sample_order(user=user_a, tickets=tickets_a)
        user_b_order = sample_order(user=user_b, tickets=tickets_b)

        res = self.client.get(TICKET_URL, data={"users": f"{user_a.id}"})
        tickets_a = user_a_order.tickets
        tickets_b = user_b_order.tickets
        serializer_a = TicketListSerializer(tickets_a, many=True)
        serializer_b = TicketListSerializer(tickets_b, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertIn(serializer_a.data[0], res.data["results"])
        self.assertNotIn(serializer_b.data[0], res.data["results"])