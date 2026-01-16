from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse

from rest_framework.test import APIClient
from airport.models import Route
from airport.serializers import RouteListSerializer, RouteDetailSerializer, RouteSerializer
from airport.tests.utils import sample_airport, sample_country, sample_city, sample_route, detail_url

ROUTE_URL = reverse("airport:route-list")


class UnauthenticatedRouteApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_not_required(self):
        res = self.client.get(ROUTE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_read_only_if_unauthorized(self):
        country = sample_country()

        city_1 = sample_city(name= "Test City 1", country=country)
        city_2 = sample_city(name= "Test City 2", country=country)

        airport_1 = sample_airport(city=city_1, code="QQQ")
        airport_2 = sample_airport(city=city_2, code="WWW")
        payload = {
            "source": airport_1.id,
            "destination": airport_2.id,
            "distance": 1000,
        }
        res = self.client.post(ROUTE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedRouteApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_route_list(self):
        sample_route()
        res = self.client.get(ROUTE_URL)
        routes = Route.objects.all()
        serializer = RouteListSerializer(routes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_filter_route_by_source(self):
        country = sample_country()

        city_1 = sample_city(name="Test City 1", country=country)
        city_2 = sample_city(name="Test City 2", country=country)
        city_3 = sample_city(name="Test City 3", country=country)

        airport_1 = sample_airport(name="Test Airport 1", city=city_1, code="TTT")
        airport_2 = sample_airport(name="Test Airport 2", city=city_2, code="EEE")
        airport_3 = sample_airport(name="Test Airport 3", city=city_3, code="SSS")

        route_1 = sample_route(source=airport_1, destination=airport_2)
        route_2 = sample_route(source=airport_2, destination=airport_3)
        route_3 = sample_route(source=airport_3, destination=airport_1)

        serializer_route_1 = RouteListSerializer(route_1)
        serializer_route_2 = RouteListSerializer(route_2)
        serializer_route_3 = RouteListSerializer(route_3)

        res = self.client.get(ROUTE_URL, data={"sources": f"{airport_1.id}, {airport_2.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)
        self.assertIn(serializer_route_1.data, res.data["results"])
        self.assertIn(serializer_route_2.data, res.data["results"])
        self.assertNotIn(serializer_route_3.data, res.data["results"])

    def test_filter_route_by_destination(self):
        country = sample_country()

        city_1 = sample_city(name="Test City 1", country=country)
        city_2 = sample_city(name="Test City 2", country=country)
        city_3 = sample_city(name="Test City 3", country=country)

        airport_1 = sample_airport(name="Test Airport 1", city=city_1, code="TTT")
        airport_2 = sample_airport(name="Test Airport 2", city=city_2, code="EEE")
        airport_3 = sample_airport(name="Test Airport 3", city=city_3, code="SSS")

        route_1 = sample_route(source=airport_3, destination=airport_1)
        route_2 = sample_route(source=airport_1, destination=airport_2)
        route_3 = sample_route(source=airport_2, destination=airport_3)

        serializer_route_1 = RouteListSerializer(route_1)
        serializer_route_2 = RouteListSerializer(route_2)
        serializer_route_3 = RouteListSerializer(route_3)

        res = self.client.get(ROUTE_URL, data={"destinations": f"{airport_1.id}, {airport_2.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)
        self.assertIn(serializer_route_1.data, res.data["results"])
        self.assertIn(serializer_route_2.data, res.data["results"])
        self.assertNotIn(serializer_route_3.data, res.data["results"])

    def test_filter_route_by_source_code(self):
        country = sample_country()

        city_1 = sample_city(name="Test City 1", country=country)
        city_2 = sample_city(name="Test City 2", country=country)
        city_3 = sample_city(name="Test City 3", country=country)

        airport_1 = sample_airport(name="Test Airport 1", city=city_1, code="TTT")
        airport_2 = sample_airport(name="Test Airport 2", city=city_2, code="EEE")
        airport_3 = sample_airport(name="Test Airport 3", city=city_3, code="SSS")

        route_1 = sample_route(source=airport_1, destination=airport_2)
        route_2 = sample_route(source=airport_2, destination=airport_3)
        route_3 = sample_route(source=airport_3, destination=airport_1)

        serializer_route_1 = RouteListSerializer(route_1)
        serializer_route_2 = RouteListSerializer(route_2)
        serializer_route_3 = RouteListSerializer(route_3)

        res = self.client.get(ROUTE_URL, data={"source_codes": f"{airport_1.code}, {airport_2.code}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)
        self.assertIn(serializer_route_1.data, res.data["results"])
        self.assertIn(serializer_route_2.data, res.data["results"])
        self.assertNotIn(serializer_route_3.data, res.data["results"])

    def test_filter_route_by_destination_code(self):
        country = sample_country()

        city_1 = sample_city(name="Test City 1", country=country)
        city_2 = sample_city(name="Test City 2", country=country)
        city_3 = sample_city(name="Test City 3", country=country)

        airport_1 = sample_airport(name="Test Airport 1", city=city_1, code="TTT")
        airport_2 = sample_airport(name="Test Airport 2", city=city_2, code="EEE")
        airport_3 = sample_airport(name="Test Airport 3", city=city_3, code="SSS")

        route_1 = sample_route(source=airport_3, destination=airport_1)
        route_2 = sample_route(source=airport_1, destination=airport_2)
        route_3 = sample_route(source=airport_2, destination=airport_3)

        serializer_route_1 = RouteListSerializer(route_1)
        serializer_route_2 = RouteListSerializer(route_2)
        serializer_route_3 = RouteListSerializer(route_3)

        res = self.client.get(ROUTE_URL, data={"destination_codes": f"{airport_1.code}, {airport_2.code}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)
        self.assertIn(serializer_route_1.data, res.data["results"])
        self.assertIn(serializer_route_2.data, res.data["results"])
        self.assertNotIn(serializer_route_3.data, res.data["results"])

    def test_retrieve_route_detail(self):
        route = sample_route()
        url = detail_url("route", route.id)
        serializer = RouteDetailSerializer(route)

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_forbidden_if_not_staff(self):
        country = sample_country()

        city_1 = sample_city(name="Test City 1", country=country)
        city_2 = sample_city(name="Test City 2", country=country)

        airport_1 = sample_airport(name="Test Airport 1", city=city_1, code="TTT")
        airport_2 = sample_airport(name="Test Airport 2", city=city_2, code="EEE")

        payload = {
            "source": airport_1.id,
            "destination": airport_2.id,
            "distance": 1000,
        }
        res = self.client.post(ROUTE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_forbidden_if_not_staff(self):
        route = sample_route()
        url = detail_url("route", route.id)
        payload = {
            "distance":  2000,
        }
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_forbidden_if_not_staff(self):
        route = sample_route()
        url = detail_url("route", route.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminRouteApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com",
            password="testpassword",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_allowed_if_staff(self):
        country = sample_country()

        city_1 = sample_city(name="Test City 1", country=country)
        city_2 = sample_city(name="Test City 2", country=country)

        airport_1 = sample_airport(name="Test Airport 1", city=city_1, code="TTT")
        airport_2 = sample_airport(name="Test Airport 2", city=city_2, code="EEE")

        payload = {
            "source": airport_1.id,
            "destination": airport_2.id,
            "distance": 1000,
        }
        res = self.client.post(ROUTE_URL, payload)
        route = Route.objects.get(id=res.data["id"])
        serializer = RouteSerializer(route)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data, serializer.data)

    def test_update_allowed_if_staff(self):
        route = sample_route()
        url = detail_url("route", route.id)
        payload = {
            "distance": 2000,
        }
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["distance"], payload["distance"])

    def test_delete_allowed_if_staff(self):
        route = sample_route()
        url = detail_url("route", route.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_create_with_bad_input_source(self):
        country = sample_country()

        city_2 = sample_city(name="Test City 2", country=country)
        airport_2 = sample_airport(name="Test Airport 2", city=city_2, code="EEE")

        payload = {
            "source": 999999,
            "destination": airport_2.id,
            "distance": 1000,
        }
        res = self.client.post(ROUTE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_bad_input_distance(self):
        country = sample_country()

        city_1 = sample_city(name="Test City 1", country=country)
        city_2 = sample_city(name="Test City 2", country=country)

        airport_1 = sample_airport(name="Test Airport 1", city=city_1, code="TTT")
        airport_2 = sample_airport(name="Test Airport 2", city=city_2, code="EEE")

        payload = {
            "source": airport_1.id,
            "destination": airport_2.id,
            "distance": 0,
        }
        res = self.client.post(ROUTE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
