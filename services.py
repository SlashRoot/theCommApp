'''
Service-specific functionality.  Any operations that are bound to specific providers belongs here.
'''
from . import comm_settings
from .comm_settings import SLASHROOT_EXPRESSIONS
from .models import PhoneCall
from .response import CallResponse
from .rest import SLASHROOT_TWILIO_ACCOUNT
from Crypto.Random.random import choice
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from private import API_tokens, resources
from tropo import Result, Session
from twilio import util, twiml
from twilio.rest import TwilioRestClient
from twisted.internet.threads import deferToThread
from what_apps.contact.models import PhoneProvider, PhoneNumber
import json
import logging
import requests
import urllib2





comm_logger = logging.getLogger('comm')

def incoming_twilio_phone_client_loader(request):
    from twilio.util import TwilioCapability
    account_sid = "AC260e405c96ce1eddffbddeee43a13004"
    auth_token = "fd219130e257e25e78613adc6c003d1a"
    capability = TwilioCapability(account_sid, auth_token)
    capability.allow_client_incoming(str(request.user.username))
    return render(request, 'comm/incoming_phone.html', locals())

def get_phone_calls_by_phone_number(phone_number):
    '''
    Deprecated but interesting - make agnostic.
    '''
    call_dict = {'To': phone_number.number}
    to_calls_json = SLASHROOT_TWILIO_ACCOUNT.request('/%s/Accounts/%s/Calls.json' % (API_tokens.TWILIO_API_VERSION, API_tokens.TWILIO_SID), 'GET', call_dict)

    call_dict = {'From': phone_number.number}
    from_calls_json = SLASHROOT_TWILIO_ACCOUNT.request('/%s/Accounts/%s/Calls.json' % (API_tokens.TWILIO_API_VERSION, API_tokens.TWILIO_SID), 'GET', call_dict)


    all_calls = json.loads(to_calls_json)['calls'] + json.loads(from_calls_json)['calls']

    for call in all_calls:
        recordings = SLASHROOT_TWILIO_ACCOUNT.request(call['subresource_uris']['recordings'], 'GET')
        call['recordings'] = json.loads(recordings)

    return all_calls

def find_command_in_twilio_response(twilio_response_object, command_name=None):
    verb_list = twilio_response_object._container[0].verbs
    for verb in verb_list:
        if verb.name == command_name:
            return verb
    return False #if the loop does not find any places where verb name is equal to command name then we know the command name is not in this verb list    
    
def find_command_in_tropo_command_list(command_list, signal_on=None, signal_allowed=None, command_name=None, occurance=0):
        '''
        Iterate through a tropo command list and figure out which one is the command that happens for the kwarg specified.
        If none exists, return False.
        
        Can identify the nth occurance, where 0 is the first matching command.
        '''
        number_of_kwargs_passed = bool(signal_on) + bool(signal_allowed) + bool(command_name)
        if not number_of_kwargs_passed == 1:
           raise TypeError('Pass one and only one criterion kwarg, not %s.  Passing too many or too few will cause Justin to bite you.' % number_of_kwargs_passed) 
        
        attempts = 0 #To match will occurances if need be.
        
        if command_name:
            for command in command_list:
                try:
                    if command_name in command: #Is this the command whose name we want?
                        if attempts == occurance:
                            return command #If so, we found what we're looking for.  Send it on back.
                        else:
                            attempts += 1
                            continue
                except KeyError:
                    continue #Nothing here.  Try the next entry.
            
            return False #If we made it this far, the signal wasn't found.

        if signal_on or signal_allowed:
            if signal_allowed:
                keyword = 'allowSignals' 
            if signal_on:
                keyword = 'event'
            needle = signal_on if signal_on else signal_allowed
            for command in command_list:
                if keyword in command.items()[0][1]:
                    command_details_tuple = command.items()[0] #The command is actually a dict of one entry - now we have it as a tuple.
                    command_parameters = command_details_tuple[1] #This is the "meat" of the command, where allowSignals will appear, if at all.
                    try:
                        haystack = command_parameters[keyword] #This is now a list of allowed signals OR a signal 'on' signal.
                    except KeyError:
                        continue #Nothing here.  Try the next entry.
                    if signal_on:
                        if needle == haystack: #There's only going to be one signal for this command if it's 'on.'
                            if attempts == occurance:
                                return command #If the needle fits, wear it.
                            else:
                                attempts += 1
                                continue
                        else:
                            continue #If it's not the needle, it's not the command.  Try the next one.
                    if signal_allowed: #In this case, haystack is a list.
                        for needle_candidate in haystack: #Let's iterate through it and look for our needle.
                            if needle_candidate == needle: #Is this the command that matches the signal we're looking for?
                                if attempts == occurance:
                                    return command #If so, we found what we're looking for.  Send it on back.
                                else:
                                    attempts += 1
                                    continue
                                    
                            
            return False #If we made it this far, the signal wasn't found.

