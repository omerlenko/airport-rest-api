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

class TicketInline(admin.TabularInline):
    model = Ticket
    extra = 1

admin.site.register(Country)
admin.site.register(City)
admin.site.register(Airport)
admin.site.register(Route)
admin.site.register(CrewMember)
admin.site.register(AirplaneType)
admin.site.register(Airplane)
admin.site.register(SeatClass)

@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    form = FlightAdminForm

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    readonly_fields = ("price",)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = (TicketInline,)

