from the_comm_app.views.call_in_progress import AnswerViewSet
from the_comm_app.actions import CallBlast



class AnswerBlast(CallBlast):
    
    recipients = []
    
    def greeting(self):
        return "Hello."
    
    def __init__(self, *args, **kwargs):
        super(AnswerBlast, self).__init__(*args, **kwargs)


class PhoneCallAnswer(AnswerViewSet):
    
    action = AnswerBlast
    
    def reject(self):
        return False
    
    
    def get_or_create_nice_number(incoming_number):
        '''
        A wrapper over get_or_create for a PhoneNumber object.  Gets or Creates a new PhoneNumber from various formats.
        '''
        number_as_list = re.findall(r"[0-9]", incoming_number) #No matter the format, grab only the numbers.
        
        #An unknown caller will produce a completely blank number.
        if not number_as_list:
            return PhoneNumber.objects.get_blank_number()
        
        if number_as_list[0] == '1': #If the first digit is a 1, we'll just pop it off.
            number_as_list.pop(0)
        if not len(number_as_list) == 10: #Now we expect to have exactly ten digits.
            raise TypeError("I wasn't able to discern exactly ten digits from the phone number you gave me.  It was %s" % incoming_number)
        incoming_number = ''.join(number_as_list) #Now our incoming number is properly formatted.
    
        phone_number = "+1" + str(incoming_number)
        nice_number = phone_number[2:5] + "-" + phone_number[5:8] + "-" + phone_number[8:] #parse the number to look like django wants it: ex. 845-633-8330
        phone_number_object, new = PhoneNumber.objects.get_or_create(number = nice_number)
        return phone_number_object, new