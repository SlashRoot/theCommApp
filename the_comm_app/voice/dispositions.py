'''
Disposition classes define behavior which will manifest
while the caller waits for a Feature or NOBODY_HOME.
'''

import functools
from twilio.rest import TwilioRestClient
from the_comm_app.constants import NO_ANSWER, INTEGRATE_FEATURES
import logging

logger = logging.getLogger(__name__)


class VoiceCallDisposition(object):

    slug = "voicemail"
    url_params = None

    def __init__(self, line):
        self.line = line


class ConferenceHoldingPattern(VoiceCallDisposition):

    slug = "conference_holding_pattern"
    hold_music = None
    conference_name = None
    digits_to_join = range(10)

    def proceed(self):
        dial = self.line.response.addDial()

        dial.addConference(
            self.conference_id,
            waitUrl=self.hold_music,
            waitMethod="GET",
            record="record-from-start",
        )

        return INTEGRATE_FEATURES


    @property
    def conference_id(self):
        return self.conference_name or self.line.conference_id


class Voicemail(VoiceCallDisposition):

    prompt = "Please leave a message."

    def __call__(self):

        try:
            twilio_rest_client = TwilioRestClient(self.line.twilio_sid,  self.line.twilio_auth)
        except AttributeError:
            if hasattr(self.line, 'twilio_sid') and hasattr(self.line, 'twilio_auth'):
                raise
            else:
                raise TypeError('Voicemails must expose API creds. (ie, twilio_sid and twilio_auth')

        if not self.line.call.has_begun():
            voicemail_url = self.line.get_url(self.proceed)
            voicemailer = functools.partial(twilio_rest_client.calls.route, self.line.call.call_id, voicemail_url)

            return self.line.call_with_runner(voicemailer)

        else:
            return False

    def proceed(self):
        self.line.say(self.prompt)
        self.line.response.record(
            format="audio/mp3",
            transcribe=True,
            )