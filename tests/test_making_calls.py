from httplib2 import Response
from django.test import TestCase
import mock
from the_comm_app.plumbing import PhoneLine
from the_comm_app.voice.features import CallMaker, CallMakerFromCallers
from urlparse import parse_qs
import json


class SamplePhoneLine(PhoneLine):
    twilio_sid = 'some_twilio_sid'
    twilio_auth = 'some_twilio_auth'
    number_to_use_for_outgoing_calls = "+15557779999"


class MakeANewCallTest(TestCase):
    '''
    Tests for logic that creates new calls (ie, calls that aren't encapsulated
    after a dial action)
    '''

    def setUp(self):
        self.mock_calls = 0
        self.request_bodies = []
        super(MakeANewCallTest, self).setUp()

    class SampleCallMaker(CallMaker):
        slug = "sample_call_maker"
        caller_id = ['+12223332233']

    class SampleCallJoiner(CallMakerFromCallers):
        callers = ['+15554443333', '+19998887777']

    def mock_http_request(self, url, method, body=None, headers=None):
            self.mock_calls += 1
            self.request_bodies.append(parse_qs(body))

            return Response({'status': '200'}), json.dumps({'sid': self.phone_line. twilio_sid})

    def test_phone_call_without_action_fails(self):
        self.phone_line = SamplePhoneLine()
        self.phone_line.add_feature(self.SampleCallMaker, default_call_maker=True)
        self.SampleCallMaker.call_action = None
        self.assertRaises(ValueError, self.phone_line.place_call,to_phone="+12229997171")

    def test_phone_call_with_action(self):
        self.phone_line = SamplePhoneLine()
        self.action_called_flag = False

        class CallMakerWithAction(self.SampleCallMaker):

            def call_action(call_maker):
                self.action_called_flag = True

        self.phone_line.add_feature(CallMakerWithAction, default_call_maker=True)

        with mock.patch("httplib2.Http.request", new=self.mock_http_request):
            self.phone_line.place_call(to_phone="+12229997171")

        # We've made just one request.
        self.assertEqual(len(self.request_bodies), 1)

        # Get the URL we told the provider to follow.
        url = self.request_bodies[0]['Url'][0]
        default_call_maker = self.phone_line.call_makers[None]
        self.assertEqual(url,
                         default_call_maker.url
                         )

        # Now let's verify that our sample_call_action is in fact
        # the action followed by the call.
        phase_name = url.split('/')[-2]
        phase_function = self.phone_line.get_phase_from_name(phase_name)

        # For those not keeping active enough score,
        # the flag is still false.
        self.assertFalse(self.action_called_flag)

        # However...
        phase_function()

        # Now it has flipped.
        self.assertTrue(self.action_called_flag)

    # def test_phone_call_to_stranger(self):
    #     self.fail()
