import os
from datetime import datetime, timedelta, timezone as dt_timezone

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from airport.models import (
    Country,
    City,
    Airport,
    Route,
    AirplaneType,
    Airplane,
    CrewMember,
    Flight,
    Order,
    Ticket,
)


class Command(BaseCommand):
    help = "Seed demo data (admin + demo user + flights + orders/tickets). Safe to re-run."

    def handle(self, *args, **options):

        if not settings.DEBUG:
            self.stdout.write(self.style.ERROR("Refusing to seed when DEBUG=False"))
            return

        admin_email = os.environ.get("DJANGO_ADMIN_EMAIL", "admin@demo.com")
        admin_password = os.environ.get("DJANGO_ADMIN_PASSWORD", "admin12345")
        demo_email = os.environ.get("DJANGO_DEMO_EMAIL", "demo@demo.com")
        demo_password = os.environ.get("DJANGO_DEMO_PASSWORD", "demo12345")

        user = get_user_model()

        with transaction.atomic():
            # --- Users ---
            admin, _ = user.objects.update_or_create(
                email=admin_email,
                defaults={"is_staff": True, "is_superuser": False},
            )
            admin.set_password(admin_password)
            admin.save()

            demo_user, _ = user.objects.update_or_create(
                email=demo_email,
                defaults={"is_staff": False, "is_superuser": False},
            )
            demo_user.set_password(demo_password)
            demo_user.save()

            # --- Countries / Cities / Airports ---
            pl, _ = Country.objects.get_or_create(
                iso_code="PL", defaults={"name": "Poland"}
            )
            uk, _ = Country.objects.get_or_create(
                iso_code="GB", defaults={"name": "United Kingdom"}
            )
            us, _ = Country.objects.get_or_create(
                iso_code="US", defaults={"name": "United States"}
            )

            waw_city, _ = City.objects.get_or_create(
                name="Warsaw",
                country=pl,
                defaults={"timezone": "Europe/Warsaw"},
            )
            lon_city, _ = City.objects.get_or_create(
                name="London",
                country=uk,
                defaults={"timezone": "Europe/London"},
            )
            nyc_city, _ = City.objects.get_or_create(
                name="New York",
                country=us,
                defaults={"timezone": "America/New_York"},
            )

            waw, _ = Airport.objects.get_or_create(
                code="WAW",
                defaults={"name": "Warsaw Chopin", "city": waw_city},
            )
            lhr, _ = Airport.objects.get_or_create(
                code="LHR",
                defaults={"name": "Heathrow", "city": lon_city},
            )
            jfk, _ = Airport.objects.get_or_create(
                code="JFK",
                defaults={"name": "John F. Kennedy", "city": nyc_city},
            )

            # --- Routes ---
            route_waw_lhr, _ = Route.objects.get_or_create(
                source=waw, destination=lhr, defaults={"distance": 1440}
            )
            route_lhr_jfk, _ = Route.objects.get_or_create(
                source=lhr, destination=jfk, defaults={"distance": 5540}
            )

            # --- AirplaneType / Airplane (seats auto-generated) ---
            a320, _ = AirplaneType.objects.get_or_create(
                manufacturer="Airbus", model="A320"
            )

            airplane, _ = Airplane.objects.get_or_create(
                tail_number="SP-LOT",
                defaults={"rows": 20, "seats_in_row": 6, "airplane_type": a320},
            )

            # --- Crew ---
            cm1, _ = CrewMember.objects.get_or_create(first_name="John", last_name="Smith")
            cm2, _ = CrewMember.objects.get_or_create(first_name="Anna", last_name="Kowalski")
            cm3, _ = CrewMember.objects.get_or_create(first_name="Mark", last_name="Brown")

            # --- Flights ---
            base = datetime(2030, 1, 10, 10, 0, tzinfo=dt_timezone.utc)

            dep1 = base
            arr1 = dep1 + timedelta(hours=2, minutes=20)

            dep2 = arr1 + timedelta(hours=3)
            arr2 = dep2 + timedelta(hours=8, minutes=50)

            flight1, _ = Flight.objects.get_or_create(
                route=route_waw_lhr,
                airplane=airplane,
                departure_time=dep1,
                arrival_time=arr1,
                defaults={"status": Flight.Status.SCHEDULED},
            )
            flight1.crew_members.set([cm1, cm2])

            flight2, _ = Flight.objects.get_or_create(
                route=route_lhr_jfk,
                airplane=airplane,
                departure_time=dep2,
                arrival_time=arr2,
                defaults={"status": Flight.Status.SCHEDULED},
            )
            flight2.crew_members.set([cm2, cm3])

            # --- Order + tickets for demo user ---
            demo_order = (
                    Order.objects.filter(user=demo_user).order_by("created_at").first()
                    or Order.objects.create(user=demo_user)
            )

            seats = airplane.seats.order_by("row", "seat_number")[:2]

            for seat in seats:
                Ticket.objects.update_or_create(
                    flight=flight1,
                    seat=seat,
                    defaults={"order": demo_order},
                )

        self.stdout.write(self.style.SUCCESS("✅ Demo data seeded.\n"))
        self.stdout.write("Admin:")
        self.stdout.write(f"  email: {admin_email}")
        self.stdout.write(f"  password: {admin_password}\n")
        self.stdout.write("Demo user:")
        self.stdout.write(f"  email: {demo_email}")
        self.stdout.write(f"  password: {demo_password}\n")
        self.stdout.write("Tip: obtain JWT at /api/user/token/ and use Authorization: Bearer <access>")
