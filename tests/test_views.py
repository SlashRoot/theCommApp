from rest_framework.test import APIRequestFactory

from tests.sample_requests import TYPICAL_TWILIO_REQUEST

from the_comm_app.models import PhoneCall
from the_comm_app.plumbing import PhoneLine

from django.test import TestCase


class answer_tests(TestCase):
    
    def test_simple_answer(self):

        # We start with no PhoneCall object.
        self.assertFalse(PhoneCall.objects.exists())

        # But after the view...
        factory = APIRequestFactory()
        request = factory.post('/answer/', TYPICAL_TWILIO_REQUEST)
        response = PhoneLine().post(request)

        # ...a call exists.
        self.assertTrue(PhoneCall.objects.exists())
