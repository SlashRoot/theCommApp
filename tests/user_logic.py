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