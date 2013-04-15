
from . import comm_settings
from .models import PhoneCall
from django.http import HttpResponse
from django.utils.datastructures import MultiValueDictKeyError
from private import API_tokens, resources
from tropo import Session, Tropo
from twilio import twiml, util
from twilio.rest import TwilioRestClient
from twisted.internet import reactor
from twisted.internet.task import deferLater
from twisted.internet.threads import deferToThread
from what_apps.contact.models import PhoneProvider, PhoneNumber
import json
import logging
import requests






comm_logger = logging.getLogger('comm')

class CallResponse(object):
    '''
    A response to a request from a voip provider such as twilio or tropo.  
    Abstracts common verbs such as .say() and .ask() and .conference() and provides the appropriate command for the provider.
    '''
    
    def __init__(self, provider, *args, **kwargs):
        '''
        Takes a PhoneProvider object, sets the provider for this response to that provider.
        '''
        self.provider = provider
        if provider.name == "Twilio":
            self.response_object = twiml.Response()
        if provider.name == "Tropo":
            self.response_object = Tropo()
        super(CallResponse, self).__init__()
        
    def render(self):
        if self.provider.name == "Twilio":
            return HttpResponse(self.response_object, mimetype='text/xml')
        if self.provider.name == "Tropo":
            return HttpResponse(self.response_object.RenderJson(), mimetype='text/json')
    
    def say(self, *args, **kwargs):
        if self.provider.name == "Twilio":
            if kwargs['voice'] == 'Allison' or kwargs['voice'] == 'Susan' or kwargs['voice'] == 'Vanessa':
                kwargs['voice'] = 'woman'
            else:
                kwargs['voice'] = 'man'
            return self.response_object.addSay(*args, **kwargs)
        if self.provider.name == "Tropo":
            return self.response_object.say(*args, **kwargs)

    def transfer(self, *args, **kwargs):
        if self.provider.name == "Twilio":
            return self.response_object.addDial(*args, **kwargs)
        if self.provider.name == "Tropo":
            return self.response_object.transfer(*args, **kwargs)
        
    def conference(self, start_recording=False, *args, **kwargs):
        if self.provider.name == "Twilio":
            if start_recording:
                dial = self.response_object.addDial(record=True, action='%s/comm/recording_handler/call/%s/' % (resources.COMM_DOMAIN, kwargs['conference_id']))
            else:
                dial = self.response_object.addDial()
            startConferenceOnEnter = True if 'start_now' in kwargs and kwargs['start_now'] else False #Sometimes we want this joiner to start the conference.  Sometimes not.
            command = dial.addConference(kwargs['conference_id'], startConferenceOnEnter=startConferenceOnEnter)
            comm_logger.info('Telling Twilio: %s' % dial)
            return command
        if self.provider.name == "Tropo":
            self.response_object.on("hangup", next="/comm/handle_hangup/%s/%s/" % (kwargs['conference_id'], kwargs['number'].id))
            if 'record' in kwargs and kwargs['record']:
                self.response_object.startRecording('%s/comm/recording_handler/call/%s/' % (resources.COMM_DOMAIN, kwargs['conference_id']), format="audio/mp3")
            return self.response_object.conference(kwargs['conference_id'], allowSignals=['leaveConference',], *args, **kwargs)
    
    def conference_holding_pattern(self, conference_id, number_object, hold_music):
        '''
        Put someone on hold, perparing them for a conference.  During their hold, play the hold music.
        '''
        if self.provider.name == "Twilio":
            dial = self.response_object.addDial()
            reactor.callFromThread(twilio_deferred_voicemail_determination, conference_id, 30)
            return dial.addConference(conference_id)#TODO: waitUrl=hold_music)
         
        if self.provider.name == "Tropo":
            #First we add the hold music, allowing for the "exithold" signal to end it.
            self.response_object.say(hold_music, allowSignals=["joinConference", "goToVoiceMail", "incomplete"])
            self.response_object.on("hangup", next="/comm/handle_hangup/%s/%s/" % (conference_id, number_object.id))
            self.response_object.on('joinConference', next="/comm/simply_join_conference/%s/%s/" % (conference_id, number_object.id))
            self.response_object.on('goToVoiceMail', next="/comm/voicemail/")
            reactor.callFromThread(send_deferred_tropo_signal, conference_id, 'goToVoiceMail', 40) #How to test this?

    def join_and_begin_conference(self, conference_id, number, *args, **kwargs):
        '''
        Join the user to a conference that started with a holding pattern and begin the conference.
        '''
        comm_logger.info('%s is beginning conference %s', number, conference_id)
        conference_kwargs = {'conference_id':conference_id, 'number':number}
        if self.provider.name == "Twilio":
            conference_kwargs['start_now'] = True
        if self.provider.name == "Tropo":
            reactor.callFromThread(send_deferred_tropo_signal, conference_id, 'joinConference', 0)
            
        self.conference(start_recording=True, **conference_kwargs)
        return True #We can't know anything meaningful because we aren't going to wait around for the signal.
    
    def on(self, *args, **kwargs):
        if self.provider.name == "Twilio":
            raise NotImplementedError("Twilio does not offer an equivalent to Tropo's .on() method.")
        if self.provider.name == "Tropo":
            return self.response_object.on(*args, **kwargs)
        
    def call(self, *args, **kwargs):
        if self.provider.name == "Twilio":
            raise NotImplementedError("Twilio does not offer an equivalent to Tropo's .call() method.")
        if self.provider.name == "Tropo":
            if 'caller_id' in kwargs:
                kwargs['from'] = kwargs['caller_id'] #Why Tropo, do you think it's acceptable to use a python command (from) in your lib?
            return self.response_object.call(*args, **kwargs)
    
    def ask(self, *args, **kwargs):
        if self.provider.name == "Twilio":
            raise NotImplementedError("We're getting there..")
        if self.provider.name == "Tropo":
            return self.response_object.ask(*args, **kwargs)
        
    def prompt_and_record(self, recording_object=None, prompt=None, transcribe=False, *args, **kwargs):
        
        recording_url_args = ("recording" if recording_object else "call", recording_object.id if recording_object else int(kwargs['call_id']))
        
        if self.provider.name == "Twilio":
            self.response_object.say(prompt)
            recording_kwargs = {}
            recording_kwargs['action'] = "%s/comm/recording_handler/%s/%s/" % ((resources.COMM_DOMAIN,) + recording_url_args)
            recording_kwargs['timeout'] = 20
            if transcribe:
                recording_kwargs['transcribe'] = True
                recording_kwargs['transcribeCallback'] = "%s/comm/transcription_handler/%s/%s/" % ((resources.COMM_DOMAIN,) + recording_url_args)
            self.response_object.record(**recording_kwargs)
            
        if self.provider.name == "Tropo":
            recording_kwargs = {}
            recording_kwargs['say'] = prompt
            recording_kwargs['url'] = "%s/comm/recording_handler/%s/%s/" % ((resources.COMM_DOMAIN,) + recording_url_args)
            if transcribe:
                recording_kwargs['transcription'] = {'id':kwargs['call_id'], "url":"%s/comm/transcription_handler/%s/%s/" % ((resources.COMM_DOMAIN,) + recording_url_args)}
            self.response_object.record(**recording_kwargs)
    
    def reject(self):
        if self.provider.name == "Twilio":
            self.response_object.reject()
        else:
            raise NotImplementedError("Twilio only for the moment.")
            
        
    
    def hangup(self, *args, **kwargs):
        self.response_object.hangup(*args, **kwargs)

