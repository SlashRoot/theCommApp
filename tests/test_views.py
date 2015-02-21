from django.test import TestCase
from sample_requests import TYPICAL_TWILIO_REQUEST
from rest_framework.test import APITestCase
from rest_framework.test import APIRequestFactory
from the_comm_app.views.call_in_progress import AnswerViewSet


class answer_tests(APITestCase):
    
    def test_simple_answer(self):
        factory = APIRequestFactory()
        request = factory.post('/answer/', TYPICAL_TWILIO_REQUEST)
        r = AnswerViewSet().create(request)
        self.fail()
        
        