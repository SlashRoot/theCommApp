from unittest.case import skip
from urlparse import parse_qs
import urlparse
import xml
from django.core.urlresolvers import reverse

from httplib2 import Response
from django.test import TestCase
from django.test.client import RequestFactory
import json
import mock
from tests.sample_requests import TYPICAL_TWILIO_REQUEST
from the_comm_app.call_functions import call_object_from_call_info
from the_comm_app.constants import INTEGRATE_FEATURES, NO_ANSWER
from the_comm_app.models import PhoneProvider
from the_comm_app.plumbing import PhoneLine
from the_comm_app.voice.dispositions import ConferenceHoldingPattern, Voicemail
from the_comm_app.voice.voice_features import Feature, CallBlast, ConferenceBlast
from the_comm_app.voice.utilities import standardize_call_info


class Dispositions(TestCase):

    class TestPhoneLine(PhoneLine):
        twilio_sid = 'some_twilio_sid'
        twilio_auth = 'some_twilio_auth'

    def setUp(self):
        self.mock_calls = 0

    def test_disposition_is_part_of_responses(self):
        factory = RequestFactory()
        request = factory.post('/phone_line/', TYPICAL_TWILIO_REQUEST)
        phone_line = PhoneLine()

        ConferenceHoldingPattern.hold_music = "test_hold_music"
        phone_line.add_disposition(ConferenceHoldingPattern)
        response = phone_line.post(request)
        twiml_response = xml.etree.ElementTree.fromstring(response._container[0])
        dials = twiml_response.findall('Dial')

        conference = dials[0]._children[0]
        hold_music = conference.attrib['waitUrl']


        self.assertEqual(hold_music, "test_hold_music")

    def test_nobody_redirects_to_voicemail(self):
        factory = RequestFactory()
        request = factory.post('/phone_line/', TYPICAL_TWILIO_REQUEST)

        self.phone_line = self.TestPhoneLine()
        self.phone_line.add_disposition(ConferenceHoldingPattern)
        self.phone_line.add_disposition(Voicemail)
        self.phone_line.add_feature(Feature)

        call_info = standardize_call_info(TYPICAL_TWILIO_REQUEST, PhoneProvider('Twilio'))
        self.call = self.phone_line.call = call_object_from_call_info(call_info)

        # Per usual, we'll make a request and they'll get the first greeting.
        response = self.phone_line.post(request)

        def mock_http_request(http_object, url, method, body=None, headers=None):
            self.mock_calls += 1
            payload_dict = parse_qs(body)
            self.assertEqual(url.split('/')[-1].split('.')[0], self.call.call_id)

            # Assert that the URL to which we're directing them for voicemail
            # is in fact the proper voicemail URL.
            voicemail_disposition = self.phone_line.disposition_dict['voicemail']

            new_url = parse_qs(body)['Url'][0]
            voicemail_url = self.phone_line.get_url(voicemail_disposition.proceed)

            self.assertEqual(new_url, voicemail_url)
            return Response({'status': '200'}), json.dumps({'sid': self.phone_line. twilio_sid})


        # So far, nothing new has happened.
        # However, if the feature reports NO_ANSWER,
        # a new update will be made to the call.
        f = self.phone_line.feature_dict.values()[0]

        with mock.patch("httplib2.Http.request", new=mock_http_request):
            f.report(NO_ANSWER)

        # And we verify that the client has in fact been called.
        self.assertEqual(self.mock_calls, 1)

    def test_bad_phase_name_raises_error(self):
        self.phone_line = self.TestPhoneLine()
        factory = RequestFactory()
        request = factory.post('/phone_line/', TYPICAL_TWILIO_REQUEST)

        # If Voicemail is not the disposition for nobody_home, it goes back to pickup by default.

        self.assertRaises(TypeError, self.phone_line.post, request, phase_name="this_method_does_not_exist")


