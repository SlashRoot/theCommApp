from the_comm_app.plumbing import PhoneLine
from the_comm_app.voice.features import CallBlast


class AnswerBlast(CallBlast):

    def greeting(self):
        return "Hello."
    
    def recipients(self):
        return []

    def reject_when(self, bad_numbers):
        return self.caller_number in bad_numbers



    def __init__(self, *args, **kwargs):
        super(AnswerBlast, self).__init__(*args, **kwargs)


class BirthAnswerBlast(AnswerBlast):

    def greeting(self):
        return "Thanks for inquiring about the birth!"

    def recipients(self):
        return some_list_of_people_interested_in_the_birth

    def make_call(self):
        place_call_to(self.recipients)


class BusinessAnswerBlast(AnswerBlast):

    def greeting(self):
        return "Very serious greeting"


class MyPhoneLine(PhoneLine):
    
    action = AnswerBlast
    
    def reject(self):
        return False

