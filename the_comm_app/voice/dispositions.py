'''
Disposition classes define behavior which will manifest
while the caller waits for a Feature or NOBODY_HOME.
'''

import functools
from django.core.urlresolvers import reverse
from twilio.rest import TwilioRestClient
from the_comm_app.constants import NOBODY_HOME, INTEGRATE_FEATURES
import logging
logger = logging.getLogger(__name__)


def phase_of_call(name):
    def phase_decorator(name, func):
        func.call_phase_name = name
        return func
    return functools.partial(phase_decorator, name)


class VoiceCallDisposition(object):

    def __init__(self, line):
        self.line = line


class ConferenceHoldingPattern(VoiceCallDisposition):

    hold_music = None
    conference_name = None
    digits_to_join = range(10)

    def proceed(self):
        gather = self.line.response.addGather(
            action=self.line.get_url(self.join),
            numDigits=1,
        )

        return gather

    @phase_of_call('conference_caller_join')
    def join(self):

        digits_pressed = self.line.request.POST['Digits']
        if int(digits_pressed) not in self.digits_to_join:
            self.line.say('You have elected not to join the conference.')
            return NOBODY_HOME

        dial = self.line.response.addDial()

        self.conference_name = self.conference_name or self.line.conference_name or self.line.call.call_id
        logger.info("Putting %s into conference %s" % (self.line.request.POST['From'],
                                                       self.conference_name))
        dial.addConference(
            self.conference_name,
            waitUrl=self.hold_music,
            waitMethod="GET",
            record="record-from-start",
        )

        return INTEGRATE_FEATURES


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

    @phase_of_call('voicemail')
    def proceed(self):
        self.line.say(self.prompt)
        self.line.response.record(
            format="audio/mp3",
            transcribe=True,
            )