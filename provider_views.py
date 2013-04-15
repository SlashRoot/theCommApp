'''
Handles requests made by provider entities, such as Twilio and Tropo.

These views are not meant to be accessed directly by humans.
'''
from .call_functions import call_object_from_call_info, \
    place_conference_call_to_dial_list, proper_verbage_for_final_call_connection
from .comm_settings import SLASHROOT_EXPRESSIONS
from .models import PhoneCall, CommunicationInvolvement, PhoneCallRecording
from .services import get_provider_and_response_for_request, \
    standardize_call_info, random_tropo_voice, \
    discern_destination_from_tropo_request, \
    discern_intention_to_connect_from_answerer, extract_transcription_as_text, \
    get_audio_from_provider_recording
from django.conf import settings
from django.core.mail.message import EmailMultiAlternatives
from django.http import HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from twisted.internet import reactor
from what_apps.contact.models import DialList, PhoneNumber
from what_apps.people.models import UserProfile
from what_apps.utility.models import FixedObject
import datetime
import logging

comm_logger = logging.getLogger('comm')


@require_http_methods(["POST"])
@csrf_exempt
def answer(request, this_is_only_a_test=False):
    '''
    The first response to a basic incoming call.  Can take requests from multiple providers.
    '''
    #First, let's figure out which provider is making this request.
    provider, r = get_provider_and_response_for_request(request) #Now we have a response object that we can use to build our response to the provider.
    
    #Now we need a call object with the appropriate details, regardless of the provider.
    call_info = standardize_call_info(request, provider=provider)
    call = call_object_from_call_info(call_info) #Identify the call, saving it as a new object if necessary.
    if call.from_number.spam:
        r.reject()
        comm_logger.info('%s %s call from %s (rejected because spam)' % (call_info['status'], provider, call.from_number))
    else:
        comm_logger.info('%s %s call from %s' % (call_info['status'], provider, call.from_number))
    
    if not call.ended:
        r.say(SLASHROOT_EXPRESSIONS['public_greeting'], voice=random_tropo_voice()) #Greet them.
        
        r.conference_holding_pattern(call.call_id, call.from_number, "http://hosting.tropo.com/97442/www/audio/mario_world.mp3") #TODO: Vary the hold music
        
        dial_list = DialList.objects.get(name="SlashRoot First Dial")
        
        if not this_is_only_a_test:
            #if it is only a test users' phones will not ring
            reactor.callFromThread(place_conference_call_to_dial_list, call.id, dial_list.id) #Untested because it runs in twisted. TOOD: Ought to take a DialList as an argument

    return r.render()


@csrf_exempt
def conference_blast(request):
    '''
    Places the outgoing call to somebody who might pick up.
    We have a branch here regarding whether the picker-upper is a green phone.
    If they are and they pick up, connect them to the call quickly.
    If they aren't and they pick up, send a request to the alert_pickup function.
    '''
    provider, r = get_provider_and_response_for_request(request)
    
    try: #Prevent 500s from simply browsing to the URL.
        number_object, phone_call_object, is_green_phone = discern_destination_from_tropo_request(request)
    except ValueError:
        return HttpResponseNotAllowed(['POST'])
    
    nicer_number = number_object.number[0:3] + number_object.number[4:7] + number_object.number[8:12]
    
    r.call(to = nicer_number, timeout=24, caller_id='18456338330') #TODO: Capitalization is Tropo convention.  Abstract in response class.
    r.on("incomplete", next="/comm/alert_timeout/") #TODO: Slightly TROPO coupled.  Let's fix this.
    if is_green_phone:
        #If they are the green phone, don't make them say the confirmation phrase.
        r.on("continue", next="/comm/pickup_connect_auto/%s/%s/" % (number_object.id, phone_call_object.id))
    else:
        r.on("continue", next="/comm/alert_pickup/%s/%s/" % (number_object.id, phone_call_object.id))
    
    return r.render()

