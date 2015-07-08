from django.test import TestCase
from tests.test_making_calls import SamplePhoneLine
from the_comm_app.sms import SMSReceiver


class TestSmsEndpoint(TestCase):

    def test_receive_basic_sms(self):

        self.phone_line = SamplePhoneLine()
        self.phone_line.add_feature(SMSReceiver)

        # self.phone_line.
        # self.fail()