import re
import zoneinfo
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils.timezone import now
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

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


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ("id", "name", "iso_code")


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ("id", "name", "country", "timezone")

    def validate_timezone(self, value):
        if value.strip() not in zoneinfo.available_timezones():
            raise serializers.ValidationError(
                "Timezone must be a valid IANA string, "
                "e.g. 'America/New_York'."
            )
        return value


class CityListSerializer(CitySerializer):
    country = serializers.SlugRelatedField(
        many=False, read_only=True, slug_field="name"
    )


class CityDetailSerializer(CitySerializer):
    country = CountrySerializer()


class AirportSerializer(serializers.ModelSerializer):
    timezone = serializers.CharField(source="city.timezone", read_only=True)

    class Meta:
        model = Airport
        fields = ("id", "name", "city", "code", "timezone")

    def validate_code(self, value):
        value = value.strip().upper()
        if len(value) != 3 or not value.isalpha():
            raise serializers.ValidationError(
                "Airport code must be exactly 3 letters. (e.g., 'JFK')"
            )

        qs = Airport.objects.filter(code__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Airport code already exists.")
        return value


class AirportListSerializer(AirportSerializer):
    city = serializers.SlugRelatedField(
        many=False, read_only=True, slug_field="name"
    )


class AirportDetailSerializer(AirportSerializer):
    city = CityListSerializer(many=False, read_only=True)


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ("id", "source", "destination", "distance")

    def validate_distance(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Route distance must be greater than 0."
            )
        return value

    def validate(self, attrs):
        source = attrs.get("source", getattr(self.instance, "source", None))
        destination = attrs.get(
            "destination", getattr(self.instance, "destination", None)
        )
        if source is None or destination is None:
            return attrs

        if source == destination:
            raise serializers.ValidationError(
                "Source and destination airports must be different."
            )

        qs = Route.objects.filter(source=source, destination=destination)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Route already exists.")
        return attrs


class RouteListSerializer(RouteSerializer):
    source = serializers.SlugRelatedField(
        many=False, read_only=True, slug_field="code"
    )
    destination = serializers.SlugRelatedField(
        many=False, read_only=True, slug_field="code"
    )


class RouteDetailSerializer(RouteSerializer):
    source = AirportDetailSerializer(many=False, read_only=True)
    destination = AirportDetailSerializer(many=False, read_only=True)


class CrewMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrewMember
        fields = ("id", "first_name", "last_name", "full_name")


class AirplaneTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AirplaneType
        fields = ("id", "manufacturer", "model")

    def validate(self, attrs):
        manufacturer = attrs.get(
            "manufacturer", getattr(self.instance, "manufacturer", None)
        )
        model = attrs.get("model", getattr(self.instance, "model", None))
        if not manufacturer and not model:
            return attrs

        qs = AirplaneType.objects.filter(
            manufacturer__iexact=manufacturer.strip(),
            model__iexact=model.strip()
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "This manufacturer and model combo already exists."
            )
        return attrs


class AirplaneSerializer(serializers.ModelSerializer):
    rows = serializers.IntegerField(min_value=1)
    seats_in_row = serializers.IntegerField(min_value=1)

    class Meta:
        model = Airplane
        fields = ("id", "airplane_type", "tail_number", "rows", "seats_in_row")

    def validate_tail_number(self, value):
        tail_number = value.strip().upper()
        if not re.match(r"^[A-Z]{1,2}-?[A-Z0-9]{2,5}$", tail_number):
            raise serializers.ValidationError(
                "Tail number must be a valid registration format, "
                "like 'SP-LOT' or 'N12345'."
            )

        qs = Airplane.objects.filter(tail_number__iexact=tail_number)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "This tail number already exists."
            )

        return tail_number


class AirplaneListSerializer(AirplaneSerializer):
    airplane_type = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Airplane
        fields = ("id", "airplane_type", "tail_number")

    def get_airplane_type(self, obj):
        return obj.airplane_type.manufacturer + " " + obj.airplane_type.model


class AirplaneDetailSerializer(AirplaneSerializer):
    airplane_type = AirplaneTypeSerializer(many=False, read_only=True)


class FlightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flight
        fields = (
            "id",
            "route",
            "airplane",
            "crew_members",
            "status",
            "departure_time",
            "arrival_time",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "route" in self.fields:
            self.fields["route"].queryset = Route.objects.select_related(
                "source",
                "source__city",
                "source__city__country",
                "destination",
                "destination__city",
                "destination__city__country",
            )
        if "airplane" in self.fields:
            self.fields["airplane"].queryset = Airplane.objects.select_related(
                "airplane_type"
            )

    def validate(self, attrs):
        airplane = attrs.get(
            "airplane", getattr(self.instance, "airplane", None)
        )
        crew_members = attrs.get("crew_members", None)
        if crew_members is None and self.instance:
            crew_members = self.instance.crew_members.all()
        departure_time = attrs.get(
            "departure_time", getattr(self.instance, "departure_time", None)
        )
        arrival_time = attrs.get(
            "arrival_time", getattr(self.instance, "arrival_time", None)
        )

        if departure_time and arrival_time:
            if arrival_time <= departure_time:
                raise serializers.ValidationError(
                    "Arrival time cannot be sooner than departure time."
                )
        else:
            return attrs

        if airplane:
            airplane_flights = airplane.flights.all()
            if self.instance:
                airplane_flights = airplane_flights.exclude(
                    pk=self.instance.pk
                )
            airplane_flights = airplane_flights.filter(
                arrival_time__gte=departure_time,
                departure_time__lte=arrival_time
            )
            if airplane_flights.exists():
                raise serializers.ValidationError(
                    f"Airplane {airplane} has another flight during this time."
                )

        if crew_members:
            for crew_member in crew_members:
                crew_member_flights = crew_member.flights.all()
                if self.instance:
                    crew_member_flights = crew_member_flights.exclude(
                        pk=self.instance.pk
                    )
                crew_member_flights = crew_member_flights.filter(
                    arrival_time__gte=departure_time,
                    departure_time__lte=arrival_time
                )
                if crew_member_flights.exists():
                    raise serializers.ValidationError(
                        f"Crew member {crew_member.full_name} "
                        f"has another flight during this time."
                    )

        return attrs


class FlightListSerializer(FlightSerializer):
    route = RouteListSerializer(many=False, read_only=True)
    airplane = AirplaneListSerializer(many=False, read_only=True)
    crew_members = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="full_name"
    )
    status = serializers.CharField(source="get_status_display", read_only=True)
    capacity = serializers.IntegerField(read_only=True)
    tickets_available = serializers.IntegerField(read_only=True)

    class Meta:
        model = Flight
        fields = (
            "id",
            "route",
            "airplane",
            "crew_members",
            "status",
            "departure_time",
            "arrival_time",
            "capacity",
            "tickets_available",
        )


class FlightDetailSerializer(FlightListSerializer):
    route = RouteDetailSerializer(many=False, read_only=True)
    airplane = AirplaneDetailSerializer(many=False, read_only=True)
    crew_members = CrewMemberSerializer(many=True, read_only=True)
    taken_seats = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Flight
        fields = (
            "id",
            "route",
            "airplane",
            "crew_members",
            "status",
            "departure_time",
            "arrival_time",
            "capacity",
            "tickets_available",
            "taken_seats",
        )

    @staticmethod
    def get_taken_seats(obj) -> list[dict]:
        return [
            {"row": ticket.seat.row, "seat": ticket.seat.seat_number}
            for ticket in obj.tickets.all()
        ]


class FlightMiniSerializer(FlightSerializer):
    source = serializers.SlugRelatedField(
        many=False, read_only=True, source="route", slug_field="source.code"
    )
    destination = serializers.SlugRelatedField(
        many=False,
        read_only=True,
        source="route",
        slug_field="destination.code"
    )
    departure_time = serializers.DateTimeField()
    arrival_time = serializers.DateTimeField()

    class Meta:
        model = Flight
        fields = (
            "id", "source", "destination", "departure_time", "arrival_time"
        )


class FlightMiniDetailSerializer(FlightMiniSerializer):
    distance_km = serializers.SerializerMethodField()
    status = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Flight
        fields = (
            "id",
            "source",
            "destination",
            "airplane",
            "distance_km",
            "status",
            "departure_time",
            "arrival_time",
        )

    def get_distance_km(self, obj) -> int:
        return obj.route.distance


class SeatClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeatClass
        fields = ("id", "name", "priority", "multiplier")

    def validate(self, attrs):
        priority = attrs.get(
            "priority", getattr(self.instance, "priority", None)
        )
        multiplier = attrs.get(
            "multiplier", getattr(self.instance, "multiplier", None)
        )

        if not priority and not multiplier:
            return attrs

        if priority < 0:
            raise serializers.ValidationError(
                "Priority can not be a negative integer."
            )
        if multiplier < Decimal("1.00"):
            raise serializers.ValidationError(
                "The seat price multiplier can not be less than 1.00."
            )

        return attrs


class SeatClassMiniSerializer(SeatClassSerializer):
    class Meta:
        model = SeatClass
        fields = ("id", "name")


class SeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seat
        fields = ("id", "airplane", "row", "seat_number", "seat_class")

    def validate(self, attrs):
        airplane = attrs.get(
            "airplane", getattr(self.instance, "airplane", None)
        )
        row = attrs.get("row", getattr(self.instance, "row", None))
        seat_number = attrs.get(
            "seat_number", getattr(self.instance, "seat_number", None)
        )

        if airplane is None or row is None or seat_number is None:
            return attrs

        if row <= 0 or row > airplane.rows:
            raise ValidationError(
                f"The row for this seat must be in range 1-{airplane.rows} "
            )
        if seat_number <= 0 or seat_number > airplane.seats_in_row:
            raise ValidationError(
                f"The seat number for this seat "
                f"must be in range 1-{airplane.seats_in_row}"
            )

        return attrs


class SeatListSerializer(SeatSerializer):
    airplane = AirplaneListSerializer(many=False, read_only=True)
    seat_class = serializers.SlugRelatedField(
        many=False, read_only=True, slug_field="name"
    )


class SeatDetailSerializer(SeatListSerializer):
    seat_class = SeatClassMiniSerializer(many=False, read_only=True)


class SeatMiniSerializer(SeatListSerializer):
    class Meta:
        model = Seat
        fields = ("id", "row", "seat_number", "seat_class")


class TicketSerializer(serializers.ModelSerializer):
    order = serializers.PrimaryKeyRelatedField(read_only=True)
    price = serializers.DecimalField(
        max_digits=7, decimal_places=2, read_only=True
    )

    class Meta:
        model = Ticket
        fields = ("id", "flight", "seat", "order", "price")
        validators = [
            UniqueTogetherValidator(
                queryset=Ticket.objects.all(),
                fields=["seat", "flight"],
                message="This ticket has already been taken. "
                        "Please choose from available tickets.",
            )
        ]

    def validate(self, attrs):
        flight = attrs.get("flight", getattr(self.instance, "flight", None))
        seat = attrs.get("seat", getattr(self.instance, "seat", None))

        if flight and seat:
            if flight.airplane != seat.airplane:
                raise serializers.ValidationError(
                    "Seat must be appropriate for this flight."
                )

            if flight.status != Flight.Status.SCHEDULED:
                raise serializers.ValidationError(
                    f"You cannot book this flight because "
                    f"its status is [{flight.get_status_display()}]"
                )

            if flight.departure_time <= now():
                raise serializers.ValidationError(
                    "You can only book future flights."
                )

        return attrs


class TicketListSerializer(TicketSerializer):
    seat = SeatMiniSerializer(many=False, read_only=True)
    flight = FlightMiniSerializer(read_only=True)


class TicketDetailSerializer(TicketListSerializer):
    seat = SeatDetailSerializer(many=False, read_only=True)
    flight = FlightMiniDetailSerializer(many=False, read_only=True)


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, read_only=False, allow_empty=False)

    class Meta:
        model = Order
        fields = ("id", "created_at", "tickets")

    def validate_tickets(self, tickets):
        ticket_pairs = set()

        for ticket in tickets:
            pair = (ticket["flight"].id, ticket["seat"].id)

            if pair in ticket_pairs:
                raise serializers.ValidationError(
                    "There's a duplicate seat "
                    "for the same flight in this request."
                )
            else:
                ticket_pairs.add(pair)

        condition = Q()
        for flight, seat in ticket_pairs:
            condition = condition | Q(flight_id=flight, seat_id=seat)

        if Ticket.objects.filter(condition).exists():
            raise serializers.ValidationError(
                "This ticket has already been taken. "
                "Please choose from available tickets."
            )

        return tickets

    def create(self, validated_data):
        with transaction.atomic():
            user = self.context.get("request").user
            tickets_data = validated_data.pop("tickets")
            order = Order.objects.create(user=user, **validated_data)
            for ticket_data in tickets_data:
                try:
                    Ticket.objects.create(order=order, **ticket_data)
                except (ValidationError, IntegrityError):
                    raise serializers.ValidationError(
                        "This ticket has already been taken. "
                        "Please choose from available tickets."
                    )
            return order


class OrderListSerializer(OrderSerializer):
    user = serializers.SlugRelatedField(
        many=False, read_only=True, slug_field="email"
    )
    total_price = serializers.DecimalField(
        read_only=True, max_digits=7, decimal_places=2, default=0
    )

    class Meta:
        model = Order
        fields = ("id", "created_at", "user", "total_price")


class OrderDetailSerializer(OrderListSerializer):
    tickets = TicketDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ("id", "created_at", "user", "tickets", "total_price")
