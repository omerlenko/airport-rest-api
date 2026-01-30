from datetime import UTC, datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.reverse import reverse

from airport.models import (
    Airplane,
    AirplaneType,
    Airport,
    City,
    Country,
    CrewMember,
    Flight,
    Order,
    Route,
    Seat,
    SeatClass,
    Ticket,
)


def detail_url(prefix, instance_id):
    return reverse(f"airport:{prefix}-detail", args=(instance_id,))


def sample_country(**params):
    defaults = {"name": "Test Country", "iso_code": "TC"}
    defaults.update(params)
    return Country.objects.get_or_create(**defaults)[0]


def sample_city(**params):
    defaults = {"name": "Test City", "timezone": "Europe/Warsaw"}

    defaults.update(params)
    if "country" not in params:
        defaults.update(country=sample_country())

    return City.objects.get_or_create(**defaults)[0]


def sample_airport(**params):
    defaults = {"name": "Test Airport", "code": "TSA"}

    defaults.update(params)
    if "city" not in params:
        defaults.update(city=sample_city())

    return Airport.objects.get_or_create(**defaults)[0]


def sample_route(**params):
    defaults = {
        "distance": 1000,
    }

    defaults.update(params)
    if "source" not in params or "destination" not in params:
        country = sample_country()

        if "source" not in params:
            defaults.update(
                source=sample_airport(
                    city=sample_city(name="Test City 1", country=country),
                    code="QQQ",
                )
            )

        if "destination" not in params:
            defaults.update(
                destination=sample_airport(
                    city=sample_city(name="Test City 2", country=country),
                    code="WWW",
                )
            )

    return Route.objects.get_or_create(**defaults)[0]


def sample_crew_member(**params):
    defaults = {"first_name": "Test", "last_name": "Crew_Member"}

    defaults.update(params)

    return CrewMember.objects.get_or_create(**defaults)[0]


def sample_seat_class(**params):
    defaults = {
        "name": "First",
        "priority": 0,
        "multiplier": Decimal("3.00"),
    }
    defaults.update(params)

    priority = defaults.pop("priority")

    seat_class, _ = SeatClass.objects.update_or_create(
        priority=priority,
        defaults=defaults,
    )

    return seat_class


def create_basic_three_seat_classes():
    sample_seat_class(priority=0, name="First", multiplier=Decimal("3.00"))
    sample_seat_class(priority=1, name="Business", multiplier=Decimal("2.00"))
    sample_seat_class(priority=2, name="Economy", multiplier=Decimal("1.00"))


def sample_seat(**params):
    defaults = {
        "row": 1,
        "seat_number": 1,
    }
    defaults.update(params)

    if "airplane" not in params:
        defaults.update(airplane=sample_airplane())
    if "seat_class" not in params:
        defaults.update(seat_class=sample_seat_class())

    return Seat.objects.get_or_create(**defaults)[0]


def sample_airplane_type(**params):
    defaults = {"manufacturer": "Test_Manufacturer", "model": "Test_Model"}

    defaults.update(params)

    return AirplaneType.objects.get_or_create(**defaults)[0]


def sample_airplane(**params):
    create_basic_three_seat_classes()

    defaults = {
        "tail_number": "N12345",
        "rows": 10,
        "seats_in_row": 6,
    }
    defaults.update(params)

    if "airplane_type" not in params:
        defaults.update(airplane_type=sample_airplane_type())

    return Airplane.objects.get_or_create(**defaults)[0]


def sample_flight(crew_members=None, **params):
    if crew_members is None:
        crew_members = [sample_crew_member()]
    elif not isinstance(crew_members, (list, tuple, set)):
        crew_members = [crew_members]

    base_time = datetime(2030, 1, 1, 10, 0, tzinfo=UTC)

    defaults = {
        "status": Flight.Status.SCHEDULED,
        "departure_time": base_time + timedelta(days=1),
        "arrival_time": base_time + timedelta(days=1, hours=2),
    }
    defaults.update(params)

    if "route" not in params:
        defaults.update(route=sample_route())
    if "airplane" not in params:
        defaults.update(airplane=sample_airplane())

    flight = Flight.objects.get_or_create(**defaults)[0]
    flight.crew_members.set(crew_members)

    return flight


def sample_user(**params):
    defaults = {
        "email": "test_user@test.com",
        "password": "test_password",
        "is_staff": False,
    }
    defaults.update(params)

    return get_user_model().objects.create_user(**defaults)


def sample_order(user=None, tickets=None):
    if user is None:
        user = sample_user()

    order = Order.objects.create(user=user)

    if tickets is None:
        sample_ticket(order=order)
    else:
        for ticket_data in tickets:
            sample_ticket(order=order, **ticket_data)

    return order


def sample_ticket(order, **params):
    defaults = {}
    defaults.update(params)

    if "flight" not in params:
        defaults.update(flight=sample_flight())
    if "seat" not in params:
        defaults.update(seat=sample_seat())

    return Ticket.objects.create(order=order, **defaults)
