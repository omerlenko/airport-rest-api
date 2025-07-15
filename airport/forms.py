from django import forms
from django.core.exceptions import ValidationError
from airport.models import Flight


class FlightAdminForm(forms.ModelForm):
    class Meta:
        model = Flight
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        departure = cleaned_data.get("departure_time")
        arrival = cleaned_data.get("arrival_time")
        crew_members = cleaned_data.get("crew_members")
        flight_id = self.instance.pk

        if crew_members and departure and arrival:
            for member in crew_members:
                member_flights = member.flights.exclude(pk=flight_id)
                for flight in member_flights:
                    if flight.departure_time <= arrival and flight.arrival_time >= departure:
                        raise ValidationError(f"Crew member {member} has another flight during this time.")

        return cleaned_data