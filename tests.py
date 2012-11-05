'''
The comm tests are quite different in a number of ways from the tests in the other apps of the WHAT.
This will be obvious even for the casual reader.

The reason for this stark distinction - in style and substance - speaks to the very nature of this app.
The comm app is about communication - outreach to another party.
This necessaties a venture into the unknown.

It means that we can't always know how the other party will respond.
We can't always know that our response is handled gracefully.
We can't always know what kind of request will even be made.

None of this is terribly new - developers have dealt with foreign APIs, whether or not they were called that - for a long time.
We deal with this situation in a typical and predictable way - by mocking the API calls of the services that we use.

There is some debate about whether or not, as such this necessarily means that our tests have ceased to be one or another kind of test.

Are they unit tests?
Are they TDD tests?
Are they integration tests?

These questions, frankly, are rather sophomoric.

The real questions are:

Do these tests cover the fundamental pieces of logic that are prone to either success or failure?
Do these tests depict a reality which is likely to occur, given the services that we have chosen to use?
Do these tests cause greater ease in developing new features?
Do these tests cause greater likelihood of bug-freedom?

Each test here meets - at least - the following criterion:
It depicts a situation or scenario that some human being may encounter when her desire is to communicate with - or hear from - some other human being.

All of this communication is regulated by electronic media, from the utterly synchronous (ie, a phone call), to the delayed (a voicemail).

Additionally, each situation or scenario needs to be tested in light of several different service providers, each with their own API.
The APIs that the various service providers use betray an underlying philosophy about how (and sometimes why) human communication occurs.

We need to test each demonstrable coherent underlying philosophy.
This is generally not so with the other apps - this is likely the most difficult testing challenge we face in the WHAT.

'''

from .call_functions import call_object_from_call_info, \
    place_conference_call_to_dial_list
from .comm_settings import SLASHROOT_EXPRESSIONS
from .models import PhoneCall, CommunicationInvolvement
from .provider_views import answer, alert_pickup, conference_blast, \
    pickup_connect, voicemail, transcription_handler, handle_hangup
from .sample_requests import *
from .services import find_command_in_tropo_command_list, standardize_call_info, \
    find_command_in_twilio_response
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils.unittest.case import _UnexpectedSuccess
from private import resources
from taggit.models import Tag
from unittest import expectedFailure
from what_apps.contact.models import PhoneProvider, DialList, ContactInfo, \
    PhoneNumber, DialListParticipation
from what_apps.do import config
from what_apps.people import config
from what_apps.people.models import UserProfile, UserInGroup
from what_apps.utility.models import FixedObject
import json
import what_apps.do.config as do_config
import what_apps.mellon.config as mellon_config
import what_apps.people.config as people_config











PHONE_NUMBER_ID_TO_TEST = 2
ANSWERER_NAME = "Jane"
CALLER_NAME = "Joe"

unknown_caller_username = "Joe Test Caller"
unknown_caller_first_name = "Joe"
unknown_caller_last_name = "Test Caller"
        

def set_up_providers(testcase):
    testcase.tropo_provider = PhoneProvider.objects.create(name="Tropo")
    testcase.twilio_provider = PhoneProvider.objects.create(name="Twilio")

def prepare_testcase_for_answer_tests(testcase):
    '''
    Takes a test case and adds proper objects for it to conduct tests about responding to incoming calls.
    Returns the PhoneCall object that is created when the call is answered.
    '''
    do_config.set_up()
    mellon_config.set_up()
    do_config.set_up_privileges()
    
    #Providers
    set_up_providers(testcase)
    
    #The dial list
    testcase.diallist = DialList.objects.create(name="SlashRoot First Dial")
    
    #Twilio response to calls
    testcase.http_response_to_twilio_request = testcase.client.post("/comm/phone/", TYPICAL_TWILIO_REQUEST)
    testcase.twilio_response_object = testcase.http_response_to_twilio_request._container[0]
    
    #Tropo response to calls
    fake_initial_request = FakeRequest(TYPICAL_TROPO_REQUEST)
    testcase.http_response_to_tropo_request = answer(fake_initial_request)
    testcase.tropo_response_dict = json.loads(testcase.http_response_to_tropo_request.content)
    
    testcase.twilio_interpretation_of_conference_id = testcase.twilio_response_object.verbs[1].verbs[0].body
    
    tropo_join_conference_command = find_command_in_tropo_command_list(testcase.tropo_response_dict['tropo'], signal_on="joinConference")
    testcase.tropo_interpretation_of_conference_id = tropo_join_conference_command['on']['next'].split('/')[3] #Turn the list into a dict - we know there's only one conference verb.
    
    testcase.tropo_call_id = PhoneCall.objects.get(call_id = testcase.tropo_interpretation_of_conference_id).id #We need the actual ID of the phone call, and it's not clear from the dict.  This is basically a short cut. 
    testcase.twilio_call_id = PhoneCall.objects.get(call_id = testcase.twilio_interpretation_of_conference_id).id
    
    return testcase.twilio_interpretation_of_conference_id, testcase.tropo_interpretation_of_conference_id

