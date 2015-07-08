from collections import OrderedDict
import logging
import random

from django.core.urlresolvers import reverse
from django.http import HttpResponse
from twilio.rest import TwilioRestClient
from django.views.generic import View

from the_comm_app.constants import INTEGRATE_FEATURES, DID_NOT_RUN, FINISHED, NO_ANSWER, ALREADY_RAN
import random
from the_comm_app.voice.utilities import standardize_call_info
from the_comm_app.call_functions import call_object_from_call_info
from the_comm_app.models import PhoneProvider

logger = logging.getLogger(__name__)


phase_registry = {}


class PhoneLine(object):
    """
    Think of this as a view (ie, you generally pipe a URL to it; it handles Requests and issues Responses).

    Story:
    You pick up the phone and dial a number.
    Somewhere in the world, you are connected to a PhoneLine.

    It may ring a few times and then somebody may pick up.
    It may read you the weather report from Kalamazoo.
    It may just hang up on you.
    """
    name = "Generic Phone Line"
    runner = None

    voice = None
    language = None
    provider = None

    domain = None
    protocol = None

    default_call_maker = None
    features = ()
    disposition = ()

    greeting_text = "This is a phone line powered by theCommApp.  To change this message, set the greeting method on your phone line class."

    conference_name = None
    pickup_conclusion = None

    def __init__(self, *args, **kwargs):
        super(PhoneLine, self).__init__(*args, **kwargs)

        self.call_info = {}
        self.call_makers = {}
        if self.default_call_maker:
            self.add_feature(self.default_call_maker, default_call_maker=True)

        self.feature_dict = OrderedDict()
        for f in self.features:
            self.add_feature(f)

        self.spent_dispositions = []
        self.disposition_dict = OrderedDict()
        for d in self.disposition:
            self.add_disposition(d)

    def call_with_runner(self, thing_to_call,
                         runner=None,
                         prefer_async=False,
                         require_async=False):
        runner = runner or self.runner
        if runner:
            runner(thing_to_call)
        else:
            thing_to_call()

    def handle_feature_progress(self, feature):
        if feature.status == NO_ANSWER:
            slug, disposition = self.next_disposition()
            if disposition:
                self.redirect_call(disposition.proceed)
            else:
                return

    # Information

    @property
    def twilio_creds(self):
        return (self.twilio_sid, self.twilio_auth)

    @property
    def client(self):
        # TODO: Multiple providers
        return TwilioRestClient(*self.twilio_creds)

    @property
    def from_number(self):
        try:
            return self.number_to_use_for_outgoing_calls
        except AttributeError:
            raise TypeError("Features utilizing outgoing calls require the PhoneLine object to have number_to_use_for_outgoing_calls to be set.")

    def get_url(self, phase_method):
        call_part = phase_method.__self__
        part_slug = call_part.slug
        phase_name = "%s__%s" % (part_slug, phase_method.__name__)

        if not part_slug in self.disposition_dict.keys() + self.feature_dict.keys():

            raise AttributeError("The method %s of %s has not been added as a phase to phone line %s." % (phase_method.__name__, phase_method.__self__.__class__, self.name))

        local_url = reverse(self.name, args=[phase_name])
        full_url = "%s//%s%s" % (self.protocol, self.domain, local_url)

        if call_part.url_params:
            full_url += "?"
            for k, v in call_part.url_params.items():
                full_url += "%s=%s&" % (k, v)

        return full_url

    def get_phase_from_name(self, phase_name):
        # First, assume the the phase is declared on this call.
        phase_method = getattr(self, phase_name, None)

        if not phase_method:
            try:
                call_part_name, method_name = phase_name.split('__')
            except ValueError:
                raise TypeError("%s does not describe a method on the phone line, nor does it conform to the format for a phase on a phone call part." % phase_name)

            # Check dispositions first.
            call_part = self.disposition_dict.get(call_part_name, None)

            # Then features.
            if not call_part:
                call_part = self.feature_dict[call_part_name]

            if not call_part:
                raise TypeError("%s does not describe a method on the phone line or on any phone call part." % phase_name)

            phase_method = getattr(call_part, method_name)

        return phase_method

    def next_disposition(self):
        slug = disposition = None
        for slug, disposition in self.disposition_dict.items():
            if slug in self.spent_dispositions:
                slug = disposition = None
                continue
            else:
                self.spent_dispositions.append(slug)
                break
        return slug, disposition

    @property
    def conference_id(self):
        return self.conference_name or self.conference_name_from_random_word()

    def conference_name_from_random_word(self):
        word_file = "/usr/share/dict/words"
        words = open(word_file).read().splitlines()
        self.conference_name = random.choice(words)
        return self.conference_name

    # Adherence

    def adhere_call(self, call_info=None):
        call_info = call_info or self.call_info
        self.call = call_object_from_call_info(call_info)
        return self.call

    def adhere_response(self):
        if not self.provider:
            self.adhere_provider()
        self.response = self.provider.get_response_object()
        return self.response

    def adhere_provider(self):
        # Hard-coding Twilio for now.
        self.provider = PhoneProvider("Twilio")
        return self.provider

    def add_feature(self, feature_class, default_call_maker=False):
        feature = feature_class(self)
        self.feature_dict[feature.slug] = feature
        # self.add_phases_from_object(feature)

        if hasattr(feature_class, "place_call"):
            # This is a call maker.

            if default_call_maker:
                feature_key = None
            else:
                feature_key = feature_class.slug
            self.call_makers[feature_key] = feature
            logger.info("Added call maker %s to phone line %s" % (feature_class.slug, self.name))

            if not self.call_makers.get(None):
                logger.warning("Added call maker %s, but there is still not default." % feature_class.slug)

        return feature

    def add_disposition(self, disposition_class):
        disposition = disposition_class(self)
        self.disposition_dict[disposition.slug] = disposition
        # self.add_phases_from_object(disposition)
        return disposition

    def integrate_features(self):
        for feature in self.feature_dict.values():
            feature.start()

    # ACTIONS

    def say(self, message, voice=None, language=None, **kwargs):
        voice = voice or self.voice
        language = language or self.language
        self.response.say(message, voice=voice, language=language, **kwargs)

    def place_caller_on_hold(self):
        '''
        # TODO: Explain what causes the caller to no longer be on hold.
        '''
        pass

    def greeting(self):
        self.say(self.greeting_text)


    ########
    # HTTP #
    ########

    def post(self, request, phase_name="pickup"):
        '''
        The first response to a basic incoming call.  Can take requests from multiple providers.
        '''
        self.protocol = self.protocol or request.build_absolute_uri().split('/')[0]
        self.domain = self.domain or request.build_absolute_uri().split('/')[1]

        if request.GET:
            if request.GET.get('conference_id', None):
                self.conference_name = request.GET['conference_id']

        self.adhere_provider()
        self.adhere_response()

        phase_method = self.get_phase_from_name(phase_name)

        #Now we need a call object with the appropriate details, regardless of the provider.
        call_info = standardize_call_info(request.POST, self.provider)

        # Identify the call, saving it as a new object if necessary.
        self.call = self.adhere_call(call_info)

        phase_result = phase_method()

        if phase_result is INTEGRATE_FEATURES:
            self.integrate_features()

        return HttpResponse(self.response)

    def place_call(self, call_maker=None, *args, **kwargs):
        call_maker = self.call_makers.get(call_maker)

        try:
            call_maker.place_call(*args, **kwargs)
        except AttributeError:
            if not call_maker:
                raise ValueError("This phone line has no default call maker, and no call maker was specified.")
            else:
                raise

    def redirect_call(self, phase_method):
        url = self.get_url(phase_method)
        self.client.calls.update(self.call.call_id, url=url)

    ##########
    # Phases #
    ##########

    @property
    def nobody_home(self):
        '''
        Called  when a human action (such as answering the call) is expected,
        but not undertaken.

        A common use case is to redirect to voicemail.
        '''
        return self.nobody_home_func

    def customize_disposition(self, result):
        return result

    def pickup(self):

        if not self.call.ended and self.greeting:
            self.greeting()

        slug, disposition = self.next_disposition()
        disposition_result = None

        if disposition is None:
            logger.warning("PhoneLine had no dispositions remaining.  That's weird!")
        else:
            try:
                disposition_result = disposition.proceed()
            except AttributeError:
                if hasattr(disposition, 'proceed'):
                    raise
                else:
                    raise TypeError("A Disposition must expose a 'proceed' method.")

        return disposition_result or self.pickup_conclusion