def verifyTwilio(request):   
    utils = util.RequestValidator(API_tokens.TWILIO_AUTH_TOKEN)
    
    #Cheat - undo for deployment
    return 1
    
    try:
        if not utils.validateRequest(request.get_host(), request.POST, request.META['HTTP_X_TWILIO_SIGNATURE']):
            #Catch a spoofed Twilio request
            r = twiml.Response()
            r.addSay("no dice.")
            return HttpResponse(r, mimetype='text/xml')
    except KeyError:
        #Not even pretending to be Twilio.
        pass #TODO: Pass some kind of signal to raise error or 404
    
def get_provider_and_response_for_request(request):
    '''
    Conveinence method to determine if the request has come from Twilio or Tropo, return the appropriate provider object, and an appropriate repsonse object
    '''
    if 'AccountSid' in request.POST:
        provider = PhoneProvider.objects.get(name="Twilio")
    else:
        provider = PhoneProvider.objects.get(name="Tropo") #Ugh. TODO: Make better.
        
    return provider, CallResponse(provider)

def random_tropo_voice():
    voices = ['Allison', 'Susan', 'Vanessa', 'Dave', 'Steven', 'Victor']
    return choice(voices)

def discern_destination_from_tropo_request(request):
    '''
    Takes a Tropo blast request, figures out the single phone number that is to be called.
    '''
    session_params = json.loads(request.raw_post_data)['session']['parameters']
    number_id = session_params['number_to_call'] #Works for Tropo
    call_id = session_params['call_to_join'] #Works for Tropo
    is_green_phone = True if unicode(session_params['green_phone']) == "True" else False #Resolves properly to false even if param is the string "none," which Tropo sometimes throws into the mix
    return PhoneNumber.objects.get(id=number_id), PhoneCall.objects.get(id=call_id), is_green_phone


def standardize_call_info(request, provider=None):
    '''
    Takes a provider object, figures out the important details of the call (you know, caller id and whatnot) and return it as a dictionary.s
    '''
    if not provider:
        pass #TODO: Some logic to detect the provider.
    
    if provider.name == "Twilio":
        account_id = request.POST['AccountSid']
        call_id = request.POST['CallSid']
        from_caller_id = request.POST['From']
        to_caller_id = request.POST['To']
        status = request.POST['CallStatus']
    
    if provider.name == "Tropo":
        '''
        Tropo is kinda funny - it doesn't always let us grab the session info via their Session object (which we probably can help them fix).
        '''
        try:
            s = Session(request.raw_post_data)
            call_id = s.id
            account_id = s.accountId
            from_caller_id = s.dict['from']['id']
            to_caller_id = s.dict['to']['id']
            status = s.state if "state" in s.dict else "ringing"        
        except KeyError:
            '''
            e.message has been deprecated in lieu of wrapping a str() around KeyError
            '''
            if str(KeyError) == "session":                
                json_post_data = json.loads(request.raw_post_data)
                call_id = json_post_data['result']['sessionId']
                try:
                    phone_call = PhoneCall.objects.get(call_id = call_id)
                    call_object = phone_call
                    from_caller_id = phone_call.from_number.number
                except PhoneCall.DoesNotExist:
                    #This is a major bummer.
                    call_object = None
                    from_caller_id = None
            else:
                #We had a session, but we didn't have the keys we were looking for.
                s = Session(request.raw_post_data)
                number_id = s.parameters['number_to_call']
    
    return locals() #Don't forget, we're returning a dict.

