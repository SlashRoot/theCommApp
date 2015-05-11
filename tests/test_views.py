from tests.sample_requests import TYPICAL_TWILIO_REQUEST
from rest_framework.test import APITestCase
from rest_framework.test import APIRequestFactory
from the_comm_app.actions import SideEffect
from the_comm_app.models import PhoneCall
from the_comm_app.views.call_in_progress import AnswerViewSet


class answer_tests(APITestCase):
    
    def test_simple_answer(self):

        # We start with no PhoneCall object.
        self.assertFalse(PhoneCall.objects.exists())

        # But after the view...
        factory = APIRequestFactory()
        request = factory.post('/answer/', TYPICAL_TWILIO_REQUEST)
        response = AnswerViewSet().create(request)

        # ...a call exists.
        self.assertTrue(PhoneCall.objects.exists())

    def test_side_effect_was_caused(self):
        '''
        A Request
        '''

        some_side_effect = SideEffect()
        phone_line = AnswerViewSet()
        phone_line.add_side_effect(some_side_effect)

        request = APIRequestFactory().post('/answer/', TYPICAL_TWILIO_REQUEST)

        # Before handling the response, the Side Effect hasn't started.
        self.assertFalse(some_side_effect.has_started)

        # Dial into the phone line and...
        response = phone_line.create(request)

        # The Side Effect has now started.
        self.assertTrue(some_side_effect.has_started)