@csrf_exempt
def alert_pickup(request, number_id, call_id):
    '''
    Somebody has in has picked up a call - now they can decide whether to answer or not.
    '''
    provider, r = get_provider_and_response_for_request(request)
    call = PhoneCall.objects.get(id = call_id)
    
    inquiry = call.announce_caller()
        
    try:
        call_participants = call.participants.filter(direction="to")
        if call_participants:
            inquiry += "Also on the call: "
            voice = "Victor"
            for involvement in call_participants:
                inquiry += " %s, " % str(involvement.person.first_name)
        else:
            voice = "Allison"
            
    except PhoneCall.DoesNotExist:#    r.transfer('+1845-204-3574')
#    return r.render()
        pass #raise ReallyFuckedUpError or provide some kind of path to a decent outcome
    
    r.ask(choices = "0,1,2,3,4,5,6,7,8,9,%s" % SLASHROOT_EXPRESSIONS['phrase_to_answer_call'], timeout=10, name="response", say = inquiry, attempts=20, minConfidence=37, voice = voice)
    r.on(event = "continue", next ="/comm/pickup_connect/%s/%s/" % (number_id, call.id) ) #We need to tell them the number, call id, and number of current participants
    
    return r.render()

@csrf_exempt
def pickup_connect(request, number_id, call_id, connect_regardless=False):
    '''
    Checks to see if the answerer indicated that they wanted to answer, and creates a new call object and connects them if so.
    '''
    
    provider, r = get_provider_and_response_for_request(request)
    call = PhoneCall.objects.get(id = call_id)
    
    try: #This is somebody who is answering our call.  We damn well better know what this number is and to whom is belongs.
        answerer_number = PhoneNumber.objects.get(id=number_id)
        answerer_user = answerer_number.owner.userprofile.user 
    except (PhoneNumber.DoesNotExist, UserProfile.DoesNotExist), e:
        #raise ReallyFuckedUpError
        raise
    
    if not connect_regardless: #If connect regardless is false, we still might answer if they answered with the correct phrase.
        #TODO: Turn this into a "prevent default" decorator
        try: #Prevent 500s from simply browsing to the URL.
            affirmative_consent = discern_intention_to_connect_from_answerer(request, provider)
        except ValueError:
            return HttpResponseNotAllowed(['POST'])

        
    if connect_regardless or affirmative_consent:
        announce_caller = bool(connect_regardless) #If we're connecting regardless, let's assume we haven't yet heard whom the caller is.
        proper_verbage_for_final_call_connection(call, r, announce_caller) #Appends the appropriate say to the response
        
        if not call.has_begun():
            r.join_and_begin_conference(conference_id = call.call_id, number=answerer_number)
        else:
            r.conference(conference_id = call.call_id, number=answerer_number)
         
        #Create a participant object for this answerer (they are receiving the call, so it's "to" them)   
        call.participants.create(person=answerer_user, direction="to")
        
        comm_logger.info('%s answered call %s' % (answerer_user, call))
        
        #Make sure the answerer is an owner of the task and it's tagged "answered."
        task = call.resolve_task()
        task.ownership.create(owner=answerer_user)
        task.tags.add("answered") #TODO: Maybe move this into the branch above (call.has_begun()) so that we only tag the task once.
        
        #Send an email to this user with a link to the Task.
        
        #We want to include the caller in the subject, so we'll grab their PhoneNubmer object now.        
        caller_number = call.from_number
        subject = "Call from %s" % str(caller_number)
        from_email = "phonecalldispatch@slashrootcafe.com"
        recipient_list = [answerer_user.email]
        
        #We also want to inform the caller of the other unresolved calls.
        resolve_protoype = FixedObject.objects.get(name="TaskPrototype__resolve_phone_call").object
        number_of_unresolved_calls = resolve_protoype.instances.filter(resolutions__isnull=True).exclude(id=2686).count() #TODO: Explain to the people WHY the fuck we are excluding 2686.
        
        message = '<a href="http://slashrootcafe.com%s">Resolve This Call</a>\n\n<a href="http://slashrootcafe.com/comm/resolve_calls/">(%s other unresolved calls)</a>' % (task.get_absolute_url(), number_of_unresolved_calls)
        
        msg = EmailMultiAlternatives(subject, message, from_email, recipient_list)
        msg.attach_alternative(message, "text/html")
        msg.send()
        
    return r.render()