def prepare_testcase_for_outgoing_tests(testcase):
    #First we need to prepare our testcase for the basic answer tests.
    #(If we haven't answered the call yet, there's no way to blast the call out to our members.)
    twilio_conference_id, tropo_conference_id = prepare_testcase_for_answer_tests(testcase)
    
    tr = TYPICAL_TROPO_REQUEST_AFTER_REST #Get the REST request that will instruct us on who to call.
    
    #Before we go further, we need to add the custom parameters that we normally set on a tropo request.
    #(We'll somewhat hackily override these for individual test)
    testcase.tropo_request_json = json.loads(tr) #Load it into JSON
    testcase.tropo_request_json['session']['parameters']['number_to_call'] = PHONE_NUMBER_ID_TO_TEST
    testcase.tropo_request_json['session']['parameters']['call_to_join'] = testcase.tropo_call_id
    testcase.tropo_request_json['session']['parameters']['green_phone'] = False
    testcase.modified_tropo_request = json.dumps(testcase.tropo_request_json)
    
    testcase.tropo_blast_request = FakeRequest(testcase.modified_tropo_request)
    testcase.tropo_blast_response = conference_blast(testcase.tropo_blast_request)
    testcase.tropo_blast_response_dict = json.loads(testcase.tropo_blast_response.content)


def prepare_testcase_for_pickup_tests(testcase):
    '''
    Takes a test case and adds proper objects for it to conduct tests about humans picking up calls.
    '''
    #First we need to prepare our testcase for the basic answer tests.
    #(If we haven't answered the call yet, there's no way our members can pick it up.)
    twilio_conference_id, tropo_conference_id = prepare_testcase_for_answer_tests(testcase)
    
    #We need to have an owner for this phone number; get the object first.
    phone_number_object = PhoneNumber.objects.get_or_create(id = PHONE_NUMBER_ID_TO_TEST)[0]    
    phone_number_object.owner = ContactInfo.objects.create()
    
    #Create the user who owns this phone number.    
    UserProfile.objects.create(contact_info = phone_number_object.owner, user=User.objects.create(username=ANSWERER_NAME, first_name=ANSWERER_NAME))
    phone_number_object.save()
        
    testcase.pickup_alert_request = FakeRequest(TYPICAL_TROPO_PICKUP_ALERT)
    
    #Use the call ID determined from the conference ID (see the answer prepare function above)
    testcase.tropo_pickup_response = alert_pickup(testcase.pickup_alert_request, phone_number_object.id, testcase.tropo_call_id) 
    testcase.tropo_pickup_response_dict = json.loads(testcase.tropo_pickup_response.content)

def teardown_testcase_for_pickup_tests(testcase):
    PhoneNumber.objects.all().delete()
    PhoneCall.objects.all().delete()
    
    
def create_phone_calls(number_of_phone_calls_to_create, from_user=None, to_user=None, from_number=None, to_number=None):
    do_config.set_up()
    mellon_config.set_up()
    do_config.set_up_privileges()
    phone_calls = []
    twilio = PhoneProvider.objects.get_or_create(name="Twilio")[0]
    
    if from_user and from_number:
        raise TypeError('Specify either from_user or from_number - not both.')
    
    if to_user and to_number:
        raise TypeError('Specify either to_user or to_number - not both.')
    
    #From
    
    if from_number:
        pass #We'll just use this.
    elif from_user:
        UserProfile.objects.get_or_create(user=from_user, defaults={'contact_info':ContactInfo.objects.create()})
        from_number = PhoneNumber.objects.get_or_create(owner=from_user.userprofile.contact_info, defaults=dict(number="+15551231234"))[0]        
    else:
        from_number = PhoneNumber.objects.get_or_create(type='mobile', number='+18455551234')[0]
    
    if to_number:
        pass #We'll just use this.
    elif to_user:
        UserProfile.objects.get_or_create(user=to_user, defaults={'contact_info':ContactInfo.objects.create()})
        to_number = PhoneNumber.objects.create(owner=to_user.userprofile.contact_info, number="+15551231234")        
    else:
        to_number = PhoneNumber.objects.get_or_create(type='mobile', number='+18455551234')[0]
    
    number_of_existing_calls = PhoneCall.objects.count()
    
    for x in range(number_of_existing_calls+1, number_of_existing_calls+number_of_phone_calls_to_create+1):
        phone_call = PhoneCall.objects.create(service=twilio, call_id=x, from_number=from_number, to_number=to_number)
        phone_calls.append(phone_call)
        
        if from_user:
            CommunicationInvolvement.objects.create(communication=phone_call, person=from_user, direction="from")
        if to_user:
            CommunicationInvolvement.objects.create(communication=phone_call, person=to_user, direction="to")
        
    return phone_calls


class FakeRequest(object):
    '''
    Fairly ridiculous object mocking a request.
    
    We can't use the HttpRequest object because we can't set raw_post_data.
    '''
    POST = {}
    raw_post_data = ""
    method = "POST"  # Will it always be? TODO: Clarify.
    
    def __init__(self, data):
        '''
        More bad hacking.  If data is a dict, make it POST.  If it's a string, make it raw_post_data.
        '''
        if type(data).__name__ == "dict":
            self.POST = data
        else:
            self.raw_post_data = data
            
        

class IncomingCallInformationHandling(TestCase):
    def setUp(self):
        do_config.set_up()
        mellon_config.set_up()
        do_config.set_up_privileges()
        
        self.tropo_provider = PhoneProvider.objects.create(name="Tropo")
        self.twilio_provider = PhoneProvider.objects.create(name="Twilio")
        
        self.diallist = DialList.objects.create(name="test_dial_list")
    
    def test_turn_twilio_request_into_phone_call_object(self):
        '''
        Tests that the call_from_post function takes a typical twilio request object and returns a PhoneCall object.
        '''
        fake_request = FakeRequest(TYPICAL_TWILIO_REQUEST)
        call_info = standardize_call_info(fake_request, self.twilio_provider)
        self.assertIsInstance(call_object_from_call_info(call_info), PhoneCall)
    
    def test_turn_tropo_request_into_phone_call_object(self):
        '''
        Same as above but for tropo.
        '''
        fake_request = FakeRequest(TYPICAL_TROPO_REQUEST)
        call_info = standardize_call_info(fake_request, self.tropo_provider)
        self.assertIsInstance(call_object_from_call_info(call_info), PhoneCall)
        

