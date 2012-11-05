from django.core.management.base import BaseCommand
from django.http import HttpRequest
from comm.services import standardize_call_info
from comm.call_functions import call_object_from_call_info
from what_apps.contact.models import PhoneProvider

class Command(BaseCommand):
 
    def handle(self, *args, **options):
        '''
        Scenarios:
        
        *A call is not accounted for in our system.
        *A call is accounted for, but its recordings are not.
        *A call and its recordings are accounted for.
        '''
        
        from comm.services import SLASHROOT_TWILIO_ACCOUNT
        from comm.models import PhoneCall, PhoneCallRecording
        import logging
        
        s = SLASHROOT_TWILIO_ACCOUNT
        
        calls = SLASHROOT_TWILIO_ACCOUNT.calls.list(page_size=30, to="+18456338330")
        
        TWILIO = PhoneProvider.objects.get(name="Twilio")
        
        print "Retrieved Initial data about %s calls." % len(calls)
        
        for counter, call in enumerate(calls):
            
            print "Iteration %s: Processing Call %s" % (counter, call.sid)
            try:
                phone_call_object = PhoneCall.objects.get(call_id=call.sid)
                print "We knew about the call.  It's #%s" % phone_call_object.id
            except PhoneCall.DoesNotExist:
                #We need to proceed through the flow of creating a call, just like we do for a new call.
                fake_request = HttpRequest()
                
                try: #We have cases with no "from."  Let's deal with those.
                    fake_request.POST['From'] = call.from_formatted
                except AttributeError:
                    fake_request.POST['From'] = ""
                
                fake_request.POST['AccountSid'] = call.account_sid
                fake_request.POST['CallSid'] = call.sid
                fake_request.POST['To'] = call.to
                fake_request.POST['CallStatus'] = call.status
                
                call_info = standardize_call_info(fake_request, provider=TWILIO)
                phone_call_object = call_object_from_call_info(call_info) #Identify the call, saving it as a new object if necessary.
                
                print "WE DID NOT KNOW ABOUT THE CALL.  We have saved it as #%s." % phone_call_object.id
            #Now, in either case, we have a record of the phone call.  That's good.  Now for the recordings.
            #We're going to delete PhoneCallRecording objects and just make them new.
            phone_call_object.recordings.all().delete()
            
            for recording in call.recordings.list():
                #We need to process the URL and delete parts of _it because the python helper library reports them with the now deprecated calls resource.
                url_parts_list = recording.uri.split('/')
                del(url_parts_list[6:8])
                good_url = "/".join(url_parts_list)
                
                    
                r = PhoneCallRecording.objects.create(
                                                      url = "%s.mp3" % good_url,
                                                      call = phone_call_object 
                                                      )
                print "There is a recording.  We have saved it as #%s." % r.id
                
            print "----------------------------------------------"