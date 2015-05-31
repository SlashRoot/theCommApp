from twilio.rest import TwilioRestClient


class BlastToText(object):

    sent = False

    def __init__(self,
                 twilio_account_sid,
                 twilio_auth_token,
                 from_number,
                 recipients=None,
                 message=None):
        self.recipients = recipients
        self.message = message
        self.from_number = from_number
        self.client = TwilioRestClient(twilio_account_sid, twilio_auth_token)

    def send(self):
        for r in self.recipients:
            self.client.messages.create(to=r,
                                        from_=self.from_number,
                                        body=self.message
            )