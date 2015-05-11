from tests.sample_requests import TYPICAL_TWILIO_REQUEST
from rest_framework.test import APITestCase
from rest_framework.test import APIRequestFactory
from tests.user_logic import PhoneCallAnswer


class answer_tests(APITestCase):
    
    def test_simple_answer(self):
        factory = APIRequestFactory()
        request = factory.post('/answer/', TYPICAL_TWILIO_REQUEST)
        r = PhoneCallAnswer().create(request)
        self.assertEqual(r.status_code, 200)