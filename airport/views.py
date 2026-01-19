from django.db.models import Count, F, Sum
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
)
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

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
from airport.permissions import (
    IsAdminOrIfAuthenticatedReadOnly,
    IsAdminOrReadOnly,
)
from airport.serializers import (
    AirplaneDetailSerializer,
    AirplaneListSerializer,
    AirplaneSerializer,
    AirplaneTypeSerializer,
    AirportDetailSerializer,
    AirportListSerializer,
    AirportSerializer,
    CityDetailSerializer,
    CityListSerializer,
    CitySerializer,
    CountrySerializer,
    CrewMemberSerializer,
    FlightDetailSerializer,
    FlightListSerializer,
    FlightSerializer,
    OrderDetailSerializer,
    OrderListSerializer,
    OrderSerializer,
    RouteDetailSerializer,
    RouteListSerializer,
    RouteSerializer,
    SeatClassSerializer,
    SeatDetailSerializer,
    SeatListSerializer,
    SeatSerializer,
    TicketDetailSerializer,
    TicketListSerializer,
    TicketSerializer,
)
from airport.utils import (
    params_to_datetime,
    params_to_decimal,
    params_to_ints,
    params_to_str,
    parse_date_range,
)


class CountryViewSet(ModelViewSet):
    """
    Countries.
    Read-only for non-admin users.
    Admins can create/update/delete.
    No query parameters supported.
    """

    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = (IsAdminOrReadOnly,)


class CityViewSet(ModelViewSet):
    """
    Read-only access to cities.
    Non-safe methods allowed for admin.

    Filters:
      - countries: array[int] — country IDs; comma-separated or repeated.
    """

    queryset = City.objects.select_related("country")
    serializer_class = CitySerializer
    permission_classes = (IsAdminOrReadOnly,)

    def get_queryset(self):
        countries_ids = params_to_ints(self.request.query_params, "countries")
        queryset = self.queryset

        if countries_ids:
            queryset = queryset.filter(country__id__in=countries_ids)
        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return CityListSerializer
        if self.action == "retrieve":
            return CityDetailSerializer

        return CitySerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="countries",
                type=OpenApiTypes.INT,
                many=True,
                location=OpenApiParameter.QUERY,
                description=(
                    "Filter by one or more country IDs. "
                    "Supports both repeated parameters "
                    "(`?countries=1&countries=2`) "
                    "and comma-separated lists (`?countries=1,2`)."
                ),
                examples=[
                    OpenApiExample("Single value", value=[1]),
                    OpenApiExample("Multiple values", value=[1, 2]),
                ],
            )
        ],
    )
    def list(self, request, *args, **kwargs):
        """Get list of cities."""
        return super().list(request, *args, **kwargs)


