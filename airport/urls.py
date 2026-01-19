from django.urls import include, path
from rest_framework import routers

from airport.views import (
    AirplaneTypeViewSet,
    AirplaneViewSet,
    AirportViewSet,
    CityViewSet,
    CountryViewSet,
    CrewMemberViewSet,
    FlightViewSet,
    OrderViewSet,
    RouteViewSet,
    SeatClassViewSet,
    SeatViewSet,
    TicketViewSet,
)

router = routers.DefaultRouter()
router.register("countries", CountryViewSet)
router.register("cities", CityViewSet)
router.register("airports", AirportViewSet)
router.register("routes", RouteViewSet)
router.register("crew_members", CrewMemberViewSet)
router.register("airplane_types", AirplaneTypeViewSet)
router.register("airplanes", AirplaneViewSet)
router.register("flights", FlightViewSet)
router.register("seat_classes", SeatClassViewSet)
router.register("seats", SeatViewSet)
router.register("orders", OrderViewSet)
router.register("tickets", TicketViewSet)

urlpatterns = [path("", include(router.urls))]

app_name = "airport"
