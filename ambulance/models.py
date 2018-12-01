import logging
from enum import Enum

from django.contrib.auth.models import User
from django.contrib.gis.db import models
from django.utils import timezone
from django.urls import reverse
from django.template.defaulttags import register

from emstrack.latlon import calculate_orientation, calculate_distance, stationary_radius
from emstrack.models import AddressModel, UpdatedByModel, defaults

logger = logging.getLogger(__name__)


# filters

@register.filter
def get_ambulance_status(key):
    return AmbulanceStatus[key].value


@register.filter
def get_ambulance_capability(key):
    return AmbulanceCapability[key].value


@register.filter
def get_location_type(key):
    return LocationType[key].value

@register.filter
def get_location_coordinates(key):
    return str(key.x) + ", " + str(key.y)

@register.filter
def get_call_status(key):
    return CallStatus[key].value


@register.filter
def get_call_priority(key):
    return CallPriority[key].value


# Ambulance location models


# Ambulance model

class AmbulanceStatus(Enum):
    UK = 'Unknown'
    AV = 'Available'
    OS = 'Out of service'
    PB = 'Patient bound'
    AP = 'At patient'
    HB = 'Hospital bound'
    AH = 'At hospital'
    BB = 'Base bound'
    AB = 'At base'
    WB = 'Waypoint bound'
    AW = 'At waypoint'


AmbulanceStatusOrder = [ 
    AmbulanceStatus.AV,
    AmbulanceStatus.PB,
    AmbulanceStatus.AP,
    AmbulanceStatus.HB,
    AmbulanceStatus.AH,
    AmbulanceStatus.BB,
    AmbulanceStatus.AB,
    AmbulanceStatus.WB,
    AmbulanceStatus.AW,
    AmbulanceStatus.OS,
    AmbulanceStatus.UK
] 


class AmbulanceCapability(Enum):
    B = 'Basic'
    A = 'Advanced'
    R = 'Rescue'


AmbulanceCapabilityOrder = [ 
    AmbulanceCapability.B,
    AmbulanceCapability.A,
    AmbulanceCapability.R
] 


