from django.contrib import admin

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
admin.site.register(Flight)
admin.site.register(Ticket)
admin.site.register(Order)
