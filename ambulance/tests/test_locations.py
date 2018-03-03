from django.test import Client

from django.conf import settings

from rest_framework.parsers import JSONParser
from io import BytesIO

from ambulance.models import Location
from ambulance.serializers import LocationSerializer

from emstrack.tests.util import date2iso, point2str, dict2point

from login.tests.setup_data import TestSetup


class TestLocationGetList(TestSetup):

    def test_location_serializer(self):
        # test LocationSerializer
        for h in (self.l1, self.l2, self.l3):
            serializer = LocationSerializer(h)
            result = {
                'id': h.id,
                'name': h.name,
                'type': h.type,
                'number': h.number,
                'street': h.street,
                'unit': h.unit,
                'neighborhood': h.neighborhood,
                'city': h.city,
                'state': h.state,
                'zipcode': h.zipcode,
                'country': h.country,
                'location': point2str(h.location),
                'comment': h.comment,
                'updated_by': h.updated_by.id,
                'updated_on': date2iso(h.updated_on)
            }
            self.assertDictEqual(serializer.data, result)

    def test_location_get_list_viewset(self):
        # instantiate client
        client = Client()

        # login as admin
        client.login(username=settings.MQTT['USERNAME'], password=settings.MQTT['PASSWORD'])

        # retrieve locations
        response = client.get('/api/location/',
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = [LocationSerializer(self.l1).data,
                  LocationSerializer(self.l2).data,
                  LocationSerializer(self.l3).data]
        self.assertCountEqual(result, answer)

        # logout
        client.logout()

        # login as testuser1
        client.login(username='testuser1', password='top_secret')

        # retrieve locations
        response = client.get('/api/location/',
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = [LocationSerializer(self.l1).data,
                  LocationSerializer(self.l2).data,
                  LocationSerializer(self.l3).data]
        self.assertCountEqual(result, answer)

        # logout
        client.logout()

        # login as testuser2
        client.login(username='testuser2', password='very_secret')

        # retrieve locations
        response = client.get('/api/location/',
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = [LocationSerializer(self.l1).data,
                  LocationSerializer(self.l2).data,
                  LocationSerializer(self.l3).data]
        self.assertCountEqual(result, answer)

        # logout
        client.logout()

    def _test_location_get_viewset(self):
        # instantiate client
        client = Client()

        # login as admin
        client.login(username=settings.MQTT['USERNAME'], password=settings.MQTT['PASSWORD'])

        # retrieve any location
        response = client.get('/api/location/{}/'.format(str(self.l1.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = LocationSerializer(Location.objects.get(id=self.l1.id)).data
        self.assertDictEqual(result, answer)

        # retrieve any location
        response = client.get('/api/location/{}/'.format(str(self.l2.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = LocationSerializer(Location.objects.get(id=self.l2.id)).data
        self.assertDictEqual(result, answer)

        # retrieve any location
        response = client.get('/api/location/{}/'.format(str(self.l3.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = LocationSerializer(Location.objects.get(id=self.l3.id)).data
        self.assertDictEqual(result, answer)

        # logout
        client.logout()

        # login as testuser1
        client.login(username='testuser1', password='top_secret')

        # retrieve own's
        response = client.get('/api/location/{}/'.format(str(self.l1.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = LocationSerializer(Location.objects.get(id=self.l1.id)).data
        self.assertDictEqual(result, answer)

        response = client.get('/api/location/{}/'.format(str(self.l2.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = LocationSerializer(Location.objects.get(id=self.l2.id)).data
        self.assertDictEqual(result, answer)

        # retrieve someone else's
        response = client.get('/api/location/{}/'.format(str(self.l3.id)),
                              follow=True)
        self.assertEqual(response.status_code, 404)

        # logout
        client.logout()

        # login as testuser2
        client.login(username='testuser2', password='very_secret')

        # retrieve someone else's
        response = client.get('/api/location/{}/'.format(str(self.l1.id)),
                              follow=True)
        self.assertEqual(response.status_code, 404)

        # retrieve someone else's
        response = client.get('/api/location/{}/'.format(str(self.l2.id)),
                              follow=True)
        self.assertEqual(response.status_code, 404)

        # retrieve someone else's
        response = client.get('/api/location/{}/'.format(str(self.l3.id)),
                              follow=True)
        self.assertEqual(response.status_code, 404)

        # logout
        client.logout()


