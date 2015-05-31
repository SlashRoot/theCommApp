'''
Functions for extracting information from SIP / VOIP calls.
Attempts to be less gnostic with providers and rely instead on the implementations in services.py
'''

from the_comm_app.models import PhoneCall, CommunicationInvolvement

import datetime
import json
import logging
import re

comm_logger = logging.getLogger('comm')


def call_object_from_call_info(call_info):
    '''
    Takes a standardized call info dict and extracts call objects from it. 
    '''
    #First let's get the call id of the call we're being asked about.    
    call_id = call_info['call_id']

    #Let's see if we already know about this call.
    try:
        call = PhoneCall.objects.get(call_id=call_id) #Set call to a phone call matching the call_id we just got.
        return call #We already know about this call.  Let's just dispense with the formalities and return the call.
    except PhoneCall.DoesNotExist, e: #This call does not exist in our database.
        
        comm_logger.info('NEW CALL %s (%s)' % (call_id, call_info['provider']))
        
        #Start to populate our PhoneCall object                
        call = PhoneCall(
                         service        = call_info['provider'].int,
                         account_id     = call_info['account_id'], #TODO: No.
                         call_id        = call_id, #We grabbed this above.
                         )
        
    #Now, increasing difficulty: let's handle the From and To numbers.
    
    #Make a dict of incoming numbers.
    #In the future we might have more than two - forwarded from, forwarded to, transfered from, transfered to, etc.
    incoming_numbers = {
                        'caller' : call_info['from_caller_id'],
                        'recipient' : call_info['to_caller_id'],                        
                        }
    
    
    phone_numbers = {} #This is going to be the dictionary of the phone numbers pertaining to this call.
    
    #Are either of these already in the system?
    #If not we're going to make a number for them.
    #The number can be assigned to a ContactInfo object later.
    
    # for (key, phone_number) in incoming_numbers.items(): #key will be 'caller', 'recipient', etc.  phone number will be the number.
    #     phone_numbers[key + '_nice'] = nicefy_number(phone_number)
            
    call.from_number = incoming_numbers['caller']
    call.to_number = incoming_numbers['recipient']
  
    call.save()
    
    # If this this is the first time we've seen the call marked completed, we'll set the ended date.
    if call_info['status'] == 'completed' and not call.ended:
        call.ended = datetime.datetime.now()

    return call
