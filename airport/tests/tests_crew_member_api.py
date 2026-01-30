from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from airport.models import CrewMember
from airport.serializers import CrewMemberSerializer
from airport.tests.utils import detail_url, sample_crew_member

CREW_MEMBER_URL = reverse("airport:crewmember-list")


class UnauthenticatedCrewMemberApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(CREW_MEMBER_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedCrewMemberApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_crew_member_list(self):
        sample_crew_member()
        res = self.client.get(CREW_MEMBER_URL)
        crew_members = CrewMember.objects.all()
        serializer = CrewMemberSerializer(crew_members, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_retrieve_crew_member_detail(self):
        crew_member = sample_crew_member()
        url = detail_url("crewmember", crew_member.id)
        serializer = CrewMemberSerializer(crew_member)

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_forbidden_if_not_staff(self):
        payload = {"first_name": "Test", "last_name": "Crew_Member"}
        res = self.client.post(CREW_MEMBER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_forbidden_if_not_staff(self):
        crew_member = sample_crew_member()
        url = detail_url("crewmember", crew_member.id)
        payload = {
            "first_name": "Update",
        }
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_forbidden_if_not_staff(self):
        crew_member = sample_crew_member()
        url = detail_url("crewmember", crew_member.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminCrewMemberApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com", password="testpassword", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_allowed_if_staff(self):
        payload = {"first_name": "Test", "last_name": "Crew_Member"}
        res = self.client.post(CREW_MEMBER_URL, payload)
        crew_member = CrewMember.objects.get(id=res.data["id"])
        serializer = CrewMemberSerializer(crew_member)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data, serializer.data)

    def test_update_allowed_if_staff(self):
        crew_member = sample_crew_member()
        url = detail_url("crewmember", crew_member.id)
        payload = {
            "first_name": "Update",
        }
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["first_name"], payload["first_name"])

    def test_delete_allowed_if_staff(self):
        crew_member = sample_crew_member()
        url = detail_url("crewmember", crew_member.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_create_with_bad_input_first_name(self):
        payload = {"first_name": "", "last_name": "Crew_Member"}
        res = self.client.post(CREW_MEMBER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