class CallerInitialExperience(TestCase):
    def setUp(self):
        prepare_testcase_for_answer_tests(self)

    def test_twilio_greeting(self):
        '''
    Tests that the greeting is equal to the say command
        '''
        self.assertEqual(self.twilio_response_object.verbs[0].name, 'Say')
        self.assertEqual(self.twilio_response_object.verbs[0].body, SLASHROOT_EXPRESSIONS['public_greeting'])
        
    def test_twilio_answer_second_command_dial(self):
        '''
        Test that the second verb in the response is "Dial"
        '''
        self.assertEqual(self.twilio_response_object.verbs[1].name, "Dial")
        
    def test_twilio_answer_dial_into_conference(self):
        self.assertEqual(self.twilio_response_object.verbs[1].verbs[0].name, "Conference")
    
    def test_tropo_greeting(self):
        commands_list = self.tropo_response_dict['tropo']
        first_command = commands_list[0]
        self.assertEqual(first_command.items()[0][0], 'say') #This is in fact a say command.
        self.assertEqual(first_command.items()[0][1]['value'], SLASHROOT_EXPRESSIONS['public_greeting']) #The say expression is the appropriate one for an unknown caller.
    
    @expectedFailure
    def test_twilio_hold_music(self):
        self.fail()
            
    def test_tropo_hold_music(self):
        commands_list = self.tropo_response_dict['tropo']
        command = find_command_in_tropo_command_list(commands_list, command_name="say", occurance=1)
        self.assertTrue('mp3' in command['say']['value'], msg="The say command for hold music was not an mp3 file.")
        
    @expectedFailure
    def test_twilio_hold_music_allows_stop_signal(self):
        self.fail()
            
    def test_tropo_hold_music_allows_stop_signal(self):
        '''
        That the hold music does allow itself to be interuppted by the "joinConference" signal.
        '''
        commands_list = self.tropo_response_dict['tropo']
        command = find_command_in_tropo_command_list(commands_list, signal_on='joinConference')
        
        self.assertTrue(command) #If the command exists, we're good for this test.
    
    @expectedFailure
    def test_twilio_join_conference(self):
        self.fail()
        
    def test_tropo_join_conference(self):
        '''
        That the method to which users are directed does in fact result in the conference being joined.
        '''
        commands_list = self.tropo_response_dict['tropo']
        command = find_command_in_tropo_command_list(commands_list, signal_on='joinConference')
        
        url = command['on']['next']
        response_to_conference_join = self.client.get(url)
        response_commands_json = response_to_conference_join.content
        response_commands_dict = json.loads(response_commands_json)
        response_commands_list = response_commands_dict['tropo']
        command_to_join_conference = find_command_in_tropo_command_list(response_commands_list, command_name="conference")
        command_to_join_conference['conference']['id']
        
        self.assertTrue(command_to_join_conference['conference']['id'] in url, "The join conference function did not cause the caller to join the conference specified in the url")
        
    def test_tropo_record_command_is_issued(self):
        commands_list = self.tropo_response_dict['tropo']
        command = find_command_in_tropo_command_list(commands_list, signal_on='joinConference')
        
        url = command['on']['next']
        response_to_conference_join = self.client.get(url)
        response_commands_json = response_to_conference_join.content
        response_commands_dict = json.loads(response_commands_json)
        response_commands_list = response_commands_dict['tropo']
        command_to_join_conference = find_command_in_tropo_command_list(response_commands_list, command_name="startRecording")
        self.assertTrue(command_to_join_conference)  
    
    @expectedFailure    
    def test_twilio_record_command_is_issued(self):
        #TODO: This test previously looked for the command in the wrong place.
        #The command now appears in our response when an answerer joins a conference, not in our response when a caller reaches us.
        #This is so that we no longer record hold music.
        try:
            record_command_value = self.twilio_response_object.verbs[1].attrs['record']
            self.assertEqual(record_command_value, True, msg="The record command was issued, but was not set to True.")
        except KeyError:    
            self.fail()("record was not in the dictionary")        
        
        
