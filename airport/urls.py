from django.urls import path, include
from rest_framework import routers

from airport.views import CountryViewSet, CityViewSet, AirportViewSet, RouteViewSet, CrewMemberViewSet, \
    AirplaneTypeViewSet, AirplaneViewSet, FlightViewSet, SeatClassViewSet, OrderViewSet, TicketViewSet

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
router.register("orders", OrderViewSet)
router.register("tickets", TicketViewSet)

urlpatterns = [
    path("", include(router.urls))
]

app_name = "airport"