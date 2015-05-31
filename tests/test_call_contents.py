from unittest.case import skip
from urlparse import parse_qs
import xml
from django.core.urlresolvers import reverse
from django.http.response import HttpResponse
from httplib2 import Response
from django.test import TestCase
from django.test.client import RequestFactory
import json
import mock
from tests.sample_requests import TYPICAL_TWILIO_REQUEST
from the_comm_app.call_functions import call_object_from_call_info
from the_comm_app.constants import INTEGRATE_FEATURES
from the_comm_app.models import PhoneProvider
from the_comm_app.plumbing import PhoneLine
from the_comm_app.voice.dispositions import ConferenceHoldingPattern, Voicemail
from the_comm_app.voice.features import Feature, CallBlast
from the_comm_app.voice.utilities import standardize_call_info


class Dispositions(TestCase):

    class TestPhoneLine(PhoneLine):
        twilio_sid = 'some_twilio_sid'
        twilio_auth = 'some_twilio_auth'

    def test_disposition_is_part_of_responses(self):
        factory = RequestFactory()
        request = factory.post('/phone_line/', TYPICAL_TWILIO_REQUEST)
        phone_line = PhoneLine()
        phone_line.add_disposition(ConferenceHoldingPattern)
        response = phone_line.post(request)
        twiml_response = xml.etree.ElementTree.fromstring(response._container[0])
        gathers = twiml_response.findall('Gather')

        gather_action = gathers[0].attrib['action']
        phase_url = phone_line.get_url(phone_line.disposition[0].join)

        self.assertEqual(gather_action, phase_url)

    @skip('NOBODY_HOME voicemail business')
    def test_nobody_redirects_to_voicemail(self):
        factory = RequestFactory()
        request = factory.post('/phone_line/', TYPICAL_TWILIO_REQUEST)

        self.phone_line = self.TestPhoneLine()
        self.phone_line.add_disposition(ConferenceHoldingPattern)
        self.phone_line.nobody_home = Voicemail

        call_info = standardize_call_info(TYPICAL_TWILIO_REQUEST, PhoneProvider('Twilio'))
        self.call = self.phone_line.call = call_object_from_call_info(call_info)

        def mock_http_request(http_object, url, method, body=None, headers=None):
            payload_dict = parse_qs(body)
            self.assertEqual(url.split('/')[-1].split('.')[0], self.call.call_id)

            # Assert that the URL to which we're directing them for voicemail
            # is in fact the proper voicemail URL.
            self.assertEqual(parse_qs(body)['Url'][0],
                reverse(self.phone_line.name, args=['voicemail'])
            )
            return Response({'status': '200'}), json.dumps({'sid': self.phone_line. twilio_sid})

        with mock.patch("httplib2.Http.request", new=mock_http_request):
            response = self.phone_line.nobody_home()

    def test_defaults_back_to_pickup(self):
        self.phone_line = self.TestPhoneLine()
        factory = RequestFactory()
        request = factory.post('/phone_line/', TYPICAL_TWILIO_REQUEST)

        # If Voicemail is not the disposition for nobody_home, it goes back to pickup by default.

        default_response = self.phone_line.post(request, phase_name="voicemail")
        twiml_response = xml.etree.ElementTree.fromstring(default_response._container[0])
        says = twiml_response.findall('Say')
        self.assertEqual(1, len(says))
        self.assertEqual(says[0].text, self.phone_line.response.verbs[0].body)

    @skip("Voicemail not done.yyy")
    def test_receive_voicemail(self):
        self.phone_line = self.TestPhoneLine()
        factory = RequestFactory()
        self.phone_line.nobody_home = Voicemail
        request = factory.post('/phone_line/voicemail', TYPICAL_TWILIO_REQUEST)
        response = self.phone_line.post(request, phase_name='voicemail')

        twiml_response = xml.etree.ElementTree.fromstring(response._container[0])

        says = twiml_response.findall('Say')
        records = twiml_response.findall('Record')

        self.assertEqual(says[0].text, Voicemail.prompt)
        self.assertEqual(len(records), 1)


class TestVoiceFeatures(TestCase):

    def setUp(self):
        self.mock_calls = 0

    class TestPhoneLine(PhoneLine):
        twilio_sid = 'some_twilio_sid'
        twilio_auth = 'some_twilio_auth'
        number_to_use_for_outgoing_calls = "+15557779999"

    def test_feature_was_caused(self):
        '''
        A Request
        '''
        phone_line = PhoneLine()
        some_feature = phone_line.add_feature(Feature)

        request = RequestFactory().post('/answer/', TYPICAL_TWILIO_REQUEST)

        # Before handling the response, the Side Effect hasn't started.
        self.assertFalse(some_feature.has_started)

        # Cause pickup to integrate the features.
        pickup = phone_line.pickup_phase

        def new_pickup():
            pickup()
            return INTEGRATE_FEATURES

        phone_line.phase_registry['pickup'] = new_pickup

        # Dial into the phone line and...
        phone_line.post(request)

        # The Side Effect has now started.
        self.assertTrue(some_feature.has_started)

    def test_call_blast_feature(self):
        def mock_http_request(http_object, url, method, body=None, headers=None):
            self.mock_calls += 1

            payload_dict = parse_qs(body)
            self.assertIn(payload_dict['To'][0], self.blaster.recipients)
            self.assertEqual(payload_dict['From'][0], self.phone_line.from_number)
            self.assertEqual(self.phone_line.get_url(self.blaster.blaster), payload_dict['Url'][0])
            return Response({'status': '200'}), json.dumps({'sid': self.phone_line. twilio_sid})

        call_blaster = CallBlast
        call_blaster.recipients = ['+15554443333', '+19998887777']
        self.phone_line = self.TestPhoneLine()
        self.blaster = self.phone_line.add_feature(call_blaster)

        request = RequestFactory().post('/answer/', TYPICAL_TWILIO_REQUEST)

        # This will cause the side effect to start.
        with mock.patch("httplib2.Http.request", new=mock_http_request):
            response = self.phone_line.post(request)
