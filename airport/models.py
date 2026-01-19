import re
import zoneinfo
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class Country(models.Model):
    name = models.CharField(max_length=100)
    iso_code = models.CharField(max_length=2, unique=True)

    class Meta:
        verbose_name_plural = "countries"
        ordering = ["name"]

    def clean(self):
        if len(self.iso_code.strip()) != 2 or not self.iso_code.isalpha():
            raise ValidationError(
                "ISO code must be exactly 2 alphabetic characters."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        self.name = self.name.strip()
        self.iso_code = self.iso_code.upper().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.iso_code})"


class City(models.Model):
    name = models.CharField(max_length=100)
    country = models.ForeignKey(
        Country, on_delete=models.PROTECT, related_name="cities"
    )
    timezone = models.CharField(max_length=100)

    class Meta:
        unique_together = ("name", "country")
        verbose_name_plural = "cities"
        ordering = ["name"]

    def clean(self):
        if self.timezone.strip() not in zoneinfo.available_timezones():
            raise ValidationError(
                "Timezone must be a valid IANA string, "
                "e.g. 'America/New_York'."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        self.name = self.name.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}, {self.country}"


class Airport(models.Model):
    name = models.CharField(max_length=100)
    city = models.ForeignKey(
        City, on_delete=models.PROTECT, related_name="airports"
    )
    code = models.CharField(max_length=3, unique=True)

    class Meta:
        unique_together = ("name", "city")

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
        if len(self.code.strip()) != 3 or not self.code.isalpha():
            raise ValidationError("Airport code must be exactly 3 letters.")

    def save(self, *args, **kwargs):
        self.full_clean()
        self.name = self.name.strip()
        self.code = self.code.upper().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} Airport ({self.code}) at {self.city.name}"


class Route(models.Model):
    source = models.ForeignKey(
        Airport, on_delete=models.PROTECT, related_name="source_routes"
    )
    destination = models.ForeignKey(
        Airport, on_delete=models.PROTECT, related_name="destination_routes"
    )
    distance = models.IntegerField()

    class Meta:
        ordering = ["distance"]

    def clean(self):
        if self.source == self.destination:
            raise ValidationError("Source and destination cannot be same.")
        if self.distance <= 0:
            raise ValidationError("Route distance must be greater than 0 km.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.source} - {self.destination}, {self.distance} km"


class CrewMember(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    class Meta:
        ordering = ["last_name"]

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        self.first_name = self.first_name.capitalize().strip()
        self.last_name = self.last_name.capitalize().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name


class AirplaneType(models.Model):
    manufacturer = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["manufacturer", "model"], name="unique_airplane_type"
            )
        ]

    def save(self, *args, **kwargs):
        self.manufacturer = self.manufacturer.strip()
        self.model = self.model.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.manufacturer} {self.model}"