class TestVoiceFeatures(TestCase):

    def setUp(self):
        self.mock_calls = 0
        self.request_bodies = []
        self.request_urls = []

    class TestPhoneLine(PhoneLine):
        twilio_sid = 'some_twilio_sid'
        twilio_auth = 'some_twilio_auth'
        number_to_use_for_outgoing_calls = "+15557779999"

    def place_call_to_line(self, feature):
        self.phone_line.pickup_conclusion = INTEGRATE_FEATURES
        self.blaster = self.phone_line.add_feature(feature)

        request = RequestFactory().post('/answer/', TYPICAL_TWILIO_REQUEST)

        def mock_http_request(http_object, url, method, body=None, headers=None):
            self.mock_calls += 1
            self.request_urls.append(url)
            try:
                rb = parse_qs(body)
            except AttributeError:
                rb = None
            self.request_bodies.append(rb)

            return Response({'status': '200'}), json.dumps({'sid': self.phone_line. twilio_sid, "participants": [
                    {
                        "account_sid": "AC5ef872f6da5a21de157d80997a64bd33",
                        "call_sid": "CA386025c9bf5d6052a1d1ea42b4d16662",
                        "conference_sid": "CFbbe46ff1274e283f7e3ac1df0072ab39",
                        "date_created": "Wed, 18 Aug 2010 20:20:10 +0000",
                        "date_updated": "Wed, 18 Aug 2010 20:20:10 +0000",
                        "end_conference_on_exit": True,
                        "muted": False,
                        "start_conference_on_enter": True,
                        "uri": "/2010-04-01/Accounts/AC5ef872f6da5a21de157d80997a64bd33/Conferences/CFbbe46ff1274e283f7e3ac1df0072ab39/Participants/CA386025c9bf5d6052a1d1ea42b4d16662.json"
                    }]
            },
           )

        # This will cause the side effect to start.
        with mock.patch("httplib2.Http.request", new=mock_http_request):
            self.phone_line.post(request)


    def test_feature_was_caused(self):
        '''
        A Request
        '''
        phone_line = PhoneLine()
        some_feature = phone_line.add_feature(Feature)

        request = RequestFactory().post('/answer/', TYPICAL_TWILIO_REQUEST)

        # Before handling the response, the Side Effect hasn't started.
        self.assertFalse(some_feature.has_started)

        phone_line.pickup_conclusion = INTEGRATE_FEATURES

        # Dial into the phone line and...
        phone_line.post(request)

        # The Side Effect has now started.
        self.assertTrue(some_feature.has_started)

    def test_call_blast_feature(self):
        self.phone_line = self.TestPhoneLine()
        CallBlast.phones = ['+15554443333', '+19998887777']
        self.place_call_to_line(CallBlast)

        for request_dict in self.request_bodies:

            self.assertIn(request_dict['To'][0], self.blaster.phones)
            self.assertEqual(request_dict['From'][0], self.phone_line.from_number)
            self.assertEqual(self.phone_line.get_url(self.blaster.blaster), request_dict['Url'][0])

        # ...and thus both phones have been called.
        self.assertEqual(self.mock_calls, len(CallBlast.phones))

    def test_conference_blast(self):
        self.phone_line = self.TestPhoneLine()
        ConferenceBlast.phones = ['+15554443333', '+19998887777']
        self.place_call_to_line(ConferenceBlast)

        call_info = standardize_call_info(TYPICAL_TWILIO_REQUEST, PhoneProvider("Twilio"))
        self.phone_line.adhere_call(call_info)

        phase_suffix = self.request_bodies[0]['Url'][0].split('/')[-2]
        self.second_phase_blaster = self.phone_line.get_phase_from_name(phase_suffix)

        call_info = standardize_call_info(TYPICAL_TWILIO_REQUEST, provider=PhoneProvider("Twilio"))
        self.phone_line.adhere_call(call_info)

        self.phone_line.adhere_response()

        # There are no verbs yet.
        self.assertEqual(len(self.phone_line.response.verbs), 0)

        self.second_phase_blaster()

        # But now the gather will be there.
        self.assertEqual(len(self.phone_line.response.verbs), 1)

        first_verb = self.phone_line.response.verbs[0]
        self.assertEqual(first_verb.name, "Gather")
        says = first_verb.xml().findall("Say")
        self.assertEqual(says[0].text, self.blaster.inquiry)

    def test_conference_id_included_in_blast_url(self):
        self.phone_line = self.TestPhoneLine()
        self.place_call_to_line(ConferenceBlast)
        url = self.request_bodies[0]['Url'][0]
        parsed = urlparse.urlparse(url)
        q = parsed.query
        self.assertIn(self.phone_line.conference_id, q)