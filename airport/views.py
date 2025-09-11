from django.db.models import Sum
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from airport.models import Country, City, Airport, Route, CrewMember, AirplaneType, Airplane, Flight, SeatClass, Order, \
    Ticket
from airport.serializers import CountrySerializer, CitySerializer, AirportSerializer, AirportListSerializer, \
    AirportDetailSerializer, RouteSerializer, RouteListSerializer, RouteDetailSerializer, CrewMemberSerializer, \
    AirplaneTypeSerializer, AirplaneSerializer, AirplaneListSerializer, AirplaneDetailSerializer, FlightSerializer, \
    FlightListSerializer, FlightDetailSerializer, SeatClassSerializer, OrderSerializer, OrderListSerializer, \
    OrderDetailSerializer, TicketSerializer, TicketListSerializer, TicketDetailSerializer


class CountryViewSet(ReadOnlyModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer


class CityViewSet(ReadOnlyModelViewSet):
    queryset = City.objects.select_related("country")
    serializer_class = CitySerializer


class AirportViewSet(ModelViewSet):
    queryset = Airport.objects.select_related("city", "city__country")
    serializer_class = AirportSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return AirportListSerializer
        if self.action == "retrieve":
            return AirportDetailSerializer

        return AirportSerializer


class RouteViewSet(ModelViewSet):
    queryset = Route.objects.select_related(
        "source",
        "source__city",
        "source__city__country",
        "destination",
        "destination__city",
        "destination__city__country"
    )
    serializer_class = RouteSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return RouteListSerializer
        if self.action == "retrieve":
            return RouteDetailSerializer

        return self.serializer_class


class CrewMemberViewSet(ModelViewSet):
    queryset = CrewMember.objects.all()
    serializer_class = CrewMemberSerializer


class AirplaneTypeViewSet(ModelViewSet):
    queryset = AirplaneType.objects.all()
    serializer_class = AirplaneTypeSerializer


class AirplaneViewSet(ModelViewSet):
    queryset = Airplane.objects.select_related("airplane_type")
    serializer_class = AirplaneSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return AirplaneListSerializer
        if self.action == "retrieve":
            return AirplaneDetailSerializer

        return self.serializer_class


class FlightViewSet(ModelViewSet):
    queryset = Flight.objects.select_related(
        "route",
        "route__source",
        "route__source__city",
        "route__source__city__country",
        "route__destination",
        "route__destination__city",
        "route__destination__city__country",
        "airplane",
        "airplane__airplane_type"
    ).prefetch_related(
        "crew_members",
    )
    serializer_class = FlightSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return FlightListSerializer
        if self.action == "retrieve":
            return FlightDetailSerializer

        return self.serializer_class


class SeatClassViewSet(ReadOnlyModelViewSet):
    queryset = SeatClass.objects.all()
    serializer_class = SeatClassSerializer


class TicketViewSet(ReadOnlyModelViewSet):
    queryset = Ticket.objects.select_related(
        "seat_class",
        "flight",
        "flight__route",
        "flight__route__source",
        "flight__route__destination",
        "flight__airplane",
        "flight__airplane__airplane_type",
        "order",
    )
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return super().get_queryset().filter(order__user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return TicketListSerializer
        if self.action == "retrieve":
            return TicketDetailSerializer

        return self.serializer_class


class OrderViewSet(ModelViewSet):
    serializer_class = OrderSerializer
    queryset = Order.objects.select_related(
        "user"
    ).prefetch_related(
        "tickets",
        "tickets__seat_class",
        "tickets__flight",
        "tickets__flight__route",
        "tickets__flight__airplane",
        "tickets__flight__airplane__airplane_type",
    ).annotate(total_price=Sum("tickets__price"))
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer
        if self.action == "retrieve":
            return OrderDetailSerializer

        return self.serializer_class


    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        instance = self.get_queryset().get(pk=order.pk)
        out = OrderDetailSerializer(instance, context=self.get_serializer_context())
        headers = self.get_success_headers(serializer.data)
        return Response(out.data, status=status.HTTP_201_CREATED, headers=headers)