class Ambulance(UpdatedByModel):

    # TODO: Should we consider denormalizing Ambulance to avoid duplication with AmbulanceUpdate?

    # ambulance properties
    identifier = models.CharField(max_length=50, unique=True)

    # TODO: Should we add an active flag?

    AMBULANCE_CAPABILITY_CHOICES = \
        [(m.name, m.value) for m in AmbulanceCapability]
    capability = models.CharField(max_length=1,
                                  choices=AMBULANCE_CAPABILITY_CHOICES)

    # status
    AMBULANCE_STATUS_CHOICES = \
        [(m.name, m.value) for m in AmbulanceStatus]
    status = models.CharField(max_length=2,
                              choices=AMBULANCE_STATUS_CHOICES,
                              default=AmbulanceStatus.UK.name)

    # location
    orientation = models.FloatField(default=0.0)
    location = models.PointField(srid=4326, default=defaults['location'])

    # timestamp
    timestamp = models.DateTimeField(default=timezone.now)

    # location client
    location_client = models.ForeignKey('login.Client',
                                        on_delete=models.CASCADE,
                                        blank=True, null=True,
                                        related_name='location_client_set')

    # default value for _loaded_values
    _loaded_values = None

    @classmethod
    def from_db(cls, db, field_names, values):

        # call super
        instance = super(Ambulance, cls).from_db(db, field_names, values)

        # store the original field values on the instance
        instance._loaded_values = dict(zip(field_names, values))

        # return instance
        return instance

    def save(self, *args, **kwargs):

        # creation?
        created = self.pk is None

        # loaded_values?
        loaded_values = self._loaded_values is not None

        # has location changed?
        has_moved = False
        if (not loaded_values) or \
                calculate_distance(self._loaded_values['location'], self.location) > stationary_radius:
            has_moved = True

        # calculate orientation only if location has changed and orientation has not changed
        if has_moved and loaded_values and self._loaded_values['orientation'] == self.orientation:
            # TODO: should we allow for a small radius before updating direction?
            self.orientation = calculate_orientation(self._loaded_values['location'], self.location)
            logger.debug('< {} - {} = {}'.format(self._loaded_values['location'],
                                                 self.location,
                                                 self.orientation))

        logger.debug('loaded_values: {}'.format(loaded_values))
        logger.debug('_loaded_values: {}'.format(self._loaded_values))
        logger.debug('self.location_client: {}'.format(self.location_client))

        # location_client changed?
        if self.location_client is None:
            location_client_id = None
        else:
            location_client_id = self.location_client.id
        location_client_changed = False
        if loaded_values and location_client_id != self._loaded_values['location_client_id']:
            location_client_changed = True

        logger.debug('location_client_changed: {}'.format(location_client_changed))
        # TODO: Check if client is logged with ambulance if setting location_client

        # if comment, status or location changed
        model_changed = False
        if has_moved or \
                self._loaded_values['status'] != self.status or \
                self._loaded_values['comment'] != self.comment:

            # save to Ambulance
            super().save(*args, **kwargs)

            logger.debug('SAVED')

            # save to AmbulanceUpdate
            data = {k: getattr(self, k)
                    for k in ('status', 'orientation',
                              'location', 'timestamp',
                              'comment', 'updated_by', 'updated_on')}
            data['ambulance'] = self
            obj = AmbulanceUpdate(**data)
            obj.save()

            logger.debug('UPDATE SAVED')

            # model changed
            model_changed = True

        # if identifier or capability changed
        # NOTE: self._loaded_values is NEVER None because has_moved is True
        elif (location_client_changed or
              self._loaded_values['identifier'] != self.identifier or
              self._loaded_values['capability'] != self.capability):

            # save only to Ambulance
            super().save(*args, **kwargs)

            logger.debug('SAVED')

            # model changed
            model_changed = True

        # Did the model change?
        if model_changed:

            # publish to mqtt
            from mqtt.publish import SingletonPublishClient
            SingletonPublishClient().publish_ambulance(self)

            logger.debug('PUBLISHED ON MQTT')

        # just created?
        if created:
            # invalidate permissions cache
            from login.permissions import cache_clear
            cache_clear()

    def delete(self, *args, **kwargs):

        # remove from mqtt
        from mqtt.publish import SingletonPublishClient
        SingletonPublishClient().remove_ambulance(self)

        # invalidate permissions cache
        from login.permissions import cache_clear
        cache_clear()

        # delete from Ambulance
        super().delete(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('ambulance:detail', kwargs={'pk': self.id})

    def __str__(self):
        return ('Ambulance {}(id={}) ({}) [{}]:\n' +
                '    Status: {}\n' +
                '  Location: {} @ {}\n' +
                ' LocClient: {}\n' +
                '   Updated: {} by {}').format(self.identifier,
                                               self.id,
                                               AmbulanceCapability[self.capability].value,
                                               self.comment,
                                               AmbulanceStatus[self.status].value,
                                               self.location,
                                               self.timestamp,
                                               self.location_client,
                                               self.updated_by,
                                               self.updated_on)


class AmbulanceUpdate(models.Model):

    # ambulance
    ambulance = models.ForeignKey(Ambulance,
                                  on_delete=models.CASCADE)

    # # ambulance call
    # # TODO: Is it possible to enforce that ambulance_call.ambulance == ambulance?
    # ambulance_call = models.ForeignKey(AmbulanceCall,
    #                                    on_delete=models.SET_NULL,
    #                                    null=True)

    # ambulance status
    AMBULANCE_STATUS_CHOICES = \
        [(m.name, m.value) for m in AmbulanceStatus]
    status = models.CharField(max_length=2,
                              choices=AMBULANCE_STATUS_CHOICES,
                              default=AmbulanceStatus.UK.name)

    # location
    orientation = models.FloatField(default=0.0)
    location = models.PointField(srid=4326, default=defaults['location'])

    # timestamp, indexed
    timestamp = models.DateTimeField(db_index=True, default=timezone.now)

    # comment
    comment = models.CharField(max_length=254, null=True, blank=True)

    # updated by
    updated_by = models.ForeignKey(User,
                                   on_delete=models.CASCADE)
    updated_on = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(
                fields=['ambulance', 'timestamp'],
                name='ambulance_timestamp_idx',
            ),
        ]


# Call related models

class CallPriority(Enum):
    A = 'Resuscitation'
    B = 'Emergent'
    C = 'Urgent'
    D = 'Less urgent'
    E = 'Not urgent'
    O = 'Omega'


CallPriorityOrder = [ 
    CallPriority.A,
    CallPriority.B,
    CallPriority.C,
    CallPriority.D,
    CallPriority.E,
    CallPriority.O,
] 


class CallStatus(Enum):
    P = 'Pending'
    S = 'Started'
    E = 'Ended'


CallStatusOrder = [ 
    CallStatus.P,
    CallStatus.S,
    CallStatus.E
] 


class PublishMixin:

    def save(self, *args, **kwargs):

        # publish?
        publish = kwargs.pop('publish', True)

        # remove?
        remove = kwargs.pop('remove', False)

        # save to Call
        super().save(*args, **kwargs)

        if publish:
            if remove:
                # This makes sure that it will not be retained
                self.publish(retain=False)
            else:
                self.publish()

        if remove:
            self.remove()


