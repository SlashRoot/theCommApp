from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from twilio.rest import TwilioRestClient
from the_comm_app.constants import NOBODY_HOME, INTEGRATE_FEATURES

from the_comm_app.voice.utilities import standardize_call_info
from the_comm_app.call_functions import call_object_from_call_info
from the_comm_app.models import PhoneProvider
from django.views.generic import View

import logging
logger = logging.getLogger(__name__)


class PhoneLine(View):
    '''
    Think of this as a view (ie, you generally pipe a URL to it; it handles Requests and issues Responses).

    Story:
    You pick up the phone and dial a number.
    Somewhere in the world, you are connected to a PhoneLine.

    It may ring a few times and then somebody may pick up.
    It may read you the weather report from Kalamazoo.
    It may just hang up on you.
    '''
    name = "Generic Phone Line"
    runner = None

    voice = None
    language = None

    domain = None
    protocol = None

    features = ()
    greeting_text = "This is a phone line powered by theCommApp.  To change this message, set the greeting method on your phone line class."

    def __init__(self, *args, **kwargs):
        super(PhoneLine, self).__init__(*args, **kwargs)
        self.phase_registry = {'pickup': self.pickup_phase,
                              }

        self.feature_list = []
        for f in self.features:
            self.add_feature(f)

        self.disposition_list = []
        for d in self.disposition:
            self.add_disposition(d)

        if self.nobody_home:
            self.nobody_home_disposition = self.nobody_home(self)

    @property
    def twilio_creds(self):
        return (self.twilio_sid, self.twilio_auth)

    @property
    def client(self):
        # TODO: Multiple providers
        return TwilioRestClient(*self.twilio_creds)

    def add_feature(self, feature_class):
        feature = feature_class(self)
        self.feature_list.append(feature)
        self.add_phases_from_object(feature)
        return feature

    def add_phase(self, name, callable_obj):
        if name in self.phase_registry:
            logger.warning("Overriding %s, which was already registered as phase %s" % (name, self.phase_registry[name]))
        else:
            logger.info("Adding phase %s (%s)" % (name, callable_obj))

        self.phase_registry[name] = callable_obj

    def call_with_runner(self, thing_to_call, runner=None, prefer_runner=False):
        runner = runner or self.runner
        if runner:
            runner(thing_to_call)
        else:
            thing_to_call()

    def say(self, message, voice=None, language=None, **kwargs):
        voice = voice or self.voice
        language = language or self.language
        self.response.say(message, voice=voice, language=language, **kwargs)

    def place_caller_on_hold(self):
        '''
        # TODO: Explain what causes the caller to no longer be on hold.
        '''
        pass

    def get_url(self, phase_method):
        try:
            phase_name = phase_method.call_phase_name
        except AttributeError:
            "%s does not have a phase name." % phase_method

        local_url = reverse(self.name, args=[phase_name])
        full_url = "%s//%s%s" % (self.protocol, self.domain, local_url)
        return full_url

    def greeting(self):
        self.say(self.greeting_text)

    @property
    def from_number(self):
        try:
            return self.number_to_use_for_outgoing_calls
        except AttributeError:
            raise TypeError("Features utilizing outgoing calls require the PhoneLine object to have number_to_use_for_outgoing_calls to be set.")

    @property
    def disposition(self):
        return self.disposition_list

    @disposition.setter
    def disposition(self, disposition_class):
        raise RuntimeError("Disposition setter is currently disabled.")
        self.disposition_list.append(disposition_class(self))

    def add_phases_from_object(self, object_with_phases):
        possible_phases = [a for a in dir(object_with_phases) if not a.startswith('_')]
        for candidate in possible_phases:
            try:
                phase_method = getattr(object_with_phases, candidate)
                phase_name = getattr(object_with_phases, candidate).call_phase_name
                self.add_phase(phase_name, phase_method)
            except AttributeError:
                pass

    def add_disposition(self, disposition_class):
        disposition = disposition_class(self)
        self.disposition_list.append(disposition)
        self.add_phases_from_object(disposition)
        return disposition

    @property
    def nobody_home(self):
        '''
        Called  when a human action (such as answering the call) is expected,
        but not undertaken.

        A common use case is to redirect to voicemail.
        '''
        try:
            nobody_home_method = self.phase_registry[NOBODY_HOME]
            return nobody_home_method
        except KeyError:
            return None

    @nobody_home.setter
    def nobody_home(self, disposition_class):
        self.add_phase(NOBODY_HOME, disposition_class(self))

    def determine_provider(self, request=None):
        # Hard-coding Twilio for now.
        self.provider = PhoneProvider("Twilio")

    def integrate_features(self):
        for feature in self.feature_list:
            feature.start()

    def post(self, request, phase_name="pickup"):
        '''
        The first response to a basic incoming call.  Can take requests from multiple providers.
        '''
        self.protocol = self.protocol or request.build_absolute_uri().split('/')[0]
        self.domain = self.domain or request.build_absolute_uri().split('/')[1]

        try:
            phase_method = self.phase_registry[phase_name]
        except KeyError:
            logger.error("%s does not have a %s phase.  Running pickup." % (self.name, phase_name))
            # Lookie here.  Great place to put a breakpoint.
            phase_method = self.pickup_phase

        self.determine_provider(request)
        self.response = self.provider.get_response_object()

        #Now we need a call object with the appropriate details, regardless of the provider.
        call_info = standardize_call_info(request.POST, self.provider)

        # Identify the call, saving it as a new object if necessary.
        self.call = call_object_from_call_info(call_info)

        phase_result = phase_method()

        if phase_result is INTEGRATE_FEATURES:
            self.integrate_features()

        return HttpResponse(self.response)

    ##########
    # Phases #
    ##########

    def customize_disposition(self, result):
        return result

    def pickup_phase(self):

        if not self.call.ended and self.greeting:
            self.greeting()

        for d in self.disposition_list:
            try:
                result = d.proceed()
                self.customize_disposition(result)

                # TODO: Deal with the case where no feature answers
                # if result is NOBODY_HOME:
                #     self.nobody_home()
            except AttributeError:
                if hasattr(d, 'proceed'):
                    raise
                else:
                    raise TypeError("A Disposition must expose a 'proceed' method.")

    def voicemail_phase(self):
        pass