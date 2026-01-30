from django.contrib import admin

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

from .forms import FlightAdminForm


class TicketInline(admin.TabularInline):
    model = Ticket
    extra = 1
    readonly_fields = ("price",)


admin.site.register(Country)
admin.site.register(City)
admin.site.register(Airport)
admin.site.register(Route)
admin.site.register(CrewMember)
admin.site.register(AirplaneType)
admin.site.register(Airplane)
admin.site.register(SeatClass)
admin.site.register(Seat)


@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    form = FlightAdminForm


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    readonly_fields = ("price",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = (TicketInline,)