class Airplane(models.Model):
    tail_number = models.CharField(max_length=10, unique=True)
    rows = models.IntegerField(
        validators=[MinValueValidator(1, message="Rows must be at least 1.")]
    )
    seats_in_row = models.IntegerField(
        validators=[MinValueValidator(
            1, message="Seats per row must be at least 1."
        )]
    )
    airplane_type = models.ForeignKey(
        AirplaneType, on_delete=models.PROTECT, related_name="airplanes"
    )

    def generate_seats(self):
        seat_class = {
            "first": SeatClass.objects.get(priority=0),
            "business": SeatClass.objects.get(priority=1),
            "economy": SeatClass.objects.get(priority=2),
        }

        for row in range(1, self.rows + 1):
            if row <= 4:
                priority = "first"
            elif 5 <= row <= 10:
                priority = "business"
            else:
                priority = "economy"

            for seat in range(1, self.seats_in_row + 1):
                Seat.objects.create(
                    airplane=self,
                    row=row,
                    seat_number=seat,
                    seat_class=seat_class[priority],
                )

    def clean(self):
        self.tail_number = self.tail_number.upper().strip()
        if not re.match(r"^[A-Z]{1,2}-?[A-Z0-9]{2,5}$", self.tail_number):
            raise ValidationError(
                "Tail number must be a valid registration format, "
                "like 'SP-LOT' or 'N12345'."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        self.tail_number = self.tail_number.upper().strip()
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self.generate_seats()

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

    route = models.ForeignKey(
        Route, on_delete=models.PROTECT, related_name="flights"
    )
    airplane = models.ForeignKey(
        Airplane, on_delete=models.PROTECT, related_name="flights"
    )
    crew_members = models.ManyToManyField(CrewMember, related_name="flights")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SCHEDULED
    )
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()

    class Meta:
        ordering = ["departure_time"]

    def clean(self):
        airplane_flights = self.airplane.flights.exclude(pk=self.pk)
        for flight in airplane_flights:
            if (
                flight.departure_time <= self.arrival_time
                and flight.arrival_time >= self.departure_time
            ):
                raise ValidationError(
                    f"Airplane {self.airplane} "
                    f"has another flight during this time."
                )

        if self.arrival_time <= self.departure_time:
            raise ValidationError(
                "Arrival time cannot be sooner than departure time."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (f"{self.route.source.code}→{self.route.destination.code} "
                f"{self.airplane} "
                f"[Departure: {self.departure_time:%Y-%m-%d %H:%M}]")


class SeatClass(models.Model):
    name = models.CharField(max_length=100, unique=True)
    priority = models.IntegerField(default=0, unique=True)
    multiplier = models.DecimalField(
        max_digits=3, decimal_places=2, default=1.00
    )

    class Meta:
        ordering = ["priority"]
        verbose_name_plural = "seat classes"

    def clean(self):
        if self.priority < 0:
            raise ValidationError("Priority can not be a negative integer.")
        if self.multiplier < Decimal("1.00"):
            raise ValidationError(
                "The seat price multiplier can not be less than 1.00."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        self.name = self.name.title().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Seat(models.Model):
    airplane = models.ForeignKey(
        Airplane, on_delete=models.CASCADE, related_name="seats"
    )
    row = models.IntegerField()
    seat_number = models.IntegerField()
    seat_class = models.ForeignKey(
        SeatClass, on_delete=models.PROTECT, related_name="seats"
    )

    class Meta:
        ordering = ["row", "seat_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["airplane", "row", "seat_number"],
                name="unique_seat",
            )
        ]

    def clean(self):
        if self.row <= 0 or self.row > self.airplane.rows:
            raise ValidationError(
                f"The row for this seat must be in range "
                f"1-{self.airplane.rows} "
            )
        if (self.seat_number <= 0
                or self.seat_number > self.airplane.seats_in_row):
            raise ValidationError(
                f"The seat number for this seat must be in range "
                f"1-{self.airplane.seats_in_row} "
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"Row #{self.row}, Seat #{self.seat_number}, "
            f"Class: {self.seat_class.name}"
        )


class Order(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order placed by {self.user} at {self.created_at}"


class Ticket(models.Model):
    flight = models.ForeignKey(
        Flight, on_delete=models.PROTECT, related_name="tickets"
    )
    seat = models.ForeignKey(
        Seat, on_delete=models.PROTECT, related_name="tickets"
    )
    order = models.ForeignKey(
        Order, on_delete=models.PROTECT, related_name="tickets"
    )
    price = models.DecimalField(max_digits=7, decimal_places=2)

    class Meta:
        ordering = ["-order__created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["flight", "seat"],
                name="unique_ticket",
            )
        ]

    @staticmethod
    def get_price(flight: Flight, seat: Seat) -> Decimal:
        distance = round(flight.route.distance)
        base_price = Decimal("0.1")

        if distance <= 500:
            base_price *= 3
        elif 501 <= distance <= 1500:
            base_price *= 2

        seat_class_mult = seat.seat_class.multiplier
        return Decimal(base_price * distance * seat_class_mult).quantize(
            Decimal("0.01")
        )

    def clean(self):
        if self.flight.airplane != self.seat.airplane:
            raise ValidationError("Seat must be appropriate for this flight.")

    def save(self, *args, **kwargs):
        self.price = self.get_price(self.flight, self.seat)
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (f"Ticket for {self.flight} "
                f"Seat {self.seat.row}-{self.seat.seat_number}")
