from unittest.case import skip
from httplib2 import Response
from urlparse import parse_qs
from django.core.urlresolvers import reverse
from django.test import TestCase
from tests.examples import ExamplePhoneLine
from tests.sample_requests import TYPICAL_TWILIO_REQUEST
import mock, json, xml

class MultiStepLineIntegrationTest(TestCase):

    def mock_http_request(self, url, method, body=None, headers=None):
        payload_dict = parse_qs(body)
        self.next_url = payload_dict['Url'][0]
        return Response({'status': '200'}), json.dumps({'sid': ExamplePhoneLine.twilio_sid})

    def parse_response(self, response):
        twiml_response = xml.etree.ElementTree.fromstring(response._container[0])
        return twiml_response.getchildren()

    @skip("Jive with INTEGRATE_FEATURES")
    def test_pickup(self):
        pickup_url = reverse(ExamplePhoneLine.name, args=['pickup'])

        with mock.patch("httplib2.Http.request", new=self.mock_http_request):
            self.client.post(pickup_url, TYPICAL_TWILIO_REQUEST)

        with mock.patch("httplib2.Http.request", new=self.mock_http_request):
            blast_response = self.client.post(self.next_url, TYPICAL_TWILIO_REQUEST)
            blast_response_list = self.parse_response(blast_response)
            self.blast_receipt_url = blast_response_list[0].attrib['action']

        with mock.patch("httplib2.Http.request", new=self.mock_http_request):
            response = self.client.post(self.blast_receipt_url, TYPICAL_TWILIO_REQUEST)
            self.fail()

        self.fail()