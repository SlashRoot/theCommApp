import json
from urlparse import parse_qs
import xml
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import RequestFactory

from httplib2 import Response as HttpResponse
import mock
from rest_framework.test import APITestCase, APIRequestFactory

from tests.sample_requests import TYPICAL_TWILIO_REQUEST, TYPICAL_TWILIO_VOICEMAIL_REQUEST
from the_comm_app.voice.dispositions import ConferenceHoldingPattern, Voicemail
from the_comm_app.voice.features import ConnectCallToConference
from the_comm_app.call_functions import call_object_from_call_info
from the_comm_app.models import PhoneProvider
from the_comm_app.voice.utilities import standardize_call_info
from the_comm_app.sms import BlastToText
from the_comm_app.plumbing import PhoneLine


class PhoneLineTests(APITestCase):

    def test_basic_answer(self):
        factory = APIRequestFactory()
        request = factory.post('/phone_line/', TYPICAL_TWILIO_REQUEST)
        phone_line = PhoneLine()
        response = phone_line.post(request)
        twiml_response = xml.etree.ElementTree.fromstring(response._container[0])
        says = twiml_response.findall('Say')
        self.assertEqual(1, len(says))
        self.assertEqual(says[0].text, phone_line.response.verbs[0].body)


class SMSRequestTests(TestCase):

    mock_calls = 0

    def setUp(self):
        self.sms_recipients = ['+11111111111', '+12222222222']
        self.sms_message = "Hello World"
        self.sms_from_number = ['+13333333333']
        self.twilio_sid = 'some_twilio_sid'

    def test_text_blaster(self):

        def mock_http_request(http_object, url, method, body=None, headers=None):
            self.mock_calls += 1
            payload_dict = parse_qs(body)
            self.assertIn(payload_dict['To'][0], self.sms_recipients)
            self.assertEqual(payload_dict['Body'][0], self.sms_message)
            self.assertEqual(payload_dict['From'], self.sms_from_number)
            self.assertEqual(url,
                'https://api.twilio.com/2010-04-01/Accounts/some_twilio_sid/Messages.json')
            return HttpResponse({'status': '200'}), json.dumps({'sid': self.twilio_sid})

        text_blaster = BlastToText(self.twilio_sid,
                                   'some_twilio_auth',
                                   recipients=self.sms_recipients,
                                   message=self.sms_message,
                                   from_number=self.sms_from_number)

        with mock.patch("httplib2.Http.request", new=mock_http_request):
            text_blaster.send()

        self.assertEqual(self.mock_calls, len(self.sms_recipients))