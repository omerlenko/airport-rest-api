from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from airport.models import Country, City, Airport, Route
from airport.serializers import CountrySerializer, CitySerializer, AirportSerializer, AirportListSerializer, \
    AirportDetailSerializer, RouteSerializer, RouteListSerializer, RouteDetailSerializer


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

        return RouteSerializer