class Call(PublishMixin,
           UpdatedByModel):

    # status
    CALL_STATUS_CHOICES = \
        [(m.name, m.value) for m in CallStatus]
    status = models.CharField(max_length=1,
                              choices=CALL_STATUS_CHOICES,
                              default=CallStatus.P.name)

    # details
    details = models.CharField(max_length=500, default="")

    # call priority
    CALL_PRIORITY_CHOICES = \
        [(m.name, m.value) for m in CallPriority]
    priority = models.CharField(max_length=1,
                                choices=CALL_PRIORITY_CHOICES,
                                default=CallPriority.E.name)

    # timestamps
    pending_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    # created at
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):

        # publish?
        publish = kwargs.pop('publish', True)

        # remove?
        remove = kwargs.pop('remove', False)

        if self.status == CallStatus.E.name:

            # timestamp
            self.ended_at = timezone.now()

            # remove topic from mqtt server
            remove = True

        elif self.status == CallStatus.S.name:

            # timestamp
            self.started_at = timezone.now()

        elif self.status == CallStatus.P.name:

            # timestamp
            self.pending_at = timezone.now()

        # call super
        super().save(*args, **kwargs,
                     publish=publish,
                     remove=remove)

    def publish(self, **kwargs):

        # publish to mqtt
        from mqtt.publish import SingletonPublishClient
        SingletonPublishClient().publish_call(self, **kwargs)

    def remove(self):

        # remove topic from mqtt server
        from mqtt.publish import SingletonPublishClient
        SingletonPublishClient().remove_call(self)

    def abort(self):

        # simply return if already ended
        if self.status == CallStatus.E.name:
            return

        # retrieve all ongoing ambulances
        ongoing_ambulancecalls = self.ambulancecall_set.exclude(status=AmbulanceCallStatus.C.name)

        if ongoing_ambulancecalls:
            # if  ambulancecalls, set ambulancecall to complete until all done

            for ambulancecall in ongoing_ambulancecalls:

                # change call status to finished
                ambulancecall.status = AmbulanceCallStatus.C.name
                ambulancecall.save()

            # At the last ambulance call will be closed

        else:
            # if no ambulancecalls, force abort

            # change call status to finished
            self.status = CallStatus.E.name
            self.save()

    def __str__(self):
        return "{} ({})".format(self.status, self.priority)


class AmbulanceCallStatus(Enum):
    R = 'Requested'
    O = 'Ongoing'
    D = 'Declined'
    S = 'Suspended'
    C = 'Completed'


class AmbulanceCallHistory(models.Model):

    # status
    AMBULANCE_CALL_STATUS_CHOICES = \
        [(m.name, m.value) for m in AmbulanceCallStatus]
    status = models.CharField(max_length=1,
                              choices=AMBULANCE_CALL_STATUS_CHOICES,
                              default=AmbulanceCallStatus.R.name)

    # call
    call = models.ForeignKey(Call,
                             on_delete=models.CASCADE)

    # ambulance
    ambulance = models.ForeignKey(Ambulance,
                                  on_delete=models.CASCADE)

    # created at
    created_at = models.DateTimeField()


