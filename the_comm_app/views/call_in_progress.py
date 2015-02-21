from rest_framework import viewsets
from twilio import twiml
from the_comm_app.services import standardize_call_info
from the_comm_app.call_functions import call_object_from_call_info
from the_comm_app.models import PhoneProvider
from rest_framework.response import Response


class AnswerViewSet(viewsets.ViewSet):
    
    def action(self):
        return
    
    @property
    def action_params(self):
        return {'name': 'Generic Answer'}
    
    def must_reject(self):
        return False

    def determine_provider(self, request=None):
        request = request or self.request
        
        if 'AccountSid' in request.POST:
            self.provider = PhoneProvider("Twilio")
        else:  # Ugh. TODO: Make better.  Instead of assuming Tropo, let's actually detect it.
            self.provider = PhoneProvider("Tropo") 

    def create(self, request):
        '''
        The first response to a basic incoming call.  Can take requests from multiple providers.
        '''
        self.determine_provider(request)
        
        #Now we need a call object with the appropriate details, regardless of the provider.
        call_info = standardize_call_info(request, self.provider)

        # Identify the call, saving it as a new object if necessary.
        self.call = call_object_from_call_info(call_info)
        
        action_result = self.action(**self.action_params)

#         if not call.ended:
#             r.say(SLASHROOT_EXPRESSIONS['public_greeting'], voice=random_tropo_voice()) #Greet them.
#             
#             r.conference_holding_pattern(call.call_id, call.from_number, "http://hosting.tropo.com/97442/www/audio/mario_world.mp3") #TODO: Vary the hold music
#             
#             dial_list = DialList.objects.get(name="SlashRoot First Dial")
#             
#             reactor.callFromThread(place_conference_call_to_dial_list, call.id, dial_list.id) #Untested because it runs in twisted. TOOD: Ought to take a DialList as an argument
#     
        return Response(self.provider.get_response_object())