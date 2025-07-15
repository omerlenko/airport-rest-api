import re
import zoneinfo
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Country(models.Model):
    name = models.CharField(max_length=100)
    iso_code = models.CharField(max_length=2, unique=True)

    class Meta:
        verbose_name_plural = "countries"

    def clean(self):
        if len(self.iso_code.strip()) != 2 or not self.iso_code.isalpha():
            raise ValidationError("ISO code must be exactly 2 alphabetic characters.")

    def save(self, *args, **kwargs):
        self.full_clean()
        self.name = self.name.capitalize().strip()
        self.iso_code = self.iso_code.upper().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.iso_code})"


class City(models.Model):
    name = models.CharField(max_length=100)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="cities")
    timezone = models.CharField(max_length=100)

    class Meta:
        unique_together = ("name", "country")
        verbose_name_plural = "cities"

    def clean(self):
        if self.timezone.strip() not in zoneinfo.available_timezones():
            raise ValidationError("Timezone must be a valid IANA string, e.g. 'America/New_York'.")

    def save(self, *args, **kwargs):
        self.full_clean()
        self.name = self.name.capitalize().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}, {self.country}"


class Airport(models.Model):
    name = models.CharField(max_length=100)
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="airports")
    code = models.CharField(max_length=3, unique=True)

    @property
    def timezone(self):
        if self.city and self.city.timezone:
            return self.city.timezone

        raise AttributeError("City or timezone wasn't found.")

    def clean(self):
        if not self.city:
            raise ValidationError("Airport must have a city.")
        if not self.city.timezone:
            raise ValidationError("Associated city must have a timezone.")
        if len(self.code.strip()) != 3:
            raise ValidationError("Airport code must be exactly 3 characters long.")

    def save(self, *args, **kwargs):
        self.full_clean()
        self.code = self.code.upper().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} Airport ({self.code}) at {self.city.name}"


class Route(models.Model):
    source = models.ForeignKey(Airport, on_delete=models.CASCADE, related_name="source_routes")
    destination = models.ForeignKey(Airport, on_delete=models.CASCADE, related_name="destination_routes")
    distance = models.IntegerField()

    def clean(self):
        if self.source == self.destination:
            raise ValidationError("Source and destination cannot be same.")
        if self.distance <= 0:
            raise ValidationError("Route distance must be greater than 0 km.")

    def __str__(self):
        return f"{self.source} - {self.destination}, {self.distance} km"


class CrewMember(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class AirplaneType(models.Model):
    manufacturer = models.CharField(max_length=100)
    model = models.CharField(max_length=100)


    class Meta:
        unique_together = ("manufacturer", "model")

    def __str__(self):
        return f"{self.manufacturer} {self.model}"


class Airplane(models.Model):
    tail_number = models.CharField(max_length=10, unique=True)
    rows = models.IntegerField()
    seats_in_row = models.IntegerField()
    airplane_type = models.ForeignKey(AirplaneType, on_delete=models.CASCADE, related_name="airplanes")

    def clean(self):
        if not re.match(r"^[A-Z]{1,2}-?[A-Z0-9]{2,5}$", self.tail_number.strip()):
            raise ValidationError("Tail number must be a valid registration format, like 'SP-LOT' or 'N12345'.")
        if self.rows <= 0 or self.seats_in_row <= 0:
            raise ValidationError("Rows and seats must be greater than 0.")

    def save(self, *args, **kwargs):
        self.full_clean()
        self.tail_number = self.tail_number.upper().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.airplane_type} ({self.tail_number})"


class Flight(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        DELAYED = "delayed", "Delayed"
        BOARDING = "boarding", "Boarding"
        IN_AIR = "in_air", "In Air"
        LANDED = "landed", "Landed"
        CANCELED = "canceled", "Canceled"

    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name="flights")
    airplane = models.ForeignKey(Airplane, on_delete=models.CASCADE, related_name="flights")
    crew_members = models.ManyToManyField(CrewMember, related_name="flights")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()

    def clean(self):
        airplane_flights = self.airplane.flights.exclude(pk=self.pk)
        for flight in airplane_flights:
            if flight.departure_time <= self.arrival_time and flight.arrival_time >= self.departure_time:
                raise ValidationError("Cannot add flight, there's overlap in schedules for this airplane.")

        for member in self.crew_members.all():
            member_flights = member.flights.exclude(pk=self.pk)
            for flight in member_flights:
                if flight.departure_time <= self.arrival_time and flight.arrival_time >= self.departure_time:
                    raise ValidationError(f"Cannot add flight, crew member {member} has a conflicting flight.")

        if self.arrival_time <= self.departure_time:
            raise ValidationError("Arrival time cannot be sooner than departure time.")

    def __str__(self):
        return f"{self.airplane}, {self.route}. Departing at {self.departure_time}, arriving at {self.arrival_time}"


class SeatClass(models.Model):
    name = models.CharField(max_length=100, unique=True)
    priority = models.IntegerField(default=0, unique=True)
    multiplier = models.DecimalField(max_digits=3, decimal_places=2, default=1.00)

    class Meta:
        ordering = ["priority"]
        verbose_name_plural = "seat classes"

    def clean(self):
        if self.priority < 0:
            raise ValidationError("Priority can not be negative.")
        if self.multiplier < Decimal("1.00"):
            raise ValidationError("The seat price multiplier can not be less than 1.00.")

    def save(self, *args, **kwargs):
        self.full_clean()
        self.name = self.name.capitalize().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Order(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order placed by {self.user} at {self.created_at}"


class Ticket(models.Model):
    row = models.IntegerField()
    seat = models.IntegerField()
    seat_class = models.ForeignKey(SeatClass, on_delete=models.CASCADE, related_name="tickets")
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name="tickets")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="tickets")
    price = models.DecimalField(max_digits=7, decimal_places=2)

    class Meta:
        unique_together = ("flight", "row", "seat")

    @staticmethod
    def get_price(flight: Flight, seat_class: SeatClass) -> Decimal:
        base_price = Decimal("0.1")
        distance = round(flight.route.distance)
        seat_class_mult = seat_class.multiplier
        return Decimal(base_price * distance * seat_class_mult).quantize(Decimal("0.01"))

    def clean(self):
        num_rows = self.flight.airplane.rows
        num_seats = self.flight.airplane.seats_in_row
        if self.row <= 0 or self.seat <= 0:
            raise ValidationError("Seat or Row number can not be 0 or negative.")
        if self.row > num_rows or self.seat > num_seats:
            raise ValidationError(f"Seat {self.row}-{self.seat} exceeds available layout: {num_rows} rows, {num_seats} seats per row.")

    def save(self, *args, **kwargs):
        self.full_clean()
        self.price = self.get_price(self.flight, self.seat_class)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Ticket for {self.flight} Seat {self.row}-{self.seat}"
