from django.core.exceptions import PermissionDenied

from rest_framework import serializers
from drf_extra_fields.geo_fields import PointField

from .models import Ambulance, AmbulanceUpdate, Call


# Ambulance serializers

class AmbulanceSerializer(serializers.ModelSerializer):

    location = PointField(required=False)
    
    class Meta:
        model = Ambulance
        fields = ['id', 'identifier',
                  'capability', 'status',
                  'orientation', 'location',
                  'timestamp',
                  'comment', 'updated_by', 'updated_on']
        read_only_fields = ('updated_by',)

    def validate(self, data):

        # timestamp must be defined together with either comment, status or location
        if 'timestamp' in data and not ('comment' in data or 'location' in data or 'status' in data):
            raise serializers.ValidationError('timestamp can only be set when either comment, location, ' +
                                              'or status are modified')

        return data

    def create(self, validated_data):

        # get current user
        user = validated_data['updated_by']

        # check credentials
        # only super can create
        if not user.is_superuser:
            raise PermissionDenied()
    
        return super().create(validated_data)
    
    def update(self, instance, validated_data):

        # get current user
        user = validated_data['updated_by']

        # check credentials
        if not user.is_superuser:

            # serializer.instance will always exist!
            if not user.profile.ambulances.filter(can_write=True,
                                                  ambulance=instance.id):
                raise PermissionDenied()

        return super().update(instance, validated_data)


class AmbulanceUpdateSerializer(serializers.ModelSerializer):

    location = PointField(required=False)
    ambulance_identifier = serializers.CharField(source='ambulance.identifier')
    updated_by_username = serializers.CharField(source='updated_by.username')

    class Meta:
        model = AmbulanceUpdate
        fields = ['id',
                  'ambulance_identifier',
                  'status', 'orientation',
                  'location', 'timestamp',
                  'comment',
                  'updated_by',
                  'updated_by_username', 'updated_on']
        read_only_fields = ['id',
                            'ambulance_identifier',
                            'updated_by',
                            'updated_by_username', 'updated_on']


# Call serializer
class CallSerializer(serializers.ModelSerializer):

    class Meta:
        model = Call
        fields = ['id', 'active', 'ambulances', 'patients', 'details',
                'priority','comment', 'updated_by', 'updated_on']
        read_only_fields = ('updated_by')

    def create(self, data):

        # Get current user.
        user = data['updated_by']

        # Make sure user is Super.
        if not user.is_superuser:
            raise PermissionDenied()

        return super().create(data)

    def update(self, instance, data):

        # Get current user.
        user = data['update_by']

        # Make sure user is Super.
        if not user.is_superuser:
            # Serializer instance will always exist!
            if not user.profile.calls.filter(can_write=True, call=instance.id):
                raise PermissionDenied()

        return super().update(instance, data)
