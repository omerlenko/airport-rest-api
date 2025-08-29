from rest_framework import serializers

from airport.models import Country, City, Airport, Route


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ("id", "name", "iso_code")


class CitySerializer(serializers.ModelSerializer):
    country = serializers.SlugRelatedField(many=False, read_only=True, slug_field="name")

    class Meta:
        model = City
        fields = ("id", "name", "country", "timezone")


class AirportSerializer(serializers.ModelSerializer):
    timezone = serializers.CharField(source="city.timezone", read_only=True)

    class Meta:
        model = Airport
        fields = ("id", "name", "city", "code", "timezone")

    def validate_code(self, value):
        value = value.strip().upper()
        if len(value) != 3 or not value.isalpha():
            raise serializers.ValidationError("Airport code must be exactly 3 letters. (e.g., 'JFK')")

        qs = Airport.objects.filter(code__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Airport code already exists.")
        return value


class AirportListSerializer(AirportSerializer):
    city = serializers.SlugRelatedField(many=False, read_only=True, slug_field="name")


class AirportDetailSerializer(AirportSerializer):
    city = CitySerializer(many=False, read_only=True)


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ("id", "source", "destination", "distance")

    def validate_distance(self, value):
        if value <= 0:
            raise serializers.ValidationError("Route distance must be greater than 0.")
        return value

    def validate(self, attrs):
        source = attrs.get("source", getattr(self.instance, "source", None))
        destination = attrs.get("destination", getattr(self.instance, "destination", None))
        if source is None or destination is None:
            return attrs

        if source == destination:
            raise serializers.ValidationError("Source and destination airports must be different.")

        qs = Route.objects.filter(source=source, destination=destination)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Route already exists.")
        return attrs

class RouteListSerializer(RouteSerializer):
    source = serializers.SlugRelatedField(many=False, read_only=True, slug_field="code")
    destination = serializers.SlugRelatedField(many=False, read_only=True, slug_field="code")


class RouteDetailSerializer(RouteSerializer):
    source = AirportDetailSerializer(many=False, read_only=True)
    destination = AirportDetailSerializer(many=False, read_only=True)