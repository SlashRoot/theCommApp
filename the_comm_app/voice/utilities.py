def standardize_call_info(call_dict, provider=None):
    '''
    Takes a provider object, figures out the important details of the call (you know, caller id and whatnot) and return it as a dictionary.s
    '''
    if not provider:
        pass #TODO: Some logic to detect the provider.

    if provider.name == "Twilio":
        account_id = call_dict['AccountSid']
        call_id = call_dict['CallSid']
        from_caller_id = call_dict['From']
        to_caller_id = call_dict['To']
        status = call_dict['CallStatus']

    if provider.name == "Tropo":
        raise NotImplementedError("No Tropo for now.")
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