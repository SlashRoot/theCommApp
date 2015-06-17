import logging
import time
from the_comm_app.constants import DID_NOT_RUN, FINISHED, NO_ANSWER

logger = logging.getLogger(__name__)


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


class CallBlast(Feature):
    '''
    Place outgoing calls to a bunch of recipients, then, when they pick up, say self.inquiry to them and gather any button presses.
    '''

    slug = "call_blast"
    digits_to_join = range(10)

    phones = ()
    green_phones = ()
    clients = ()

    conference_name = None

    inquiry = ""
    inquiry_addendum = ""

    time_to_wait_for_answer = 0


    def __iter__(self):
        pass
        
    def __unicode__(self):
        return self.name

    def blast_receipt(self):
        digits_pressed = self.line.request.POST['Digits']

        if int(digits_pressed[0]) in self.digits_to_join:
            return self.connect()

    def blaster(self):
        return self.blast()

    def blast(self):

        gather = self.line.response.addGather(
            action=self.line.get_url(self.blast_receipt),
            numDigits=1,
            timeout=30,
        )
        gather.addSay(self.inquiry + self.inquiry_addendum)

    def run(self):
        self.make_calls()
        self.follow_up()

    def make_calls(self):
        for r in self.phones:
            self.line.client.calls.create(
                url=self.line.get_url(self.blaster),
                to=r,
                from_=self.line.from_number
            )

        for r in self.green_phones:
            self.line.client.calls.create(
                url=self.line.get_url(self.connect),
                to=r,
                from_=self.line.from_number
            )

        for r in self.clients:
            self.line.client.calls.create(
                url=self.line.get_url(self.connect),
                to="client:%s" % r,
                from_=self.line.request.POST['From']
            )

    def follow_up(self):
        pass

    def see_if_anyone_answered(self):
        raise NotImplementedError("Standard CallBlast does not yet have a way to determine whether anyone answered.")


class NakedCallBlast(CallBlast):
    '''
    When the recipient picks up, simply connect them, no matter what,
    without preambulatory messages or interaction.
    '''
    pass


class MessageBlast(CallBlast):

    def blast(self):
        pass


class ConferenceBlast(CallBlast):

    slug = "conference_blast"
    conference_name = None

    @property
    def inquiry(self):
        inquiry = self.line.call.announce_caller()

        call_participants = self.line.call.participants.filter(direction="to")
        if call_participants:
            self.inquiry += "Also on the call: "
            voice = "Victor"
            for involvement in call_participants:
                inquiry += " %s, " % str(involvement.person.first_name)
        else:
            voice = "Allison"

        return inquiry

    @inquiry.setter
    def inquiry(self, thing_to_say):
        pass

    @property
    def conference_id(self):
        return self.conference_name or self.line.conference_name or self.line.call.call_id

    def current_participants(self):
        return self.line.client.participants(self.conference_id).list()

    def connect(self):
        self.line.response.addSay("Joining the conference.")
        dial = self.line.response.addDial()

        logger.info("%s joining conference %s" % (self.line.request.POST['To'],
                                                       self.conference_id))
        dial.addConference(self.conference_id)

    def follow_up(self):
        time.sleep(self.time_to_wait_for_answer)
        anybody_home = self.see_if_anyone_answered()
        if not anybody_home:
            self.report(NO_ANSWER)

    def see_if_anyone_answered(self):
        participants = self.current_participants()
        return bool(participants)


class CallMaker(Feature):

    slug = "call_maker"

    @property
    def url(self):
        if not getattr(self, "call_action", None):
            raise ValueError("No URL or call_action have been set for this call maker.  You can either set one or pass one to create_call().")
        else:
            return self.line.get_url(self.call_action)

    def place_call(self, to_phone):
        return self.create_call(to_phone, self.caller_id)

    def create_call(self, to_phone,
                    from_caller_id,
                    url=None,
                    ):
        if not url:
            url = self.url

        return self.line.client.calls.create(
            url=url,
            to=to_phone,
            from_=from_caller_id
        )


class CallMakerFromCallers(CallMaker):

    from_callers = []

    def from_caller_action(self):
        '''
        The action experienced by "from" callers.
        '''
        pass

    def call_action(self):
        pass

    def place_call(self, to_phone):
        from_caller_url = self.line.get_url(self.from_caller_action)
        for caller in self.from_callers:
            self.create_call(to_phone=caller,
                             from_caller_id=self.line.from_number,
                             url=from_caller_url)