class Feature(object):
    '''
    1. You call someone.
    2. Some batty but beautiful behavior happens (or at least starts happening).
    3. You get a Response ("Thanks for calling the chocobo farm, etc.")

    This class is step 2.
    '''
    # __metaclass__ = RegistryType

    has_started = False
    status = None
    no_go = False
    prefer_async = False
    require_async = False
    slug = "set_this"
    url_params = None
    run_only_once = True

    def __init__(self, line):
        self.line = line

    def __add__(self, name):
        pass

    def __iter__(self):
        raise StopIteration

    def __call__(self):
        return self.start()

    def last_stop_before_vegas(self):
        '''
        A place to decide to set no_go to True.
        '''
        pass

    def start(self):

        if self.has_started and self.run_only_once:
            return ALREADY_RAN

        self.has_started = True

        self.last_stop_before_vegas()

        if not self.no_go:
            return self.line.call_with_runner(self.run,
                                       self.prefer_async,
                                       self.require_async
                                       )
        else:
            self.status = FINISHED
            return DID_NOT_RUN

    def run(self):
        '''
        The main method to override.
        The Feature will not be regarded as finished until is_finished == True.
        '''
        self.status = FINISHED

    def report(self, status=None):
        '''
        Pass information back to the PhoneLine object, optionally changing this Feature's state.
        '''
        if status:
            self.status = status
        self.line.handle_feature_progress(self)

    @property
    def is_finished(self):
        return self.status == FINISHED
