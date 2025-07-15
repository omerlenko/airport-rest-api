from django.contrib import admin
from .forms import FlightAdminForm
from airport.models import (
    Country,
    City,
    Airport,
    Route,
    CrewMember,
    AirplaneType,
    Airplane,
    SeatClass,
    Ticket,
    Order,
    Flight
)

admin.site.register(Country)
admin.site.register(City)
admin.site.register(Airport)
admin.site.register(Route)
admin.site.register(CrewMember)
admin.site.register(AirplaneType)
admin.site.register(Airplane)
admin.site.register(SeatClass)
admin.site.register(Order)

@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    form = FlightAdminForm

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    readonly_fields = ("price",)
