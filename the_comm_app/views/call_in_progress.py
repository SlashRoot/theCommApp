from rest_framework import viewsets

class AnswerViewSet(viewsets.ViewSet):

    def create(self, request):
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