class CallBlastsToPotentialPickerUppers(TestCase):
    '''
    Test outgoing calls placed as transfers.  IE, when someone calls, the system places outgoing calls to the people who might answer.
    '''
    def setUp(self):
        prepare_testcase_for_outgoing_tests(self)
        
        self.dial_list = DialList.objects.create(name='test_dial_list')
        DialListParticipation.objects.create(number=PhoneNumber.objects.all()[0], list=self.dial_list)
        DialListParticipation.objects.create(number=PhoneNumber.objects.all()[1], list=self.dial_list)
    
    @expectedFailure
    def test_that_twilio_call_is_placed_from_blast_functions(self):
        self.fail()
            
    def test_that_tropo_call_is_placed_from_blast_function(self):
        '''
        Tests that an outgoing call request is properly placed in response to a tropo rest request to our outgoing call app. 
        '''
        commands_list = self.tropo_blast_response_dict['tropo']
        command = find_command_in_tropo_command_list(commands_list, command_name="call")
        self.assertTrue(command)
    
    @expectedFailure
    def test_that_twilio_alert_pickup_is_called_on_success(self):
        self.fail()
                
    def test_that_tropo_alert_pickup_is_called_on_success(self):
        '''
        wtf is with this empty ass doc string! RACHEL!
        '''
        commands_list = self.tropo_blast_response_dict['tropo']
        
        #Iterate through and figure out which one is the command that happens for the continue signal.
        for command in commands_list:
            try:
                if command['on']['event'] == "continue": #Is this the continue command?
                    #If so, we're looking for the 'next' value for this same entry.
                    actual_url = command['on']['next'] #This is the actual URL that the client is handed; we'll test this against our expected url.
                    break #We found it.  Move on.
            except KeyError:
                continue #Nothing here.  Try the next entry.
        
        #Now we'll find the proper url.
        id_of_number_to_call = self.tropo_request_json['session']['parameters']['number_to_call']
        id_of_call_to_join = self.tropo_call_id
        
        proper_url = '/comm/alert_pickup/%s/%s/' % (str(id_of_number_to_call), str(id_of_call_to_join)) #Found it! Ready to compare.
        
        self.assertEqual(actual_url, proper_url, "The pickup alert was not triggered upon successful pickup or it was directed at the wrong URL.")
    
    @expectedFailure
    def test_twilio_green_phone_gets_confirmation_bypass(self):
        self.fail()
    
    def test_tropo_green_phone_gets_confirmation_bypass(self):
        '''
        That phones marked house_phone qualify for a confirmation bypass.  This does not test that the confirmation bypass actual does anything.
        '''
        modified_tropo_request_dict = json.loads(self.modified_tropo_request) #Grab the JSON request as a dict.
        modified_tropo_request_dict['session']['parameters']['green_phone'] = True
        tropo_request_dict_with_house_phone = json.dumps(modified_tropo_request_dict)
        
        green_outgoing_call_request = FakeRequest(tropo_request_dict_with_house_phone)
        green_tropo_blast_response = conference_blast(green_outgoing_call_request)
        green_tropo_blast_response_dict = json.loads(green_tropo_blast_response.content)
        
        commands_list = green_tropo_blast_response_dict['tropo']
        
        #Iterate through and figure out which one is the command that happens for the continue signal.
        for command in commands_list:
            try:
                if command['on']['event'] == "continue": #Is this the continue command?
                    #If so, we're looking for the 'next' value for this same entry.
                    actual_url = command['on']['next'] #This is the actual URL that the client is handed; we'll test this against our expected url.
                    break #We found it.  Move on.
            except KeyError:
                continue #Nothing here.  Try the next entry.
                    
        self.assertTrue('pickup_connect_auto' in actual_url)
    
    @expectedFailure
    def test_twilio_conference_call_to_dial_list(self):
        self.fail()    
        
    def test_tropo_conference_call_to_dial_list(self):
        '''
        The call is forwarded to the dial list via Tropo. 
        '''
        success = place_conference_call_to_dial_list(self.tropo_call_id, self.dial_list.id)
        self.assertTrue(success)

        
