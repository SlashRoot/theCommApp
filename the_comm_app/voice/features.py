from twilio.rest import TwilioRestClient
from the_comm_app.voice.dispositions import phase_of_call
import logging

logger = logging.getLogger(__name__)


class ConnectCallToConference(object):
    '''
    The proces of connection of zero or more calls to an existing call.
    ???
    '''

    def __init__(self, conference, calls_to_connect=None):
        self.conference = conference
        self.calls_to_connect = calls_to_connect

    def connect(self):
        self.conference.receive(self.calls_to_connect)


class Feature(object):
    '''
    1. You call someone.
    2. Some batty but beautiful behavior happens (or at least starts happening).
    3. You get a Response ("Thanks for calling the chocobo farm, etc.")

    This class is step 2.
    '''

    has_started = False
    is_finished = False
    no_go = False

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
            self.line.call_with_runner(self.run)

    def run(self):
        '''
        The main method to override.
        The Feature will not be regarded as finished until is_finished == True.
        '''
        self.is_finished = True


class CallBlast(Feature):
    '''
    Place outgoing calls to a bunch of recipients, with each following the same action.
    '''

    url = "call_blast"
    digits_to_join = range(10)

    phones = ()
    green_phones = ()
    clients = ()

    conference_name = None

    inquiry_addendum = ""


    def __iter__(self):
        pass
        
    def __unicode__(self):
        return self.name

    @property
    def conference_id(self):
        return self.conference_name or self.line.conference_name or self.line.call.call_id


    @phase_of_call("%s__connect" % url)
    def connect(self):
        self.line.response.addSay("Joining the conference.")
        dial = self.line.response.addDial()

        logger.info("%s joining conference %s" % (self.line.request.POST['To'],
                                                       self.conference_id))
        dial.addConference(self.conference_id)

    @phase_of_call("%s__blast_receipt" % url)
    def blast_receipt(self):
        digits_pressed = self.line.request.POST['Digits']

        if int(digits_pressed[0]) in self.digits_to_join:
            return self.connect()

    @phase_of_call(url)
    def blaster(self):
        return self.blast()

    def blast(self):
        inquiry = self.line.call.announce_caller()

        call_participants = self.line.call.participants.filter(direction="to")
        if call_participants:
            inquiry += "Also on the call: "
            voice = "Victor"
            for involvement in call_participants:
                inquiry += " %s, " % str(involvement.person.first_name)
        else:
            voice = "Allison"

        inquiry += self.inquiry_addendum

        gather = self.line.response.addGather(
            action=self.line.get_url(self.blast_receipt),
            numDigits=1,
            timeout=30,
        )
        gather.addSay(inquiry)

    def run(self):

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
