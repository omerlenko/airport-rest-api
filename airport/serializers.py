import re
import zoneinfo

from django.db import transaction
from django.utils.timezone import now
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from airport.models import Country, City, Airport, Route, CrewMember, AirplaneType, Airplane, Flight, SeatClass, Order, \
    Ticket


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
            raise serializers.ValidationError("Timezone must be a valid IANA string, e.g. 'America/New_York'.")
        return value


class CityListSerializer(CitySerializer):
    country = serializers.SlugRelatedField(many=False, read_only=True, slug_field="name")


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
            raise serializers.ValidationError("Airport code must be exactly 3 letters. (e.g., 'JFK')")

        qs = Airport.objects.filter(code__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Airport code already exists.")
        return value


class AirportListSerializer(AirportSerializer):
    city = serializers.SlugRelatedField(many=False, read_only=True, slug_field="name")


class AirportDetailSerializer(AirportSerializer):
    city = CityListSerializer(many=False, read_only=True)


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ("id", "source", "destination", "distance")

    def validate_distance(self, value):
        if value <= 0:
            raise serializers.ValidationError("Route distance must be greater than 0.")
        return value

    def validate(self, attrs):
        source = attrs.get("source", getattr(self.instance, "source", None))
        destination = attrs.get("destination", getattr(self.instance, "destination", None))
        if source is None or destination is None:
            return attrs

        if source == destination:
            raise serializers.ValidationError("Source and destination airports must be different.")

        qs = Route.objects.filter(source=source, destination=destination)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Route already exists.")
        return attrs

class RouteListSerializer(RouteSerializer):
    source = serializers.SlugRelatedField(many=False, read_only=True, slug_field="code")
    destination = serializers.SlugRelatedField(many=False, read_only=True, slug_field="code")


class RouteDetailSerializer(RouteSerializer):
    source = AirportDetailSerializer(many=False, read_only=True)
    destination = AirportDetailSerializer(many=False, read_only=True)


class CrewMemberSerializer (serializers.ModelSerializer):
    class Meta:
        model = CrewMember
        fields = ("id", "first_name", "last_name", "full_name")


class AirplaneTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AirplaneType
        fields = ("id", "manufacturer", "model")

    def validate(self, attrs):
        manufacturer = attrs.get("manufacturer", getattr(self.instance, "manufacturer", None))
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
            raise serializers.ValidationError("This manufacturer and model combo already exists.")
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
            raise serializers.ValidationError("Tail number must be a valid registration format, like 'SP-LOT' or 'N12345'.")

        qs = Airplane.objects.filter(tail_number__iexact=tail_number)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This tail number already exists.")

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
        fields = ("id", "route", "airplane", "crew_members", "status", "departure_time", "arrival_time")

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
            self.fields["airplane"].queryset = Airplane.objects.select_related("airplane_type")

    def validate(self, attrs):
        airplane = attrs.get("airplane", getattr(self.instance, "airplane", None))
        crew_members = attrs.get("crew_members", None)
        if crew_members is None and self.instance:
            crew_members = self.instance.crew_members.all()
        departure_time = attrs.get("departure_time", getattr(self.instance, "departure_time", None))
        arrival_time = attrs.get("arrival_time", getattr(self.instance, "arrival_time", None))

        if departure_time and arrival_time:
            if arrival_time <= departure_time:
                raise serializers.ValidationError("Arrival time cannot be sooner than departure time.")
        else:
            return attrs

        if airplane:
            airplane_flights = airplane.flights.all()
            if self.instance:
                airplane_flights = airplane_flights.exclude(pk=self.instance.pk)
            airplane_flights = airplane_flights.filter(arrival_time__gte=departure_time, departure_time__lte=arrival_time)
            if airplane_flights.exists():
                raise serializers.ValidationError(f"Airplane {airplane} has another flight during this time.")

        if crew_members:
            for crew_member in crew_members:
                crew_member_flights = crew_member.flights.all()
                if self.instance:
                    crew_member_flights = crew_member_flights.exclude(pk=self.instance.pk)
                crew_member_flights = crew_member_flights.filter(arrival_time__gte=departure_time, departure_time__lte=arrival_time)
                if crew_member_flights.exists():
                    raise serializers.ValidationError(
                        f"Crew member {crew_member.full_name} has another flight during this time.")

        return attrs


class FlightListSerializer(FlightSerializer):
    route = RouteListSerializer(many=False, read_only=True)
    airplane = AirplaneListSerializer(many=False, read_only=True)
    crew_members = serializers.SlugRelatedField(many=True, read_only=True, slug_field="full_name")
    status = serializers.CharField(source="get_status_display", read_only=True)
    tickets_available = serializers.IntegerField(read_only=True)

    class Meta:
        model = Flight
        fields = ("id", "route", "airplane", "crew_members", "status", "departure_time", "arrival_time", "tickets_available")


class FlightDetailSerializer(FlightListSerializer):
    route = RouteDetailSerializer(many=False, read_only=True)
    airplane = AirplaneDetailSerializer(many=False, read_only=True)
    crew_members = CrewMemberSerializer(many=True, read_only=True)
    taken_seats = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Flight
        fields = ("id", "route", "airplane", "crew_members", "status", "departure_time", "arrival_time", "taken_seats")

    def get_taken_seats(self, obj) -> list[dict]:
        return [
            {
                "row": ticket.row,
                "seat": ticket.seat
            }
            for ticket in obj.tickets.all()
        ]


class FlightMiniSerializer(FlightSerializer):
    source = serializers.SlugRelatedField(many=False, read_only=True, source="route", slug_field="source.code")
    destination = serializers.SlugRelatedField(many=False, read_only=True, source="route", slug_field="destination.code")
    departure_time = serializers.DateTimeField()
    arrival_time = serializers.DateTimeField()

    class Meta:
        model = Flight
        fields = ("id", "source", "destination", "departure_time", "arrival_time")


class FlightMiniDetailSerializer(FlightMiniSerializer):
    distance_km = serializers.SerializerMethodField()
    status = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Flight
        fields = ("id", "route", "airplane", "distance_km", "status", "departure_time", "arrival_time")

    def get_distance_km(self, obj) -> int:
        return obj.route.distance


class SeatClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeatClass
        fields = ("id", "name", "priority", "multiplier")


class SeatClassMiniSerializer(SeatClassSerializer):
    class Meta:
        model = SeatClass
        fields = ("id", "name")

class TicketSerializer(serializers.ModelSerializer):
    row = serializers.IntegerField(min_value=1)
    seat = serializers.IntegerField(min_value=1)
    price = serializers.DecimalField(max_digits=7, decimal_places=2, read_only=True)

    class Meta:
        model = Ticket
        fields = ("id", "row", "seat", "seat_class", "flight", "price")
        validators = [
            UniqueTogetherValidator(
                queryset=Ticket.objects.all(),
                fields=["row", "seat", "flight"],
                message="This ticket has already been taken. Please choose from available tickets."
            )
        ]

    def validate(self, attrs):
        seat = attrs.get("seat", getattr(self.instance, "seat", None))
        row = attrs.get("row", getattr(self.instance, "row", None))
        flight = attrs.get("flight", getattr(self.instance, "flight", None))

        if seat and row and flight:
            seats_in_row = flight.airplane.seats_in_row
            rows = flight.airplane.rows

            if seat > seats_in_row or row > rows:
                raise serializers.ValidationError(f"Seat and row must be in available range. Seats [1 - {seats_in_row}], Rows [1 - {rows}]")

            if flight.status != Flight.Status.SCHEDULED:
                raise serializers.ValidationError(f"You cannot book this flight because its status is [{flight.get_status_display()}]")

            if flight.departure_time <= now():
                raise serializers.ValidationError("You can only book future flights.")

        return attrs


class TicketListSerializer(TicketSerializer):
    seat_class = serializers.SlugRelatedField(read_only=True, many=False, slug_field="name")
    flight = FlightMiniSerializer(read_only=True)


class TicketDetailSerializer(TicketListSerializer):
    seat_class = SeatClassMiniSerializer(many=False, read_only=True)
    flight = FlightMiniDetailSerializer(many=False, read_only=True)


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, read_only=False, allow_empty=False)

    class Meta:
        model = Order
        fields = ("id", "created_at", "tickets")

    def create(self, validated_data):
        with transaction.atomic():
            user = self.context.get("request").user
            tickets_data = validated_data.pop("tickets")
            order = Order.objects.create(user=user, **validated_data)
            for ticket_data in tickets_data:
                Ticket.objects.create(order=order, **ticket_data)
            return order


class OrderListSerializer(OrderSerializer):
    user = serializers.SlugRelatedField(many=False, read_only=True, slug_field="email")
    total_price = serializers.DecimalField(read_only=True, max_digits=7, decimal_places=2, default=0)

    class Meta:
        model = Order
        fields = ("id", "created_at", "user", "total_price")


class OrderDetailSerializer(OrderListSerializer):
    tickets = TicketDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ("id", "created_at", "user", "tickets", "total_price")