class PickingUpTheCall(TestCase):
    '''
    The call is blasted out to the potential answerers; now they pick it up.
    '''
    def setUp(self):
        prepare_testcase_for_pickup_tests(self)
        
    def tearDown(self):
        teardown_testcase_for_pickup_tests(self)
        
    @expectedFailure
    def test_twilio_pickup_call_from_unknown_caller_200(self):
        self.fail()
        
    def test_tropo_pickup_call_from_unknown_caller_200(self):
        self.assertEqual(self.tropo_pickup_response.status_code, 200)
    
    def test_twilio_pickup_call__first_answerer_bypass_from_unknown_caller(self):
        phone_call = PhoneCall.objects.get(call_id = self.twilio_interpretation_of_conference_id)
        number_to_call = PhoneNumber.objects.filter(owner__isnull=False)[0]
        
        phone_call.participants.all().delete()
        
        self.client.post('/comm/pickup_connect_auto/%s/%s/' % (number_to_call.id, phone_call.id), TYPICAL_TWILIO_PICKUP_BYPASS_REQUEST )
                
    def test_tropo_pickup_call_from_unknown_caller(self):
        '''
        That the appropriate phrase is expressed to someone who picks up a call from an unknown caller.
        '''
        commands_list = self.tropo_pickup_response_dict['tropo']
        first_command = commands_list[0]
        self.assertEqual(first_command.items()[0][0], 'ask') #This is in fact a say command.
        what_we_told_them = what_we_told_them = first_command.items()[0][1]['say']['value']
        self.assertEqual(what_we_told_them, SLASHROOT_EXPRESSIONS['unknown_caller']) #The say expression is the appropriate one for an unknown caller.
    
    @expectedFailure
    def test_twilio_pickup_call_from_known_caller(self):
        self.fail()
            
    def test_tropo_pickup_call_from_known_caller(self):
        #Get the phone number that just called.
        tropo_phone_call = PhoneCall.objects.filter(service = self.tropo_provider)[0] #TODO: Separate logic from other tests.
        tropo_phone_call.from_number.owner = ContactInfo.objects.create()
        
        #Create the user who owns this phone number.
        UserProfile.objects.create(contact_info = tropo_phone_call.from_number.owner, user=User.objects.create(username=unknown_caller_username, first_name=unknown_caller_first_name, last_name=unknown_caller_last_name))
        tropo_phone_call.from_number.save()
        
        #We're about to delete this call, so let's preserve the phone number id for later.
        from_number_id = tropo_phone_call.from_number.id
        
        #Delete all the calls in the system so far.
        PhoneCall.objects.all().delete()
        
        #Now they are calling again.
        fake_initial_request = FakeRequest(TYPICAL_TROPO_REQUEST)
        new_http_response_to_tropo_request = answer(fake_initial_request)
        new_call_id = PhoneCall.objects.all()[0].id
    
        self.tropo_pickup_response_known_caller = alert_pickup(self.pickup_alert_request, from_number_id, new_call_id)
        self.tropo_pickup_response_known_caller_dict = json.loads(self.tropo_pickup_response_known_caller.content)
        
        commands_list = self.tropo_pickup_response_known_caller_dict['tropo']
        first_command = commands_list[0]
        self.assertEqual(first_command.items()[0][0], 'ask') #This is in fact an ask command.
        what_we_told_them = str(first_command.items()[0][1]['say']['value'])
        what_we_tried_to_tell_them = 'Call from %s %s. ' % (unknown_caller_first_name, unknown_caller_last_name)
        self.assertEqual(what_we_told_them, what_we_tried_to_tell_them ) #The say expression is the appropriate one for an unknown caller.
        
    @expectedFailure
    def test_call_from_known_caller_does_not_list_original_caller_as_participant(self):
        '''
        The original caller is instantiated as a call participant, and all call participants are listed, ie "Also on the call, George!"
        This tests that the original caller is omitted in the list of participants.
        '''
        self.fail()
    
    @expectedFailure
    def test_twilio_pickup_call_with_no_other_participants(self):
        self.fail()
        
    def test_tropo_pickup_call_with_no_other_participants(self):
        '''
        That a call with no other participants doesn't list any participants.
        '''
        commands_list = self.tropo_pickup_response_dict['tropo']
        self.assertFalse({u'say': {u'value': SLASHROOT_EXPRESSIONS['participants_list_phrase']}} in commands_list, msg="Even though there were no call participants, the call lists the participants.")
    
    @expectedFailure
    def test_twilio_pickup_call_with_other_partcipations(self):
        self.fail()
        
    def test_tropo_pickup_call_with_other_participants(self):
        '''
        Several phases to this test:
        1) Indicate that an answerer wants to pick up an existing call.
        2) Verify that they are connected properly and that a CommunicationInvolvement object is created pursuant to their participation.
        3) Initiate *another* blast call and see if the participant from steps 1 and 2 is properly indicated to the new answerer.
        '''
        call = PhoneCall.objects.get(id=self.tropo_call_id)
        
        #Joe the test caller returns.      
        call.from_number.owner = ContactInfo.objects.create()
        UserProfile.objects.create(contact_info = call.from_number.owner, user=User.objects.create(username=CALLER_NAME, first_name=CALLER_NAME))
        call.from_number.save()
        
        connect_response = pickup_connect(FakeRequest(TYPICAL_TROPO_RESULT_REQUEST), PHONE_NUMBER_ID_TO_TEST, call.id)
        self.assertTrue(CommunicationInvolvement.objects.count(), "No call participants were saved.")
        
        commands_list = json.loads(connect_response.content)['tropo']
        conference_command = find_command_in_tropo_command_list(commands_list, command_name="conference")
        self.assertEqual(conference_command['conference']['id'], call.call_id, msg="The answerer was not connected to the proper conference.")
        
        another_pickup_response = alert_pickup(self.pickup_alert_request, PHONE_NUMBER_ID_TO_TEST, call.id)
        answerer_commands = json.loads(another_pickup_response.content)['tropo']
        
        what_we_hope_they_heard = "Call from %s. %s:  %s, " % (CALLER_NAME, SLASHROOT_EXPRESSIONS['participants_list_phrase'], ANSWERER_NAME)
        what_they_actually_heard = str(answerer_commands[0]['ask']['say']['value'])
        
        self.assertEqual(what_we_hope_they_heard, what_they_actually_heard, "The answerer of the call was not told who has already picked up the call.")

    @expectedFailure
    def test_twilio_additional_answerers_are_listed(self):
        self.fail()
        
    def test_tropo_additional_answerers_are_listed(self):
        '''
        Additional current callers, rather than "you are the first," are listed properly.
        '''
        call = PhoneCall.objects.get(id=self.tropo_call_id)
        answerers_heretofore = call.participants.count()
        self.assertEqual(answerers_heretofore, 0, msg="There were already answerers before we even picked up.")
        
        connect_response = pickup_connect(FakeRequest(TYPICAL_TROPO_RESULT_REQUEST), PHONE_NUMBER_ID_TO_TEST, self.tropo_call_id)
        answerers_now = call.participants.count()
        self.assertEqual(answerers_now, 1, msg="There was not 1 answerer after we picked up.")
        
        #We need a new number to pick up the phone this time.
        new_number = PhoneNumber.objects.create(number="123-456-1234")
        new_number.owner = ContactInfo.objects.create()
        UserProfile.objects.create(contact_info = new_number.owner, user=User.objects.create(username='does not matter', first_name='does not matter'))
        new_number.save()
        
        #Now let's try again, telling the pickup connector that there were zero answerers up until now.  We should hear about that most recent one there.
        connect_response = pickup_connect(FakeRequest(TYPICAL_TROPO_RESULT_REQUEST), new_number.id, self.tropo_call_id)
        connect_response_dict = json.loads(connect_response.content)
        commands_list = connect_response_dict['tropo']
        connect_say_command = find_command_in_tropo_command_list(commands_list, command_name="say")
        self.assertEqual(connect_say_command['say']['value'], 'Connected. Also on the call:%s,' % ANSWERER_NAME)
    
    @expectedFailure
    def test_twilio_confirmation_bypass_is_effective(self):
        self.fail()
        
    def test_tropo_confirmation_bypass_is_effective(self):
        '''
        That calls which are directed to bypass the confirmation in fact do so.
        '''
        call = PhoneCall.objects.get(id=self.tropo_call_id)

        #Send it a blank request but with connect_regardless.  It will... yep, connect regardless.
        connect_response = pickup_connect(FakeRequest({}), PHONE_NUMBER_ID_TO_TEST, self.tropo_call_id, connect_regardless=True)
        connect_response_dict = json.loads(connect_response.content)
        commands_list = connect_response_dict['tropo']
        connect_say_command = find_command_in_tropo_command_list(commands_list, command_name="say")
        self.assertEqual(connect_say_command['say']['value'], 'Connected. %s%s' % (SLASHROOT_EXPRESSIONS['unknown_caller'],SLASHROOT_EXPRESSIONS['first_answerer_alert']))
    
    @expectedFailure
    def test_twilio_first_answerer_alert(self):
        self.fail()
        
    def test_tropo_first_answerer_alert(self):
        '''
        That the first answerer is told that they are the first answerer
        '''
        call = PhoneCall.objects.get(id=self.tropo_call_id)
        answerers_heretofore = call.participants.count()
        self.assertEqual(answerers_heretofore, 0, msg="There were already answerers before we even picked up.")
        
        connect_response = pickup_connect(FakeRequest(TYPICAL_TROPO_RESULT_REQUEST), PHONE_NUMBER_ID_TO_TEST, self.tropo_call_id)
        connect_response_dict = json.loads(connect_response.content)
        command_list = connect_response_dict['tropo']
        say_command = find_command_in_tropo_command_list(command_list, command_name="say")
        self.assertEqual(say_command['say']['value'], 'Connected. %s' % SLASHROOT_EXPRESSIONS['first_answerer_alert'])
    
    @expectedFailure
    def test_twilio_conference_connection_occurs(self):
        self.fail()
    
    def test_tropo_conference_connection_occurs(self):
        '''
        The proper signal is sent to the original caller so that they get dumped into the conference.
        '''
        call_id = self.tropo_call_id
        call = PhoneCall.objects.get(id=call_id)
        
        connect_response = pickup_connect(FakeRequest(TYPICAL_TROPO_RESULT_REQUEST), PHONE_NUMBER_ID_TO_TEST, call_id)
        commands_list = json.loads(connect_response.content)['tropo']
        
        
        conference_command = find_command_in_tropo_command_list(commands_list, command_name="conference")
        conference_id = conference_command['conference']['id']
        self.assertEqual(conference_id, call.call_id, msg="The answerer was not connected to the same call as the caller.")
    
    @expectedFailure
    def test_twilio_connecting_to_conference_generates_involvement_object(self):
        self.fail()
        
    def test_tropo_connecting_to_conference_generates_involvement_object(self):
        call_id = self.tropo_call_id
        call = PhoneCall.objects.get(id=call_id)
        phone_number_object = PhoneNumber.objects.get(id=PHONE_NUMBER_ID_TO_TEST)
        phone_number_user = phone_number_object.owner.userprofile.user
        
        connect_response = pickup_connect(FakeRequest(TYPICAL_TROPO_RESULT_REQUEST), PHONE_NUMBER_ID_TO_TEST, call_id)
        self.assertTrue(CommunicationInvolvement.objects.filter(person=phone_number_user).exists())

