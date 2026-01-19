from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, F
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from airport.models import Flight, Seat, Ticket
from airport.serializers import (
    FlightDetailSerializer,
    FlightListSerializer,
    FlightSerializer,
    SeatListSerializer,
)
from airport.tests.utils import (
    detail_url,
    sample_airplane,
    sample_airplane_type,
    sample_airport,
    sample_city,
    sample_country,
    sample_crew_member,
    sample_flight,
    sample_order,
    sample_route,
    sample_seat,
)

FLIGHT_URL = reverse("airport:flight-list")


class UnauthenticatedFlightApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_not_required(self):
        res = self.client.get(FLIGHT_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_read_only_if_unauthorized(self):
        now = timezone.now()
        crew_members = [sample_crew_member().id]

        payload = {
            "route": sample_route().id,
            "airplane": sample_airplane().id,
            "crew_members": crew_members,
            "status": Flight.Status.SCHEDULED,
            "departure_time": now + timedelta(days=1),
            "arrival_time": now + timedelta(days=1, hours=2),
        }
        res = self.client.post(FLIGHT_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedFlightApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_flight_list(self):
        sample_flight()
        res = self.client.get(FLIGHT_URL)

        flights = Flight.objects.annotate(
            capacity=F("airplane__rows") * F("airplane__seats_in_row")
        ).annotate(tickets_available=F("capacity") - Count(
            "tickets", distinct=True)
        )
        serializer = FlightListSerializer(flights, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_filter_flight_by_origin(self):
        country = sample_country()

        city_1 = sample_city(name="Test City 1", country=country)
        city_2 = sample_city(name="Test City 2", country=country)
        city_3 = sample_city(name="Test City 3", country=country)

        airport_1 = sample_airport(
            name="Test Airport 1", city=city_1, code="TTT"
        )
        airport_2 = sample_airport(
            name="Test Airport 2", city=city_2, code="EEE"
        )
        airport_3 = sample_airport(
            name="Test Airport 3", city=city_3, code="SSS"
        )

        route_1 = sample_route(source=airport_1, destination=airport_2)
        route_2 = sample_route(source=airport_2, destination=airport_3)
        route_3 = sample_route(source=airport_3, destination=airport_1)

        airplane_1 = sample_airplane(
            tail_number="N11111",
            airplane_type=sample_airplane_type(manufacturer="Test_1"),
        )
        airplane_2 = sample_airplane(
            tail_number="N22222",
            airplane_type=sample_airplane_type(manufacturer="Test_2"),
        )
        airplane_3 = sample_airplane(
            tail_number="N33333",
            airplane_type=sample_airplane_type(manufacturer="Test_3"),
        )

        flight_1 = sample_flight(route=route_1, airplane=airplane_1)
        flight_2 = sample_flight(route=route_2, airplane=airplane_2)
        flight_3 = sample_flight(route=route_3, airplane=airplane_3)

        flights = Flight.objects.annotate(
            capacity=F("airplane__rows") * F("airplane__seats_in_row")
        ).annotate(tickets_available=F("capacity") - Count(
            "tickets", distinct=True)
        )

        serializer_flight_1 = FlightListSerializer(flights.get(id=flight_1.id))
        serializer_flight_2 = FlightListSerializer(flights.get(id=flight_2.id))
        serializer_flight_3 = FlightListSerializer(flights.get(id=flight_3.id))

        res = self.client.get(FLIGHT_URL, data={"origin": f"{city_1.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertIn(serializer_flight_1.data, res.data["results"])
        self.assertNotIn(serializer_flight_2.data, res.data["results"])
        self.assertNotIn(serializer_flight_3.data, res.data["results"])

    def test_filter_flight_by_destination(self):
        country = sample_country()

        city_1 = sample_city(name="Test City 1", country=country)
        city_2 = sample_city(name="Test City 2", country=country)
        city_3 = sample_city(name="Test City 3", country=country)

        airport_1 = sample_airport(
            name="Test Airport 1", city=city_1, code="TTT"
        )
        airport_2 = sample_airport(
            name="Test Airport 2", city=city_2, code="EEE"
        )
        airport_3 = sample_airport(
            name="Test Airport 3", city=city_3, code="SSS"
        )

        route_1 = sample_route(source=airport_1, destination=airport_2)
        route_2 = sample_route(source=airport_2, destination=airport_3)
        route_3 = sample_route(source=airport_3, destination=airport_1)

        airplane_1 = sample_airplane(
            tail_number="N11111",
            airplane_type=sample_airplane_type(manufacturer="Test_1"),
        )
        airplane_2 = sample_airplane(
            tail_number="N22222",
            airplane_type=sample_airplane_type(manufacturer="Test_2"),
        )
        airplane_3 = sample_airplane(
            tail_number="N33333",
            airplane_type=sample_airplane_type(manufacturer="Test_3"),
        )

        flight_1 = sample_flight(route=route_1, airplane=airplane_1)
        flight_2 = sample_flight(route=route_2, airplane=airplane_2)
        flight_3 = sample_flight(route=route_3, airplane=airplane_3)

        flights = Flight.objects.annotate(
            capacity=F("airplane__rows") * F("airplane__seats_in_row")
        ).annotate(tickets_available=F("capacity") - Count(
            "tickets", distinct=True)
        )

        serializer_flight_1 = FlightListSerializer(flights.get(id=flight_1.id))
        serializer_flight_2 = FlightListSerializer(flights.get(id=flight_2.id))
        serializer_flight_3 = FlightListSerializer(flights.get(id=flight_3.id))

        res = self.client.get(FLIGHT_URL, data={"destination": f"{city_2.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertIn(serializer_flight_1.data, res.data["results"])
        self.assertNotIn(serializer_flight_2.data, res.data["results"])
        self.assertNotIn(serializer_flight_3.data, res.data["results"])

    def test_filter_flight_by_status(self):
        country = sample_country()

        city_1 = sample_city(name="Test City 1", country=country)
        city_2 = sample_city(name="Test City 2", country=country)
        city_3 = sample_city(name="Test City 3", country=country)

        airport_1 = sample_airport(
            name="Test Airport 1", city=city_1, code="TTT"
        )
        airport_2 = sample_airport(
            name="Test Airport 2", city=city_2, code="EEE"
        )
        airport_3 = sample_airport(
            name="Test Airport 3", city=city_3, code="SSS"
        )

        route_1 = sample_route(source=airport_1, destination=airport_2)
        route_2 = sample_route(source=airport_2, destination=airport_3)
        route_3 = sample_route(source=airport_3, destination=airport_1)

        airplane_1 = sample_airplane(
            tail_number="N11111",
            airplane_type=sample_airplane_type(manufacturer="Test_1"),
        )
        airplane_2 = sample_airplane(
            tail_number="N22222",
            airplane_type=sample_airplane_type(manufacturer="Test_2"),
        )
        airplane_3 = sample_airplane(
            tail_number="N33333",
            airplane_type=sample_airplane_type(manufacturer="Test_3"),
        )

        flight_1 = sample_flight(
            route=route_1, airplane=airplane_1, status=Flight.Status.SCHEDULED
        )
        flight_2 = sample_flight(
            route=route_2, airplane=airplane_2, status=Flight.Status.DELAYED
        )
        flight_3 = sample_flight(
            route=route_3, airplane=airplane_3, status=Flight.Status.BOARDING
        )

        flights = Flight.objects.annotate(
            capacity=F("airplane__rows") * F("airplane__seats_in_row")
        ).annotate(tickets_available=F("capacity") - Count(
            "tickets", distinct=True)
        )

        serializer_flight_1 = FlightListSerializer(flights.get(id=flight_1.id))
        serializer_flight_2 = FlightListSerializer(flights.get(id=flight_2.id))
        serializer_flight_3 = FlightListSerializer(flights.get(id=flight_3.id))

        res = self.client.get(
            FLIGHT_URL, data={"status": "scheduled, delayed"}
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)
        self.assertIn(serializer_flight_1.data, res.data["results"])
        self.assertIn(serializer_flight_2.data, res.data["results"])
        self.assertNotIn(serializer_flight_3.data, res.data["results"])

    def test_filter_flight_by_departure_time(self):
        country = sample_country()

        city_1 = sample_city(name="Test City 1", country=country)
        city_2 = sample_city(name="Test City 2", country=country)
        city_3 = sample_city(name="Test City 3", country=country)

        airport_1 = sample_airport(
            name="Test Airport 1", city=city_1, code="TTT"
        )
        airport_2 = sample_airport(
            name="Test Airport 2", city=city_2, code="EEE"
        )
        airport_3 = sample_airport(
            name="Test Airport 3", city=city_3, code="SSS"
        )

        route_1 = sample_route(source=airport_1, destination=airport_2)
        route_2 = sample_route(source=airport_2, destination=airport_3)
        route_3 = sample_route(source=airport_3, destination=airport_1)

        airplane_1 = sample_airplane(
            tail_number="N11111",
            airplane_type=sample_airplane_type(manufacturer="Test_1"),
        )
        airplane_2 = sample_airplane(
            tail_number="N22222",
            airplane_type=sample_airplane_type(manufacturer="Test_2"),
        )
        airplane_3 = sample_airplane(
            tail_number="N33333",
            airplane_type=sample_airplane_type(manufacturer="Test_3"),
        )

        now = timezone.now()

        flight_1 = sample_flight(
            route=route_1,
            airplane=airplane_1,
            departure_time=now + timedelta(hours=3)
        )
        flight_2 = sample_flight(
            route=route_2,
            airplane=airplane_2,
            departure_time=now + timedelta(hours=2)
        )
        flight_3 = sample_flight(
            route=route_3,
            airplane=airplane_3,
            departure_time=now + timedelta(hours=1)
        )

        flights = Flight.objects.annotate(
            capacity=F("airplane__rows") * F("airplane__seats_in_row")
        ).annotate(tickets_available=F("capacity") - Count(
            "tickets", distinct=True)
        )

        serializer_flight_1 = FlightListSerializer(flights.get(id=flight_1.id))
        serializer_flight_2 = FlightListSerializer(flights.get(id=flight_2.id))
        serializer_flight_3 = FlightListSerializer(flights.get(id=flight_3.id))

        res = self.client.get(
            FLIGHT_URL,
            data={
                "departure_time":
                    f"{(now + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")}"
            },
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)
        self.assertIn(serializer_flight_1.data, res.data["results"])
        self.assertIn(serializer_flight_2.data, res.data["results"])
        self.assertNotIn(serializer_flight_3.data, res.data["results"])

    def test_filter_flight_by_departure_date(self):
        country = sample_country()

        city_1 = sample_city(name="Test City 1", country=country)
        city_2 = sample_city(name="Test City 2", country=country)
        city_3 = sample_city(name="Test City 3", country=country)

        airport_1 = sample_airport(
            name="Test Airport 1", city=city_1, code="TTT"
        )
        airport_2 = sample_airport(
            name="Test Airport 2", city=city_2, code="EEE"
        )
        airport_3 = sample_airport(
            name="Test Airport 3", city=city_3, code="SSS"
        )

        route_1 = sample_route(source=airport_1, destination=airport_2)
        route_2 = sample_route(source=airport_2, destination=airport_3)
        route_3 = sample_route(source=airport_3, destination=airport_1)

        airplane_1 = sample_airplane(
            tail_number="N11111",
            airplane_type=sample_airplane_type(manufacturer="Test_1"),
        )
        airplane_2 = sample_airplane(
            tail_number="N22222",
            airplane_type=sample_airplane_type(manufacturer="Test_2"),
        )
        airplane_3 = sample_airplane(
            tail_number="N33333",
            airplane_type=sample_airplane_type(manufacturer="Test_3"),
        )

        now = timezone.now()

        flight_1 = sample_flight(
            route=route_1,
            airplane=airplane_1,
            departure_time=now + timedelta(days=1),
            arrival_time=now + timedelta(days=1, hours=1),
        )
        flight_2 = sample_flight(
            route=route_2,
            airplane=airplane_2,
            departure_time=now + timedelta(days=2),
            arrival_time=now + timedelta(days=2, hours=1),
        )
        flight_3 = sample_flight(
            route=route_3,
            airplane=airplane_3,
            departure_time=now + timedelta(days=3),
            arrival_time=now + timedelta(days=3, hours=1),
        )

        flights = Flight.objects.annotate(
            capacity=F("airplane__rows") * F("airplane__seats_in_row")
        ).annotate(tickets_available=F("capacity") - Count(
            "tickets", distinct=True)
        )

        serializer_flight_1 = FlightListSerializer(flights.get(id=flight_1.id))
        serializer_flight_2 = FlightListSerializer(flights.get(id=flight_2.id))
        serializer_flight_3 = FlightListSerializer(flights.get(id=flight_3.id))

        res = self.client.get(
            FLIGHT_URL,
            data={
                "departure_date":
                    f"{(now + timedelta(days=1)).strftime("%Y-%m-%d")}"
            },
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertIn(serializer_flight_1.data, res.data["results"])
        self.assertNotIn(serializer_flight_2.data, res.data["results"])
        self.assertNotIn(serializer_flight_3.data, res.data["results"])

    def test_retrieve_flight_detail(self):
        flight = sample_flight()
        url = detail_url("flight", flight.id)

        flights = Flight.objects.annotate(
            capacity=F("airplane__rows") * F("airplane__seats_in_row")
        ).annotate(tickets_available=F("capacity") - Count(
            "tickets", distinct=True)
        )
        serializer = FlightDetailSerializer(flights.get(id=flight.id))

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_available_seats_for_flight(self):
        flight = sample_flight()
        url = detail_url("flight", flight.id) + "available_seats/"

        all_seats = flight.airplane.seats.all()
        taken_seats_ids = Ticket.objects.filter(flight=flight).values_list(
            "seat_id", flat=True
        )
        available_seats = all_seats.exclude(id__in=taken_seats_ids)
        serializer = SeatListSerializer(available_seats, many=True)

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_available_seats_excludes_booked_seats(self):
        flight = sample_flight()
        booked_seat = sample_seat(
            airplane=flight.airplane, row=1, seat_number=1
        )

        tickets = [
            {
                "flight": flight,
                "seat": booked_seat,
            },
        ]
        sample_order(tickets=tickets)

        url = detail_url("flight", flight.id) + "available_seats/"

        all_seats = flight.airplane.seats.all()
        taken_seats_ids = Ticket.objects.filter(flight=flight).values_list(
            "seat_id", flat=True
        )
        available_seats = all_seats.exclude(id__in=taken_seats_ids)

        serializer = SeatListSerializer(available_seats, many=True)
        booked_seat_serializer = SeatListSerializer(
            Seat.objects.get(id=booked_seat.id), many=False
        )

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(booked_seat_serializer.data, res.data)
        self.assertEqual(res.data, serializer.data)

    def test_available_seats_returns_only_seats_for_correct_airplane(self):
        airplane_1 = sample_airplane(tail_number="N11111")
        flight = sample_flight(airplane=airplane_1)

        airplane_2 = sample_airplane(tail_number="N22222")
        sample_flight(airplane=airplane_2)

        url = detail_url("flight", flight.id) + "available_seats/"
        res = self.client.get(url)

        for seat in res.data:
            self.assertEqual(seat["airplane"]["id"], flight.airplane.id)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_forbidden_if_not_staff(self):
        now = timezone.now()
        crew_members = [sample_crew_member().id]

        payload = {
            "route": sample_route().id,
            "airplane": sample_airplane().id,
            "crew_members": crew_members,
            "status": Flight.Status.SCHEDULED,
            "departure_time": now + timedelta(days=1),
            "arrival_time": now + timedelta(days=1, hours=2),
        }
        res = self.client.post(FLIGHT_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_forbidden_if_not_staff(self):
        flight = sample_flight()
        url = detail_url("flight", flight.id)
        payload = {
            "status": Flight.Status.CANCELED,
        }
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_forbidden_if_not_staff(self):
        flight = sample_flight()
        url = detail_url("flight", flight.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminFlightApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com", password="testpassword", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_allowed_if_staff(self):
        now = timezone.now()
        crew_members = [sample_crew_member().id]

        payload = {
            "route": sample_route().id,
            "airplane": sample_airplane().id,
            "crew_members": crew_members,
            "status": Flight.Status.SCHEDULED,
            "departure_time": now + timedelta(days=1),
            "arrival_time": now + timedelta(days=1, hours=2),
        }
        res = self.client.post(FLIGHT_URL, payload)
        flight = Flight.objects.get(id=res.data["id"])
        serializer = FlightSerializer(flight)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data, serializer.data)

    def test_update_allowed_if_staff(self):
        flight = sample_flight()
        url = detail_url("flight", flight.id)
        payload = {
            "status": Flight.Status.CANCELED,
        }
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], payload["status"])

    def test_delete_allowed_if_staff(self):
        flight = sample_flight()
        url = detail_url("flight", flight.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_create_with_bad_arrival_time(self):
        now = timezone.now()
        crew_members = [sample_crew_member().id]

        payload = {
            "route": sample_route().id,
            "airplane": sample_airplane().id,
            "crew_members": crew_members,
            "status": Flight.Status.SCHEDULED,
            "departure_time": now,
            "arrival_time": now + timedelta(hours=-1),
        }
        res = self.client.post(FLIGHT_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