class AmbulanceCall(PublishMixin,
                    models.Model):

    # status
    AMBULANCE_CALL_STATUS_CHOICES = \
        [(m.name, m.value) for m in AmbulanceCallStatus]
    status = models.CharField(max_length=1,
                              choices=AMBULANCE_CALL_STATUS_CHOICES,
                              default=AmbulanceCallStatus.R.name)

    # call
    call = models.ForeignKey(Call,
                             on_delete=models.CASCADE)

    # ambulance
    ambulance = models.ForeignKey(Ambulance,
                                  on_delete=models.CASCADE)

    # created at
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):

        # publish?
        publish = kwargs.pop('publish', True)

        # remove?
        remove = kwargs.pop('publish', False)

        # changed to ongoing?
        if self.status == AmbulanceCallStatus.O.name:

            # retrieve call
            call = self.call

            if call.status != CallStatus.S.name:

                # change call status to started
                call.status = CallStatus.S.name
                call.save()

        # changed to complete?
        elif self.status == AmbulanceCallStatus.C.name:

            # retrieve call
            call = self.call

            # retrieve all ongoing ambulances
            ongoing_ambulancecalls = call.ambulancecall_set.exclude(status=AmbulanceCallStatus.C.name)

            set_size = len(ongoing_ambulancecalls)
            if (set_size == 0 or
                    (set_size == 1 and ongoing_ambulancecalls[0].ambulance is not self)):

                logger.debug('This is the last ambulance; will end call.')

                # publish first
                self.publish()

                # then change call status to finished
                call.status = CallStatus.E.name
                call.save()

                # prevent publication, already published
                publish = False

            else:

                logger.debug('There are still {} ambulances in this call.'.format(set_size))
                logger.debug(ongoing_ambulancecalls)

                # publish and remove from mqtt
                remove = True

        # changed to declined?
        elif self.status == AmbulanceCallStatus.D.name:

            logger.debug('Ambulance call declined.')

        # changed to suspended?
        elif self.status == AmbulanceCallStatus.S.name:

            logger.debug('Ambulance call suspended.')

        # call super
        super().save(*args, **kwargs,
                     publish=publish,
                     remove=remove)

        # call history save
        copy = AmbulanceCallHistory(status=self.status, call=self.call,
                                    ambulance=self.ambulance, created_at=self.created_at)
        copy.save()

    def publish(self, **kwargs):

        # publish to mqtt
        from mqtt.publish import SingletonPublishClient
        SingletonPublishClient().publish_call_status(self, **kwargs)

    def remove(self):

        # remove from mqtt
        from mqtt.publish import SingletonPublishClient
        SingletonPublishClient().remove_call_status(self)

    class Meta:
        unique_together = ('call', 'ambulance')


# Patient, might be expanded in the future

class Patient(PublishMixin,
              models.Model):
    """
    A model that provides patient fields.
    """

    call = models.ForeignKey(Call,
                             on_delete=models.CASCADE)

    name = models.CharField(max_length=254, default="")
    age = models.IntegerField(null=True)

    def publish(self):

        # publish to mqtt
        from mqtt.publish import SingletonPublishClient
        SingletonPublishClient().publish_call(self.call)


# Location related models

# noinspection PyPep8
class LocationType(Enum):
    b = 'Base'
    a = 'AED'
    i = 'Incident'
    h = 'Hospital'
    w = 'Waypoint'
    o = 'Other'


LocationTypeOrder = [
    LocationType.h,
    LocationType.b,
    LocationType.a,
    LocationType.o,
    LocationType.i,
    LocationType.w
]


class Location(AddressModel,
               UpdatedByModel):

    # location name
    name = models.CharField(max_length=254, blank=True, null=True)

    # location type
    LOCATION_TYPE_CHOICES = \
        [(m.name, m.value) for m in LocationType]
    type = models.CharField(max_length=1,
                            choices=LOCATION_TYPE_CHOICES)

    # location: already in address
    # location = models.PointField(srid=4326, null=True)

    def get_absolute_url(self):
        return reverse('ambulance:location_detail', kwargs={'pk': self.id})

    def __str__(self):
        return "{} @{} ({})".format(self.name, self.location, self.comment)


# Waypoint related models

class WaypointStatus(Enum):
    N = 'Not visited'
    V = 'Visiting'
    D = 'Visited'


class Waypoint(PublishMixin,
               UpdatedByModel):
    # call
    ambulance_call = models.ForeignKey(AmbulanceCall,
                                       on_delete=models.CASCADE)

    # order
    order = models.PositiveIntegerField()

    # status
    WAYPOINT_STATUS_CHOICES = \
        [(m.name, m.value) for m in WaypointStatus]
    status = models.CharField(max_length=1,
                              choices=WAYPOINT_STATUS_CHOICES,
                              default=WaypointStatus.N.name)

    # active
    active = models.BooleanField(default=True)

    # Location
    location = models.ForeignKey(Location,
                                 on_delete=models.CASCADE,
                                 blank=True, null=True)

    def is_active(self):
        return self.active

    def is_not_visited(self):
        return self.status == WaypointStatus.N.name

    def is_visited(self):
        return self.status == WaypointStatus.D.name

    def is_visiting(self):
        return self.status == WaypointStatus.V.name

    def save(self, *args, **kwargs):

        # publish?
        publish = kwargs.pop('publish', False)

        # remove?
        remove = kwargs.pop('remove', False)

        # call super
        super().save(*args, **kwargs,
                     publish=publish,
                     remove=remove)

    def remove(self):
        pass

    def publish(self, **kwargs):

        logger.debug('Will publish')

        # publish to mqtt
        from mqtt.publish import SingletonPublishClient
        SingletonPublishClient().publish_call(self.ambulance_call.call)


# THOSE NEED REVIEWING

class Region(models.Model):
    name = models.CharField(max_length=254, unique=True)
    center = models.PointField(srid=4326, null=True)

    def __str__(self):
        return self.name