class HangupTests(TestCase):
    def setUp(self):
        prepare_testcase_for_pickup_tests(self)
    
    @expectedFailure
    def test_twilio_hangup_response_for_unknown_caller(self):
        self.fail()
        
    def test_tropo_hangup_response_for_unknown_caller(self):
        hangup_request = FakeRequest(TYPICAL_TROPO_AFTER_HANGUP_REQUEST)
        call = PhoneCall.objects.get(id=self.tropo_call_id)
        self.assertFalse(call.ended, msg="The call had already ended before the caller hung up.")
        hangup_response = handle_hangup(hangup_request, call.call_id, call.from_number.id)
        call = PhoneCall.objects.get(id=self.tropo_call_id)
        self.assertTrue(call.ended, msg="The call handn't ended even after the caller hung up.")
    
    @expectedFailure
    def test_twilio_hangup_response_for_known_answerer(self):
        self.fail()
        
    def test_tropo_hangup_response_for_known_answerer(self):
        call = PhoneCall.objects.get(id=self.tropo_call_id)
        answerers_heretofore = call.participants.count()
        self.assertEqual(answerers_heretofore, 0, msg="There were already answerers before we even picked up.")
        
        connect_response = pickup_connect(FakeRequest(TYPICAL_TROPO_RESULT_REQUEST), PHONE_NUMBER_ID_TO_TEST, self.tropo_call_id)
        answerers_now = call.participants.count()
        self.assertEqual(answerers_now, 1, msg="There was not 1 answerer after we picked up.")
        
        involvement = call.participants.get(person__userprofile__contact_info__phone_numbers__id=PHONE_NUMBER_ID_TO_TEST)
        self.assertFalse(involvement.destroyed)
        
        hangup_request = FakeRequest(TYPICAL_TROPO_AFTER_HANGUP_REQUEST)
        hangup_response = handle_hangup(hangup_request, call.call_id, PHONE_NUMBER_ID_TO_TEST)
        involvement = call.participants.get(person__userprofile__contact_info__phone_numbers__id=PHONE_NUMBER_ID_TO_TEST)
        self.assertTrue(involvement.destroyed)
    
