from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.core.cache import cache
from django.core.exceptions import MultipleObjectsReturned
from django.db import models
from django.db.models import Q
from django.db.models.query import QuerySet
from django.db.models.signals import post_save
from itertools import chain
from model_utils.managers import PassThroughManager
from taggit.managers import TaggableManager
from what_apps.comm import comm_settings
from what_apps.do.models import Task, TaskRelatedObject, TaskAccess
from what_apps.push.functions import push_with_template
from what_apps.utility.models import FixedObject





class Communication(models.Model):
    '''
    A single instance of communication - a phone call, email, etc.
    '''
    created = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)

class CommunicationInvolvement(models.Model):
    '''
    People are involved in communication in different ways depending on the medium, the circumstances, and sometimes the actual people.
    This model will help us sort out the ways that people are involved in an instance of communication.
    '''
    person = models.ForeignKey(User, related_name="communications")
    communication = models.ForeignKey(Communication, related_name="participants")
    
    #This is an interesting piece of knowledge to try to store.
    #In some communications, such as a phone call or one-on-one email, there is a distinct role of the "sender" and the "recipient".
    #But not always.  :-)
    direction = models.CharField(max_length=12, choices=(('from', 'from'), ('to', 'to')), blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    destroyed = models.DateTimeField(blank=True, null=True)
    
    def __unicode__(self):
        return "%s %s %s" %(self.person.username, self.direction, self.communication)
    
    def get_absolute_url(self):
        pass
    
    def number_on_the_other_end(self):
        '''
        If there are no other participants, simply returns the 'other' number
        '''
        if self.direction == "from":
            return self.communication.phonecall.to_number
        else:
            return self.communication.phonecall.from_number
    
    def other_participants(self):
        return self.communication.participants.exclude(id=self.id)
    
    def direction_inverse(self):
        if self.direction == "from":
            return "to"
        else:
            return "from"
        
    def summary(self):
        if self.direction == "to":
            return "%s answered " % (self.person.userprofile.user.first_name)
        if self.direction == "from":
            return "%s called " % (self.person.userprofile.user.first_name)

class PhoneCallQuerySet(QuerySet):
    def involving(self, user_list=None, include_from=True, include_to=True, subtractive=False):
        '''
        Takes a list of users, returns a QuerySet of PhoneCalls involving those users.
        By default, includes calls both from and to these users; can be changed with kwargs.
        '''
        if not user_list:
            return self
        
        if not include_from and not include_to:
            return self #Instead of: TypeError("You must include either 'from' or 'to' calls.")

        #We've precluded the impossible use cases.
        
        if include_from and include_to:
            filter_kwargs = dict(participants__person__in=user_list)
        #If we aren't including both, we need to discriminate.
        elif include_from:
            filter_kwargs = dict(participants__person__in=user_list, participants__direction='from') 
        elif include_to:
            filter_kwargs = dict(participants__person__in=user_list, participants__direction='to')
        
        if not subtractive:            
            return self.filter(**filter_kwargs)
        else:
            return self.exclude(**filter_kwargs)


    def unresolved(self):
        '''
        Takes a Queryset of PhoneCall objects, returns a Queryset of PhoneCall objects with unresolved tasks.
        '''
        return self.filter(tasks__task__status__lt=2)
    
    def has_recording(self, voicemail=True):
        calls_with_recordings = self.filter(recordings__is_null=False)
        
        if voicemail:
            return calls_with_recordings
        else:
            return calls_with_recordings.filter(tasks__tags__name="voicemail")
        
class PhoneCall(Communication):
    '''
    This model is loosely based on a twilio phone call HTTP request, which is explained here:
    http://www.twilio.com/docs/api/2010-04-01/twiml/twilio_request
    
    The idea is that for each phone call, we want a record that corresponds to the data that twilio recognizes.
    Even if we stop using twilio in the future, their phone call "model," if you want to think of it that way,
    is well thought out and useful.
    
    I'm having some trouble wrapping my head around which fields can be blank / null.
    I want this model to be useful outside twilio, and perhaps even manually useful.
    '''
    service = models.ForeignKey('contact.PhoneProvider') #How was this call made?
    call_id = models.CharField(max_length=40, unique=True) #A unique call identifier (from the carrier API)
    account_id = models.CharField(max_length=40, blank=True, null=True) #An account number (from the carrier API)
    dial = models.BooleanField() #Is this a "dial call"?
    related_call = models.ForeignKey("self", blank=True, null=True, related_name="related_calls") #For example, if this is a dial 
    from_number = models.ForeignKey('contact.PhoneNumber', related_name="calls_from", help_text="Literally the number that dialed to initiate the call")    
    to_number = models.ForeignKey('contact.PhoneNumber', related_name="calls_to", help_text="Literally the number that was dialed to initiate the call")
    
    ended = models.DateTimeField(blank=True, null=True, help_text="When the from_number hung up.")
    
    tasks = generic.GenericRelation('do.TaskRelatedObject')
    notices = generic.GenericRelation('social.DrawAttention')
    
    objects = PassThroughManager.for_queryset_class(PhoneCallQuerySet)()
    
    def __unicode__(self):
        if self.from_user():
            if "@" in self.from_user().username or self.from_user().is_active == False:
                user_string = self.from_user().get_full_name()
            else:
                user_string = self.from_user().username
            return "Phone Call from %s" % (user_string)
        else:
            return "Phone Call %s" % ( str(self.id), )
    
    def service_log_display(self):
        return self.__unicode__()
    
    def announce_caller(self):
        if self.from_user(): #Look to see if this phone number has an owner
            caller = self.from_user()
            announcement = "Call from %s. " % str(caller.get_full_name())
        else: #We know about the phone number, but we don't have a ContactInfo / userprofile for it.
            announcement = comm_settings.SLASHROOT_EXPRESSIONS['unknown_caller']
        return announcement
    
    def has_begun(self):
        '''
        For now, we'll consider a call as having begun if it has any 'to' participants.
        '''
        return self.participants.filter(direction="to").exists()
    
    def voicemail(self):
        if self.resolve_task().tags.filter(name="voicemail").exists():
            voicemail = self.recordings.all()[0] #There should never be more (or less) than one recording with this tag.
            return voicemail
        else:
            return False
    
    def list_events_by_time(self):
        '''
        Gives a chronology of the events in this phone call.
        Each event is a PhoneCallEvent object.
        Used, for example, in templates which depict a chronological narrative of a phone call.
        '''
        list_of_events = []
        
        if self.voicemail():
            voicemail = self.voicemail()
            voicemail_event = PhoneCallEvent(object=voicemail, time=voicemail.created, type="voicemail")
            list_of_events.append(voicemail_event)


        all_pickups = self.participants.filter(direction="to")
        all_hangups = self.participants.filter(destroyed__isnull=False)
        
        for pickup in all_pickups:
            pickup_event = PhoneCallEvent(object=pickup, time=pickup.created, type="pickup")
            list_of_events.append(pickup_event)
            
        for hangup in all_hangups:
            hangup_event = PhoneCallEvent(object=hangup, time=hangup.destroyed, type="hangup")
            list_of_events.append(hangup_event)
            
        if self.ended:
            caller_hangup_event = PhoneCallEvent(object=self, time=self.ended, type="ended")
            list_of_events.append(caller_hangup_event)
            
        sorted_list_of_events = sorted(list_of_events, key = lambda event: event.time)
        
        return sorted_list_of_events
        
    def participants_as_list(self):
        '''
        List participants other than from_user
        '''
        p = list(self.participants.all())
        
        if self.from_user() in p:
            p.remove(self.from_user())
        
        return p
    
    def answerers(self):
        answerers = []
        for participation in self.participants.filter(direction="to"):
            answerers.append(participation.person)
        return answerers

    def get_absolute_url(self):
        return "/comm/phone_call_details/" + str(self.id)
        
    #TODO: Add exception names and ensure that these lines work if the number belongs to a commercegroup
    def from_user(self, update=True):
        '''
        Returns a User object or False.
        '''
        try:
            user = self.from_number.owner.userprofile.user
            return user
        except:
            return False
    
    def from_information(self):
        person = self.from_number
        try:
            person = self.involved.get(direction="from").person.userprofile.contact_info
        except:
            try:
                person = self.from_number.owner
            except:
                pass        
        return person
    
    def to_user(self):
        person = self.to_number
        try:
            person = self.involved.get(direction="to").person
        except:
            try:
                person = self.to_number.owner
            except:
                pass        
        return person
    
    def resolve_task(self):
        try:
            related_object = self.tasks.get(task__prototype__name="Resolved Call: [[0]]")
            return related_object.task #TODO: Ask ourselves - is this how we want to do this?  Or create a utility.ConfigurationOption object?
        except Task.DoesNotExist, TaskRelatedObject.DoesNotExist:
            raise RuntimeError('Unable to get the task to resolve this call.  Tell Justin to raise ReallyFuckedUpError.')

    def set_resolve_status(self, status, user):
        '''
        A wrapper around Task.set_status. 
        Sets the status of the task object to resolve this call.
        '''
        status_is_changed = self.resolve_task().set_status(status, user)
        if status_is_changed:
            cache.delete('number_of_unresolved_calls')
        resolve_task = self.resolve_task()
        return status_is_changed
    
class PhoneCallRecording(models.Model):
    '''
    Tracks the audio recording of a telephone call.
    '''
    call = models.ForeignKey(PhoneCall, related_name="recordings")
    #snapshot = models.OneToOneField(PhoneCallSnapshot, related_name="recording")
    url = models.URLField(blank=True, null=True)
    transcription_text = models.TextField(blank=True, null=True)
    #audio file never gets saved by the model itself, but programmatically in a view that responds to provider requests
    audio_file = models.FileField(blank=True, null=True, upload_to="nowhere", editable=False)
    created = models.DateTimeField(auto_now_add=True)
    
    tags = TaggableManager()
    
    def get_audio_file_url(self):
        '''
        A shameful fucking hack.
        '''
        if self.url:
            return self.url
        
        try:
            supposed_to_be_the_url = self.audio_file.url
            split_url = supposed_to_be_the_url.split('/')
            file_name = split_url[-1]
            return "/media/public/audio/call_recordings/%s" % file_name
        except ValueError:
            return False

    
class VoiceMailBox(models.Model):
    '''
    What Mailbox does a Voicemail belong to?  The home of a group of related Voicemails.
    '''
    name = models.CharField(max_length=50)
    number = models.IntegerField(unique=True)
    discription = models.TextField()
   
    def message_count(self):
       count = self.number
       return count
   
class PhoneCallEvent(object):
    '''
    Not a model.
    Just a conveinence class to store events that occur within a phone call.
    '''
    type = None #Will be hangup, pickup, voicemail, etc.
    time = None
    object = None #Will be the CommunicationInvolvement or PhoneCallRecording - often we'll have two PhoneCallEvents for the same object, ie one for the pickup and another for the hngup in a PhoneCallInvolvement
    
    def __init__(self, type=None, time=None, object=None):
        self.type = type
        
        if self.type not in ("pickup", "hangup", "voicemail", "ended"):
            raise TypeError("Type must be pickup, hangup, ended, or voicemail")
        
        self.time = time
        self.object = object
    
    def summary(self):
        if self.type == "pickup":
            summary = "%s picked up" % self.object.person.username
        if self.type == "hangup":
            summary =  "%s hung up" % self.object.person.username
        if self.type == "voicemail":
            summary = "caller was sent to voicemail"
        if self.type == "ended":
            summary = "caller hung up"
        return summary




#TODO: Move this stuff elsewhere.  Maybe the .save() method.

RESOLVE_PHONE_CALL = "TaskPrototype__resolve_phone_call"
    
def notifyCallSave(instance, **kwargs):
    '''
    When phone calls are saved, push to watch_calls
    ''' 
    if instance.__class__ == PhoneCall:
        call = instance
        
        if kwargs['created']:
            resolve_protoype = FixedObject.objects.get(name=RESOLVE_PHONE_CALL).object        
            resolve_task = resolve_protoype.instantiate()
            resolve_relationship = TaskRelatedObject.objects.create(task = resolve_task, object = call)
            try:
                access = TaskAccess.objects.create(task=resolve_task, prototype = FixedObject.objects.get(name="TaskAccessPrototype__answer_phone_calls").object)
            except FixedObject.DoesNotExist:
                #TODO: The FixedObject isn't in the DB yet.  Run the setup.
                raise
    if instance.__class__ == CommunicationInvolvement:
        call = instance.communication.phonecall #TODO: This will break when we introduce non-phonecall CommunicationInvolvement objects.
    push_with_template('comm/call_alert.html', {'call': call}, "/incomingCall")

post_save.connect(notifyCallSave, sender=PhoneCall)
post_save.connect(notifyCallSave, sender=CommunicationInvolvement)