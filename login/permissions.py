import logging

from functools import lru_cache

from ambulance.models import Ambulance
from hospital.models import Hospital

logger = logging.getLogger(__name__)

PERMISSION_CACHE_SIZE = 10


@lru_cache(maxsize=PERMISSION_CACHE_SIZE)
def get_permissions(user):
    # hit the database for permissions
    return Permissions(user)


cache_clear = get_permissions.cache_clear
cache_info = get_permissions.cache_info


class Permissions:
    object_fields = ('ambulance', 'hospital')
    profile_fields = ('ambulances', 'hospitals')
    models = (Ambulance, Hospital)

    def __init__(self, user, **kwargs):

        # override fields
        if 'profile_fields' in kwargs:
            self.profile_fields = kwargs.pop('profile_fields')

        # override fields_id
        if 'object_fields' in kwargs:
            self.object_fields = kwargs.pop('object_fields')

        # override models
        if 'models' in kwargs:
            self.models = kwargs.pop('models')

        # initialize permissions
        self.can_read = {}
        self.can_write = {}
        for profile_field in self.profile_fields:
            # e.g.: self.ambulances = {}
            setattr(self, profile_field, {})
            # e.g.: self.can_read['ambulances'] = {}
            self.can_read[profile_field] = []
            self.can_write[profile_field] = []

        # add equipments
        self.equipments = {}
        self.can_read['equipments'] = []
        self.can_write['equipments'] = []

        # retrieve permissions if not None
        if user is not None:

            if user.is_superuser or user.is_staff:

                # superuser, add all permissions
                for (model, profile_field, object_field) in zip(self.models, self.profile_fields, self.object_fields):
                    # e.g.: objs = group.groupprofile.hospitals.all()
                    objs = model.objects.all()
                    # e.g.: self.hospitals.update({e.hospital_id: {...} for e in Hospitals.objects.all()})
                    permissions = {}
                    equipment_permissions = {}
                    for e in objs:
                        permissions[e.id] = {
                            object_field: e,
                            'can_read': True,
                            'can_write': True
                        }
                        equipment_permissions[e.equipment_holder.id] = {
                            'equipment_holder': e.equipment_holder,
                            'can_read': True,
                            'can_write': True
                        }
                    getattr(self, profile_field).update(permissions)
                    self.equipments.update(equipment_permissions)
                    # getattr(self, profile_field).update({
                    #     e.id: {
                    #         object_field: e,
                    #         'can_read': True,
                    #         'can_write': True
                    #     } for e in objs})
                    # # add equipments
                    # self.equipments.update({
                    #     e.equipment_holder.id: {
                    #         'equipment_holder': e.equipment_holder,
                    #         'can_read': True,
                    #         'can_write': True
                    #     } for e in objs})
                    logger.debug('superuser, {} = {}'.format(profile_field, getattr(self, profile_field)))
                    logger.debug('superuser, {} = {}'.format('equipments', self.equipments))

            else:

                # regular users, loop through groups
                for group in user.groups.all().order_by('groupprofile__priority', '-name'):
                    for (profile_field, object_field) in zip(self.profile_fields, self.object_fields):

                        # e.g.: objs = group.groupambulancepermission_set.all()
                        objs = getattr(group, 'group' + object_field + 'permission_set').all()

                        # e.g.: self.ambulances.update({e.ambulance_id: {...} for e in objs})
                        # getattr(self, profile_field).update({
                        #     getattr(e, object_field + '_id'): {
                        #         object_field: getattr(e, object_field),
                        #         'can_read': e.can_read,
                        #         'can_write': e.can_write
                        #     } for e in objs})
                        # logger.debug('group = {}, {} = {}'.format(group.name, profile_field, getattr(self, profile_field)))
                        # add equipments
                        # self.equipments.update({
                        #     e.id: {
                        #         'equipment_holder': getattr(e, object_field).equipment_holder,
                        #         'can_read': e.can_read,
                        #         'can_write': e.can_write
                        #     } for e in objs})

                        permissions = {}
                        equipment_permissions = {}
                        for e in objs:
                            id = getattr(e, object_field + '_id')
                            obj = getattr(e, object_field)
                            permissions[id] = {
                                object_field: obj,
                                'can_read': e.can_read,
                                'can_write': e.can_write
                            }
                            equipment_permissions[obj.equipment_holder.id] = {
                                'equipment_holder': obj.equipment_holder,
                                'can_read': e.can_read,
                                'can_write': e.can_write
                            }
                        getattr(self, profile_field).update(permissions)
                        self.equipments.update(equipment_permissions)

                # add user permissions
                for (profile_field, object_field) in zip(self.profile_fields, self.object_fields):
                    # e.g.: objs = user.userhospitalpermission_set.all()
                    objs = getattr(user, 'user' + object_field + 'permission_set').all()

                    # e.g.: self.hospitals.update({e.hospital_id: {...} for e in user.profile.hospitals.all()})
                    # getattr(self, profile_field).update({
                    #     getattr(e, object_field + '_id'): {
                    #         object_field: getattr(e, object_field),
                    #         'can_read': e.can_read,
                    #         'can_write': e.can_write
                    #     } for e in objs})
                    # logger.debug('user, {} = {}'.format(profile_field, getattr(self, profile_field)))
                    # add equipments
                    # self.equipments.update({
                    #     e.id: {
                    #         'equipment_holder': getattr(e, object_field).equipment_holder,
                    #         'can_read': e.can_read,
                    #         'can_write': e.can_write
                    #     } for e in objs})

                    permissions = {}
                    equipment_permissions = {}
                    for e in objs:
                        id = getattr(e, object_field + '_id')
                        obj = getattr(e, object_field)
                        permissions[id] = {
                            object_field: obj,
                            'can_read': e.can_read,
                            'can_write': e.can_write
                        }
                        equipment_permissions[obj.equipment_holder.id] = {
                            'equipment_holder': obj.equipment_holder,
                            'can_read': e.can_read,
                            'can_write': e.can_write
                        }
                    getattr(self, profile_field).update(permissions)
                    self.equipments.update(equipment_permissions)

            # build permissions
            for profile_field in self.profile_fields:
                for (id, obj) in getattr(self, profile_field).items():
                    if obj['can_read']:
                        # e.g.: self.can_read['ambulances'].append(obj['id'])
                        self.can_read[profile_field].append(id)
                    if obj['can_write']:
                        # e.g.: self.can_write['ambulances'].append(obj['id'])
                        self.can_write[profile_field].append(id)
                # logger.debug('can_read[{}] = {}'.format(profile_field, self.can_read[profile_field]))
                # logger.debug('can_write[{}] = {}'.format(profile_field, self.can_write[profile_field]))

            # add equipments
            for (id, obj) in self.equipments.items():
                if obj['can_read']:
                    self.can_read['equipments'].append(id)
                if obj['can_write']:
                    self.can_write['equipments'].append(id)

    def check_can_read(self, **kwargs):
        assert len(kwargs) == 1
        (key, id) = kwargs.popitem()
        # logger.debug('key = {}, id = {}'.format(key, id))
        try:
            return id in self.can_read[key + 's']
        except KeyError:
            return False

    def check_can_write(self, **kwargs):
        assert len(kwargs) == 1
        (key, id) = kwargs.popitem()
        try:
            return id in self.can_write[key + 's']
        except KeyError:
            return False

    def get(self, **kwargs):
        assert len(kwargs) == 1
        (k, v) = kwargs.popitem()
        return getattr(self, k + 's')[v]

    def get_permissions(self, profile_field):
        return getattr(self, profile_field)

    def get_can_read(self, profile_field):
        return self.can_read[profile_field]

    def get_can_write(self, profile_field):
        return self.can_write[profile_field]