class NobodyPickedUp(TestCase):
    def setUp(self):
        prepare_testcase_for_answer_tests(self)
    
    def test_tropo_voicemail_on_timeout(self):
        '''
        We're not actually going to test the delay, as this will introduce a 60 second delay to the test runner.
        We will simply test that the delayed function the proper signal sends them to voicemail.
        '''
        commands_list = self.tropo_response_dict['tropo']
        voicemail_command = find_command_in_tropo_command_list(commands_list, signal_on="goToVoiceMail")
        self.assertTrue(voicemail_command)
        
    ###TODO: Test the twisted bit that makes the REST call to Twilio, yanking them into voicemail.

    def test_twilio_voicemail_is_taken(self):
        twilio_response = self.client.post('/comm/voicemail/', TYPICAL_TWILIO_VOICEMAIL_REQUEST)
        self.assertEqual(twilio_response.status_code, 200)
        
        say_command = find_command_in_twilio_response(twilio_response, command_name='Say')
        self.assertTrue(say_command)
        
        record_command = find_command_in_twilio_response(twilio_response, command_name='Record')
        self.assertTrue(record_command)

    def test_tropo_voicemail_is_taken(self):
        '''
        That upon being sent to the voicemail function, they are in fact handed the voicemail prompt and a chance to record a voicemail.
        '''
        response_to_tropo_voicemail_request_json = voicemail(FakeRequest(TYPICAL_TROPO_VOICEMAIL_REQUEST))
        response_to_tropo_voicemail_request_dict = json.loads(response_to_tropo_voicemail_request_json.content)
        
        #Now that we have the URL, we need to post to that URL.
        command_list = response_to_tropo_voicemail_request_dict['tropo']
        record_command = find_command_in_tropo_command_list(command_list, command_name="record")
        self.assertTrue(record_command)
    
    @expectedFailure
    def test_twilio_task_to_resolve_voicemail_is_tagged_voicemail(self):
        self.fail()
            
    def test_tropo_task_to_resolve_voicemail_is_tagged_voicemail(self):
        response_to_tropo_voicemail_request_json = voicemail(FakeRequest(TYPICAL_TROPO_VOICEMAIL_REQUEST))
        response_to_tropo_voicemail_request_dict = json.loads(response_to_tropo_voicemail_request_json.content)
        
        call = PhoneCall.objects.get(id=self.tropo_call_id)
        vm_tag = Tag.objects.get(name="voicemail")
        self.assertTrue(vm_tag in call.resolve_task().tags.all(), msg="The task to resolve this call was not tagged 'voicemail' despite it being sent to the voicemail view.")
        
        self.assertTrue(call.voicemail(), msg="The conveinence method .voicemail() did not return a PhoneCallRecording object despite sending the call to the voicemail view.")


class CallInToConferenceTests(TestCase):
    @expectedFailure
    def test_caller_has_authority_to_list_conferences(self):
        self.fail()
    
    @expectedFailure
    def test_proper_list_of_current_conferences(self):
        self.fail()
    
    @expectedFailure
    def test_list_of_conference_participants(self):
        self.fail()
    
    @expectedFailure
    def test_ask_caller_which_conference_to_join(self):
        self.fail()

class CallDocumentationTests(TestCase):
    def setUp(self):
        prepare_testcase_for_answer_tests(self)
    
    def test_twilio_that_voicemail_recording_is_saved(self):
        twilio_voicemail_response = self.client.post('/comm/voicemail/', TYPICAL_TWILIO_VOICEMAIL_REQUEST)
        self.assertEqual(twilio_voicemail_response.status_code, 200)
        
        record_command = find_command_in_twilio_response(twilio_voicemail_response, command_name='Record')
        url = record_command.attrs['action'].split(resources.COMM_DOMAIN)[1] #Get everything in the URL after the domain
        
        response = self.client.post(url, TYPICAL_TWILIO_VOICEMAIL_RECORDING)
        
        self.assertEqual(response.status_code, 200)
            
    def test_tropo_that_voicemail_recording_is_saved(self):
        from django.conf import settings
        #First we need to figure out the recording URL.
        response_to_tropo_voicemail_request_json = voicemail(FakeRequest(TYPICAL_TROPO_VOICEMAIL_REQUEST))
        response_to_tropo_voicemail_request_dict = json.loads(response_to_tropo_voicemail_request_json.content)
        
        #Now that we have the URL, we need to post to that URL.
        command_list = response_to_tropo_voicemail_request_dict['tropo']
        record_command = find_command_in_tropo_command_list(command_list, command_name="record")
        url = record_command['record']['url']
        test_recording_file = '%s/apps/comm/test-call-recording.mp3' % settings.PROJECT_ROOT
        
        f = open(test_recording_file)
        response = self.client.post(url, {'filename': f})
        self.assertEqual(response.status_code, 200)
        
        call = PhoneCall.objects.get(id=self.tropo_call_id)
        self.assertTrue(call.recordings.exists())

    @expectedFailure
    def test_twilio_voicemail_is_transcribed(self):
        self.fail()
            
    def test_tropo_voicemail_is_transcribed(self): 
        from django.conf import settings
        #First we need to figure out the recording URL.
        response_to_tropo_voicemail_request_json = voicemail(FakeRequest(TYPICAL_TROPO_VOICEMAIL_REQUEST))
        response_to_tropo_voicemail_request_dict = json.loads(response_to_tropo_voicemail_request_json.content)
        
        #Now that we have the URL, we need to post to that URL.
        command_list = response_to_tropo_voicemail_request_dict['tropo']
        record_command = find_command_in_tropo_command_list(command_list, command_name="record")
        url = record_command['record']['url']
        test_recording_file = '%s/apps/comm/test-call-recording.mp3' % settings.PROJECT_ROOT
                
        f = open(test_recording_file)
        response = self.client.post(url, {'filename': f})
        self.assertEqual(response.status_code, 200)
        
        call = PhoneCall.objects.get(id=self.tropo_call_id)
        recordings = call.recordings.all()
        self.assertTrue(recordings.exists())
               
        response = transcription_handler(FakeRequest(TYPICAL_TROPO_TRANSCRIPTION_REQUEST), 'recording', recordings[0].id)
        self.assertEqual(recordings[0].transcription_text, SAMPLE_VOICEMAIL_WORDS)
    
    @expectedFailure
    def test_twilio_call_events_for_impossibly_boring_call(self):
        self.fail()
            
    def test_tropo_call_events_for_impossibly_boring_call(self):
        '''
        That a call in which absolutely nothing happens returns an empty list of events (ie no voicemail, no pickup)
        In the real world, this should never happen, as the hangup handler should always modify the 'ended' attribute, and thus this list will not be empty.
        Useful, however, for showing that problems in the hangup handler can be properly diagnosed by an empty list of events.
        '''
        call = PhoneCall.objects.get(id=self.tropo_call_id)
        events = call.list_events_by_time()
        self.assertFalse(events)
    
    @expectedFailure
    def test_twilio_call_events_for_call_that_went_to_voicemail(self):
        self.fail()
        
    def test_tropo_call_events_for_call_that_went_to_voicemail(self):
        from django.conf import settings
        #First we need to figure out the recording URL.
        response_to_tropo_voicemail_request_json = voicemail(FakeRequest(TYPICAL_TROPO_VOICEMAIL_REQUEST))
        response_to_tropo_voicemail_request_dict = json.loads(response_to_tropo_voicemail_request_json.content)
        
        #Now that we have the URL, we need to post to that URL.
        command_list = response_to_tropo_voicemail_request_dict['tropo']
        record_command = find_command_in_tropo_command_list(command_list, command_name="record")
        url = record_command['record']['url']
        test_recording_file = '%s/apps/comm/test-call-recording.mp3' % settings.PROJECT_ROOT
        
        f = open(test_recording_file)
        response = self.client.post(url, {'filename': f})
        self.assertEqual(response.status_code, 200)
        
        call = PhoneCall.objects.get(id=self.tropo_call_id)
        self.assertTrue(call.recordings.exists()) #End of clone of prior test
        
        events = call.list_events_by_time()
        self.assertTrue(events, msg="Even though call went to voicemail, events list was empty.")
        
        