class AirportViewSet(ModelViewSet):
    """
    Manage airports.

    Filters:
      - cities: array[int] — city IDs; comma-separated or repeated.
    """

    queryset = Airport.objects.select_related("city", "city__country")
    serializer_class = AirportSerializer
    permission_classes = (IsAdminOrReadOnly,)

    def get_serializer_class(self):
        if self.action == "list":
            return AirportListSerializer
        if self.action == "retrieve":
            return AirportDetailSerializer

        return AirportSerializer

    def get_queryset(self):
        queryset = self.queryset
        cities = params_to_ints(self.request.query_params, "cities")

        if cities:
            queryset = queryset.filter(city__id__in=cities)
        return queryset.distinct()

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="cities",
                type=OpenApiTypes.INT,
                many=True,
                location=OpenApiParameter.QUERY,
                description=(
                    "Filter by one or more city IDs. "
                    "Supports both repeated parameters (`?cities=1&cities=2`) "
                    "and comma-separated lists (`?cities=1,2`)."
                ),
                examples=[
                    OpenApiExample("Single value", value=[1]),
                    OpenApiExample("Multiple values", value=[1, 2]),
                ],
            )
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class RouteViewSet(ModelViewSet):
    """
    Manage routes.
    Filters: sources/destinations (IDs) or
    source_codes/destination_codes (IATA).
    If both sources and source_codes are provided, sources are used.
    """

    queryset = Route.objects.select_related(
        "source",
        "source__city",
        "source__city__country",
        "destination",
        "destination__city",
        "destination__city__country",
    )
    serializer_class = RouteSerializer
    permission_classes = (IsAdminOrReadOnly,)

    def get_serializer_class(self):
        if self.action == "list":
            return RouteListSerializer
        if self.action == "retrieve":
            return RouteDetailSerializer

        return self.serializer_class

    def get_queryset(self):
        queryset = self.queryset
        sources = params_to_ints(self.request.query_params, "sources")
        destinations = params_to_ints(
            self.request.query_params, "destinations"
        )

        if sources:
            queryset = queryset.filter(source__id__in=sources)
        elif codes := params_to_str(
            self.request.query_params, "source_codes", max_length=3, upper=True
        ):
            queryset = queryset.filter(source__code__in=codes)

        if destinations:
            queryset = queryset.filter(destination__id__in=destinations)
        elif codes := params_to_str(
            self.request.query_params,
            "destination_codes",
            max_length=3, upper=True
        ):
            queryset = queryset.filter(destination__code__in=codes)

        return queryset.distinct()

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="sources",
                type=OpenApiTypes.INT,
                many=True,
                location=OpenApiParameter.QUERY,
                description=(
                    "Filter by one or more source IDs. "
                    "Supports both repeated parameters "
                    "(`?sources=1&sources=2`) "
                    "and comma-separated lists (`?sources=1,2`)."
                ),
                examples=[
                    OpenApiExample("Single value", value=[1]),
                    OpenApiExample("Multiple values", value=[1, 2]),
                ],
            ),
            OpenApiParameter(
                name="destinations",
                type=OpenApiTypes.INT,
                many=True,
                location=OpenApiParameter.QUERY,
                description=(
                    "Filter by one or more destination IDs. "
                    "Supports both repeated parameters "
                    "(`?destinations=1&destinations=2`) "
                    "and comma-separated lists (`?destinations=1,2`)."
                ),
                examples=[
                    OpenApiExample("Single value", value=[1]),
                    OpenApiExample("Multiple values", value=[1, 2]),
                ],
            ),
            OpenApiParameter(
                name="source_codes",
                type=OpenApiTypes.STR,
                many=True,
                location=OpenApiParameter.QUERY,
                description=(
                    "Filter by source airport IATA codes (3 letters). "
                    "Supports repeated params and comma-separated values. "
                    "Example: `AMS`."
                ),
            ),
            OpenApiParameter(
                name="destination_codes",
                type=OpenApiTypes.STR,
                many=True,
                location=OpenApiParameter.QUERY,
                description=(
                    "Filter by destination airport IATA codes (3 letters). "
                    "Supports repeated params and comma-separated values. "
                    "Example: `LHR`."
                ),
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class CrewMemberViewSet(ModelViewSet):
    """Manage crew members. No query parameters supported."""

    queryset = CrewMember.objects.all()
    serializer_class = CrewMemberSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class AirplaneTypeViewSet(ModelViewSet):
    """Manage airplane types. No query parameters supported."""

    queryset = AirplaneType.objects.all()
    serializer_class = AirplaneTypeSerializer
    permission_classes = (IsAdminOrReadOnly,)


class AirplaneViewSet(ModelViewSet):
    """
    Manage airplanes.

    Filters:
      - airplane_types: array[int] — airplane type IDs;
      comma-separated or repeated.
    """

    queryset = Airplane.objects.select_related("airplane_type")
    serializer_class = AirplaneSerializer
    permission_classes = (IsAdminOrReadOnly,)

    def get_queryset(self):
        queryset = self.queryset
        airplane_types = params_to_ints(
            self.request.query_params, "airplane_types"
        )

        if airplane_types:
            queryset = queryset.filter(airplane_type__id__in=airplane_types)

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return AirplaneListSerializer
        if self.action == "retrieve":
            return AirplaneDetailSerializer

        return self.serializer_class

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="airplane_types",
                type=OpenApiTypes.INT,
                many=True,
                location=OpenApiParameter.QUERY,
                description=(
                    "Filter by one or more airplane type IDs. "
                    "Supports both repeated parameters "
                    "(`?airplane_types=1&airplane_types=2`) "
                    "and comma-separated lists (`?airplane_types=1,2`)."
                ),
                examples=[
                    OpenApiExample("Single value", value=[1]),
                    OpenApiExample("Multiple values", value=[1, 2]),
                ],
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class FlightViewSet(ModelViewSet):
    """
    Manage flights.

    Filters:
      - origin (city ID), destination (city ID)
      - status (multiple)
      - departure_time (UTC lower bound, 'YYYY-MM-DD HH:MM')
      - departure_date (origin-local day if one origin; otherwise UTC day)
    """

    queryset = (
        Flight.objects.select_related(
            "route",
            "route__source",
            "route__source__city",
            "route__source__city__country",
            "route__destination",
            "route__destination__city",
            "route__destination__city__country",
            "airplane",
            "airplane__airplane_type",
        )
        .prefetch_related(
            "crew_members",
            "tickets",
        )
        .annotate(capacity=F("airplane__rows") * F("airplane__seats_in_row"))
        .annotate(tickets_available=F("capacity") - Count(
            "tickets", distinct=True)
        )
    )
    serializer_class = FlightSerializer
    permission_classes = (IsAdminOrReadOnly,)

    def get_serializer_class(self):
        if self.action == "list":
            return FlightListSerializer
        if self.action == "retrieve":
            return FlightDetailSerializer

        return self.serializer_class

    def get_queryset(self):
        """
        Returns a filtered queryset of Flight objects
        based on query parameters.

        Supported filters:
          - origin (city ID): restricts to flights departing from this city.
          - destination (city ID): restricts to flights arriving at this city.
          - status: one or more valid Flight.Status values.
          - departure_time: lower bound (UTC datetime).
          - departure_date: calendar day, interpreted as:
              • local day if a single origin is provided,
              • UTC day otherwise.

        All comparisons are done in UTC. Returned datetimes are stored in UTC.
        """
        queryset = self.queryset
        origin = self.request.query_params.get("origin")
        destination = self.request.query_params.get("destination")
        status = params_to_str(
            self.request.query_params,
            "status",
            alpha=False,
            choices=[c[0] for c in Flight.Status.choices],
        )
        departure_time = params_to_datetime(
            self.request.query_params, "departure_time"
        )
        departure_date = self.request.query_params.get("departure_date")

        if status:
            queryset = queryset.filter(status__in=status)

        if origin:
            try:
                queryset = queryset.filter(route__source__city__id=origin)
            except ValueError:
                raise ValidationError(
                    {"origin": f"'{origin}' is not a valid integer"}
                )

        if destination:
            try:
                queryset = queryset.filter(
                    route__destination__city__id=destination
                )
            except ValueError:
                raise ValidationError(
                    {"destination": f"'{destination}' is not a valid integer"}
                )

        if departure_time:
            queryset = queryset.filter(departure_time__gte=departure_time)

        if departure_date:
            if origin:
                try:
                    city = City.objects.get(id=origin)
                except City.DoesNotExist:
                    raise ValidationError(
                        {"origin": f"'{origin}' city does not exist"}
                    )
                date_range = parse_date_range(
                    departure_date, "departure_date", time_zone=city.timezone
                )
            else:
                date_range = parse_date_range(departure_date, "departure_date")

            queryset = queryset.filter(
                departure_time__gte=date_range[0],
                departure_time__lt=date_range[1]
            )

        return queryset.distinct()

    @extend_schema(
        summary="List available seats for a flight",
        description="Returns all seats on the flight's airplane "
                    "that are not yet booked for this flight.",
        responses=SeatListSerializer(many=True),
    )
    @action(detail=True, methods=["GET"])
    def available_seats(self, request, *args, **kwargs):
        flight = self.get_object()
        all_seats = flight.airplane.seats.select_related("seat_class")
        taken_seats_ids = Ticket.objects.filter(flight=flight).values_list(
            "seat_id", flat=True
        )
        available_seats = all_seats.exclude(id__in=taken_seats_ids)
        serializer = SeatListSerializer(available_seats, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="List flights with filtering",
        description=(
            "All times are stored and returned in UTC.\n\n"
            "- `departure_time` is a UTC lower bound (`%Y-%m-%d %H:%M`).\n"
            "- `departure_date` is interpreted "
            "as the origin's **local** calendar day "
            "when a single origin is provided; otherwise as a **UTC** day. "
            "Filtering is performed in UTC internally."
        ),
        parameters=[
            OpenApiParameter(
                name="origin",
                description="Origin **city** ID (single).",
                required=False,
                type=OpenApiTypes.INT,
            ),
            OpenApiParameter(
                name="destination",
                description="Destination **city** ID (single).",
                required=False,
                type=OpenApiTypes.INT,
            ),
            OpenApiParameter(
                name="status",
                description="Flight status (multiple allowed).",
                required=False,
                many=True,
                type=OpenApiTypes.STR,
                enum=[c[0] for c in Flight.Status.choices],
            ),
            OpenApiParameter(
                name="departure_time",
                description="Shows all flights after this point in time. "
                            "Format: `YYYY-MM-DD HH:MM`.",
                required=False,
                type=OpenApiTypes.STR,
                examples=[
                    OpenApiExample("Example", value="2026-01-01 10:30"),
                ],
            ),
            OpenApiParameter(
                name="departure_date",
                description=(
                    "Calendar date filter. "
                    "If **one origin** is provided - origin-local day; "
                    "otherwise - UTC day. Format: `YYYY-MM-DD`."
                ),
                required=False,
                type=OpenApiTypes.DATE,
                examples=[
                    OpenApiExample("Example", value="2026-01-01"),
                ],
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class SeatClassViewSet(ModelViewSet):
    queryset = SeatClass.objects.all()
    serializer_class = SeatClassSerializer
    permission_classes = (IsAdminOrReadOnly,)


class SeatViewSet(ReadOnlyModelViewSet):
    """
    Seats (authenticated read-only).

    Filters:
      - airplanes: airplane IDs; comma-separated or repeated.
    """

    queryset = Seat.objects.select_related(
        "airplane", "airplane__airplane_type", "seat_class"
    )
    serializer_class = SeatSerializer
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.action == "list":
            return SeatListSerializer
        if self.action == "retrieve":
            return SeatDetailSerializer

        return self.serializer_class

    def get_queryset(self):
        queryset = self.queryset
        airplanes = params_to_ints(self.request.query_params, "airplanes")

        if airplanes:
            try:
                queryset = queryset.filter(airplane__id__in=airplanes)
            except ValueError:
                raise ValidationError(
                    {"airplane": f"'{airplanes}' is not a valid integer"}
                )

        return queryset.distinct()

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="airplanes",
                type=OpenApiTypes.INT,
                many=True,
                location=OpenApiParameter.QUERY,
                description=(
                    "Filter by one or more airplane IDs. "
                    "Supports both repeated parameters "
                    "(`?airplanes=1&airplanes=2`) "
                    "and comma-separated lists (`?airplanes=1,2`)."
                ),
                examples=[
                    OpenApiExample("Single value", value=[1]),
                    OpenApiExample("Multiple values", value=[1, 2]),
                ],
            )
        ],
    )
    def list(self, request, *args, **kwargs):
        """Get list of seats."""
        return super().list(request, *args, **kwargs)


class TicketViewSet(ReadOnlyModelViewSet):
    """
    Read-only access to tickets.

    Filters:
      - users (admin only): array[int] — user IDs to include.
      - orders: array[int] — order IDs to include.
      - flights: array[int] — flight IDs to include.
      - seat_classes: array[int] — seat class IDs to include.
      - price_min / price_max: decimal strings — inclusive bounds;
      'min' must not exceed 'max'.
    """

    queryset = Ticket.objects.select_related(
        "seat",
        "seat__seat_class",
        "seat__airplane",
        "seat__airplane__airplane_type",
        "flight",
        "flight__route",
        "flight__route__source",
        "flight__route__destination",
        "flight__airplane",
        "flight__airplane__airplane_type",
        "order",
    )
    serializer_class = TicketSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        """
        Returns tickets for the current user. Admins may filter by users.
        Supported filters: users (admin),
        orders, flights, seat_classes, price_min/max.
        """
        if self.request.user.is_staff:
            queryset = self.queryset
            users = params_to_ints(self.request.query_params, "users")
        else:
            queryset = super().get_queryset().filter(
                order__user=self.request.user
            )
        orders = params_to_ints(self.request.query_params, "orders")
        flights = params_to_ints(self.request.query_params, "flights")
        seat_classes = params_to_ints(
            self.request.query_params, "seat_classes"
        )
        price_min = params_to_decimal(self.request.query_params, "price_min")
        price_max = params_to_decimal(self.request.query_params, "price_max")

        if self.request.user.is_staff and users:
            queryset = queryset.filter(order__user__id__in=users)

        if orders:
            queryset = queryset.filter(order__id__in=orders)

        if flights:
            queryset = queryset.filter(flight_id__in=flights)

        if seat_classes:
            queryset = queryset.filter(seat__seat_class__id__in=seat_classes)

        if (price_min is not None and price_max is not None
                and price_min > price_max):
            raise ValidationError(
                {"price": ["price_min cannot be greater than price_max"]}
            )

        if price_min is not None:
            queryset = queryset.filter(price__gte=price_min)

        if price_max is not None:
            queryset = queryset.filter(price__lte=price_max)

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return TicketListSerializer
        if self.action == "retrieve":
            return TicketDetailSerializer

        return self.serializer_class

    @extend_schema(
        summary="List my tickets (filterable)",
        description=(
            "Returns tickets for the authenticated user. "
            "Admins may scope results to other users via `users`.\n\n"
            "**Filters:**\n"
            "- `orders`, `flights`, `seat_classes`: "
            "comma-separated or repeated values.\n"
            "- `price_min`, `price_max`: decimal strings (inclusive).\n\n"
        ),
        parameters=[
            OpenApiParameter(
                name="users",
                description="**Admin only.** Filter by user IDs. "
                            "Comma-separated or repeated.",
                required=False,
                type=OpenApiTypes.INT,
                many=True,
            ),
            OpenApiParameter(
                name="orders",
                description="Filter by Order IDs. "
                            "Comma-separated or repeated.",
                required=False,
                type=OpenApiTypes.INT,
                many=True,
            ),
            OpenApiParameter(
                name="flights",
                description="Filter by Flight IDs. "
                            "Comma-separated or repeated.",
                required=False,
                type=OpenApiTypes.INT,
                many=True,
            ),
            OpenApiParameter(
                name="seat_classes",
                description="Filter by SeatClass IDs. "
                            "Comma-separated or repeated.",
                required=False,
                type=OpenApiTypes.INT,
                many=True,
            ),
            OpenApiParameter(
                name="price_min",
                description="Minimum ticket price (decimal). Inclusive.",
                required=False,
                type=OpenApiTypes.NUMBER,
                examples=[OpenApiExample("Min. price", value="99.99")],
            ),
            OpenApiParameter(
                name="price_max",
                description="Maximum ticket price (decimal). Inclusive.",
                required=False,
                type=OpenApiTypes.NUMBER,
                examples=[OpenApiExample("Max. price", value="250.00")],
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class OrderViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Manage orders for the authenticated user.
    Results are always scoped to the current user.
    No query filters supported.
    """

    serializer_class = OrderSerializer
    queryset = Order.objects.select_related("user").annotate(
        total_price=Sum("tickets__price")
    )
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer
        if self.action == "retrieve":
            return OrderDetailSerializer

        return self.serializer_class

    def get_queryset(self):
        qs = self.queryset
        if self.action == "retrieve":
            qs = qs.prefetch_related(
                "tickets",
                "tickets__seat",
                "tickets__seat__seat_class",
                "tickets__seat__airplane",
                "tickets__flight",
            )

        return qs.filter(user=self.request.user)

    @extend_schema(
        summary="Create an order",
        description="Creates an order for the authenticated user. "
                    "Requires at least one ticket.",
        request=OrderSerializer,
        responses={201: OrderDetailSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        instance = self.get_queryset().get(pk=order.pk)
        out = OrderDetailSerializer(
            instance, context=self.get_serializer_context()
        )
        headers = self.get_success_headers(serializer.data)
        return Response(
            out.data, status=status.HTTP_201_CREATED, headers=headers
        )