def send_deferred_tropo_signal(session_id, signal_name, defer_time):
    '''
    Waits for defer_time seconds and then seconds signal_name to call with call_id matching session_id.
    Useful for waiting for a while and then doing something to a call (ie, sending someone to voicemail).
    '''
    url =  "https://api.tropo.com/1.0/sessions/%s/signals" % session_id
    if not defer_time:
        deferToThread(requests.get, url, params = {'action': 'signal', 'value': signal_name})
    else:
        deferLater(reactor, defer_time, requests.get, url, params = {'action': 'signal', 'value': signal_name})
    return True

def deferred_route_twilio_call(session_id, url, defer_time):
    '''
    Currently unused but potentially useful.
    '''
    twilio_rest_client = TwilioRestClient(API_tokens.TWILIO_SID, API_tokens.TWILIO_AUTH_TOKEN)
    deferLater(reactor, defer_time, twilio_rest_client.calls.route, session_id, url)
    return True

def twilio_redirect_call_if_no_answer(session_id, url):
    '''
    Takes a session_id and the url of a twilio-compliant view.
    Determines if nobody has picked up - if so, redirects call to URL.
    '''
    twilio_rest_client = TwilioRestClient(API_tokens.TWILIO_SID, API_tokens.TWILIO_AUTH_TOKEN)
    call = PhoneCall.objects.get(call_id=session_id)
    if not call.has_begun():
        return twilio_rest_client.calls.route(session_id, '%s/comm/voicemail/' % (resources.COMM_DOMAIN))
    else:
        return False

def twilio_deferred_voicemail_determination(session_id, defer_time):
    deferLater(reactor, defer_time, twilio_redirect_call_if_no_answer, session_id, '%s/comm/voicemail/' % (resources.COMM_DOMAIN))