class CallManagementExperience(TestCase):
            
    def setUp(self):
        do_config.set_up()
        admin = User.objects.create(is_superuser=True, username="admin", password="admin")
        admin.set_password('admin')
        admin.save()
        set_up_providers(self)
        people_config.set_up()

    def test_watch_calls_200(self):
        self.client.login(username="admin", password="admin")
        response = self.client.get('/comm/watch_calls/')
        self.assertEqual(response.status_code, 200)
        
    
    def test_watch_calls_page_paginates(self):
        self.client.login(username="admin", password="admin")
        create_phone_calls(30)
        
        response_page1 = self.client.get('/comm/watch_calls/')
        response_page2 = self.client.get('/comm/watch_calls/', {'page':2})
        
        self.assertFalse('displayCall_7' in response_page1.content)
        self.assertTrue('displayCall_21' in response_page1.content)
        self.assertTrue('<a href="?page=2">next</a>' in response_page1.content)
        self.assertFalse('<a href="?page=1">previous</a>' in response_page1.content)
        
        self.assertTrue('displayCall_7' in response_page2.content)
        self.assertFalse('displayCall_21' in response_page2.content)
        self.assertFalse('<a href="?page=2">next</a>' in response_page2.content)
        self.assertTrue('<a href="?page=1">previous</a>' in response_page2.content)
        
    def test_resolve_calls_200(self):
        self.client.login(username="admin", password="admin")
        response = self.client.get('/comm/resolve_calls/')
        self.assertEqual(response.status_code, 200)
        
    def test_resolve_calls_paginates(self):
        self.client.login(username="admin", password="admin")
        create_phone_calls(30)
        
        response_page1 = self.client.get('/comm/resolve_calls/')
        response_page2 = self.client.get('/comm/resolve_calls/', {'page':2})
        
        self.assertTrue('resolve_7' in response_page1.content)
        self.assertFalse('resolve_21' in response_page1.content)
        self.assertTrue('<a href="?page=2">next</a>' in response_page1.content)
        self.assertFalse('<a href="?page=1">previous</a>' in response_page1.content)
        
        self.assertFalse('resolve_7' in response_page2.content)
        self.assertTrue('resolve_21' in response_page2.content)
        self.assertFalse('<a href="?page=2">next</a>' in response_page2.content)
        self.assertTrue('<a href="?page=1">previous</a>' in response_page2.content)
           
    @expectedFailure
    def test_sms_to_tag_user_on_call_task(self):
        self.fail()
        
class OutgoingCalls(TestCase):
    '''
    We're no longer answering the phone; now we need to initiate a call.
    '''
    def setUp(self):
        people_config.set_up()
    
    def test_outgoing_call_menu_200(self):
        p = PhoneNumber.objects.create(number="5551231234")
        response = self.client.get('/comm/outgoing_call_menu/', {'phone_number':p.id})
        self.assertEqual(response.status_code, 200)
    
    @expectedFailure    
    def test_outgoing_call_menu_with_users(self):
        self.fail()
    
    @expectedFailure
    def outgoing_call_is_placed(self):
        self.fail()
        
    @expectedFailure
    def outgoing_call_initator_gets_call(self):
        self.fail()
    
    

class CommAppHealthTests(TestCase):
    
    @expectedFailure
    def test_heartbeat(self):
        self.fail()
    
    @expectedFailure
    def test_that_heartbeat_is_handled(self):
        self.fail()