@csrf_exempt
def handle_hangup(request, conference_id, number_id):
    r = get_provider_and_response_for_request(request)[1]
    phone_call_object = PhoneCall.objects.get(call_id=conference_id)
    number_object = PhoneNumber.objects.get(id=number_id)
    
    #If the number object has an owner, their participation needs to be ended.
    if number_object.owner:
        participation = CommunicationInvolvement.objects.filter(communication__phonecall__call_id=conference_id, person=number_object.owner.userprofile.user).order_by('-created')[0]
        participation.destroyed = datetime.datetime.now()
        participation.save()
        
    #If the phone call object is that of the original caller, we can consider this phone call to be over.
    if number_object == phone_call_object.from_number:
        phone_call_object.ended = datetime.datetime.now()
        phone_call_object.save()
        
    comm_logger.info('%s hung up' % phone_call_object)
    
    return r.render()

@csrf_exempt
def simply_join_conference(request, conference_id, number_id):
    '''
    Just join the conference with this conference ID and start recording.
    We aren't asking for the call ID and lookup because we want to avoid the extra DB hit.  This can be hosted on Tropo scripting, cached with varnish, or whatever we might imagine.
    '''
    provider, r = get_provider_and_response_for_request(request)
    number = PhoneNumber.objects.get(id=number_id)
    r.conference(conference_id = conference_id, number=number, record=True)
    
    comm_logger.info('%s joined the conference' % number)
    return r.render()

@csrf_exempt
def transcription_handler(request, object_type, id):
    provider, r = get_provider_and_response_for_request(request)
    transcription_text = extract_transcription_as_text(request, provider)
    
    #Now we need to figure out whether we already have a recording object to pair it with.
    if object_type == "recording":
        recording_object = PhoneCallRecording.objects.get(id=id)
    else:
        recording_object = PhoneCallRecording.objects.create(call_id = id)
    
    recording_object.transcription_text = transcription_text
    recording_object.save()
    
    comm_logger.info('%s %s was transcribed - saved on recording %s.  Reads: %s' % (object_type, id, recording_object.id, transcription_text) )
    
    
    return r.render()

@csrf_exempt
def recording_handler(request, object_type, id):
    '''
    Handles audio files sent by VOIP providers.
    '''
    comm_logger.info('Recording provided for %s %s' % (object_type, id))
    
    provider, r = get_provider_and_response_for_request(request)
    #First we'll save the MP3 file.
    file, url = get_audio_from_provider_recording(request, provider)
    
    #Now we need to figure out whether we already have a recording object to pair it with.
    if object_type == "recording":
        recording_object = PhoneCallRecording.objects.get(id=id)
    else:
        call = PhoneCall.objects.get(call_id=id)
        recording_object = PhoneCallRecording.objects.create(call=call)
    
    if file:
        recording_object.audio_file = file.name
        comm_logger.info('Got a recording file: %s' % (file.name))
    
    if url:
        comm_logger.info('Got a recording url: %s' % (url))
        recording_object.url = url
    
    recording_object.save()
    
    comm_logger.info('Recording for %s %s saved as #%s' % (object_type, id, recording_object.id))
    
    return r.render()

@csrf_exempt
def voicemail(request):
    provider, r = get_provider_and_response_for_request(request)
    #Now we need a call object with the appropriate details, regardless of the provider.
    call_info = standardize_call_info(request, provider=provider)
    call = PhoneCall.objects.get(call_id=call_info['call_id'])
    voicemail_recording = PhoneCallRecording.objects.create(call=call)
    
    task = call.resolve_task()
    task.tags.add("voicemail")
        
    prompt = 'No SlashRoot member is available to answer your call right now.  Please leave a message and a SlashRoot member will return your call.'
    r.prompt_and_record(call_id=call.id, recording_object = voicemail_recording, format="audio/mp3", url="", transcribe=True, prompt=prompt)
    
    rendered_response = r.render()
    
    comm_logger.info('%s went to voicemail.  Telling Twilio: %s' % (call, rendered_response))
    
    return rendered_response

#@csrf_exempt
#def outgoing_callback(request):
#    
#    to_number_id = request.GET['phone_number']
#    to_number = PhoneNumber.objects.get(id=to_number_id)
#
#    r = twiml.Response()
#    r.addSay('Now connecting your call.')
#    r.addDial(to_number.number, record=True, timeOut=45)
#    return response(r, mimetype='text/xml')