def discern_intention_to_connect_from_answerer(request, provider):
    '''
    Figures out if an answerer wants to answer a call.
    '''
    intends_to_answer = False #Assume that they don't want to answer unless they affirmatively indicate that they do.
    result = Result(request.raw_post_data)  # TODO: Uncouple from tropo
    try:
        if result._actions['disposition'] == "SUCCESS": #If we've found a match....
            vocal_response = result.getValue() #...then grab that match and see.....
            if vocal_response in ["0","1","2","3","4","5","6","7","8","9",SLASHROOT_EXPRESSIONS['phrase_to_answer_call']]: #....if it matches the phrase we're looking for.
                intends_to_answer = True
    except AttributeError:
        return False
    return intends_to_answer

def extract_transcription_as_text(request, provider):
    if provider.name=="Tropo":
        '''
        Tropo, in its infinite fucking helpfulness, doesn't provide a helper for receiving transcriptions.
        '''
        response_dict = json.loads(request.raw_post_data)
        result_dict = response_dict['result']
        return result_dict['transcription']

def place_deferred_outgoing_conference_call(participant, conference_id, provider):
    '''
    Calls the function below.  Refactor both!
    '''
    # TODO: Make this a REST call instead.
    place_call_to_number(str(participant.number.id), str(conference_id), provider, green_phone=participant.green_phone)

def place_call_to_number(number, conference_id, provider, green_phone=False):
    '''
    Stupid name.  Refactor please.
    '''
    if provider.name=="Tropo":
        # This function causes tropo to hit /comm/conference_blast/
        deferToThread(requests.get, 'https://api.tropo.com/1.0/sessions?action=create&token=%s&number_to_call=%s&call_to_join=%s&green_phone=%s' % (API_tokens.TROPO_BLAST_TOKEN, number, str(conference_id), str(green_phone)))
    if provider.name=="Twilio":        
        twilio_client = TwilioRestClient(API_tokens.TWILIO_SID, API_tokens.TWILIO_AUTH_TOKEN)  # dehydrate.
        number_object = PhoneNumber.objects.get(id=number)
        # TODO: No if machine detection for green phone, and timeout issues
        deferToThread(twilio_client.calls.create, if_machine="Hangup", to=number_object.number, from_="8456338330", timeout=20, url="%s/comm/pickup_connect_auto/%s/%s/" % (resources.COMM_DOMAIN, number, conference_id))

def get_audio_from_provider_recording(request, provider):
    
    if provider.name == "Twilio":
        # At the moment we've commented out the actual audio download from Twilio.
        # We need to re-implement asynchronously.
        # The best way is probably to make a cronjob that grabs them every night or something. 
        recording_url = "%s.mp3" % request.POST['RecordingUrl']
#        recording_file_name = recording_url.split('/')[-1]
#        recording_audio = urllib2.urlopen(recording_url)
#        comm_logger.info('Opened %s' % recording_audio)
        
#        local_recording_file = open(settings.PUBLIC_FILE_UPLOAD_DIRECTORY + "audio/call_recordings/" + recording_file_name, 'wb+')
#        local_recording_file.write(recording_audio.read())        
#        comm_logger.info('Saved %s' % recording_audio)
#        local_recording_file.close()
        
        return None, recording_url
    
    if provider.name == "Tropo":
        filename = str(request.FILES['filename'])
        destination = open(settings.PUBLIC_FILE_UPLOAD_DIRECTORY + "audio/call_recordings/" + filename, 'wb+')
        for chunk in request.FILES['filename'].chunks():
            destination.write(chunk)
        destination.close()
        
        return destination, False
    