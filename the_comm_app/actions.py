class ConnectCall(object):
    '''
    The proces of connection of zero or more calls to an existing call.
    ???
    '''

    def __init__(self, call, calls_to_connect=None):
        self.call = call
        self.calls_to_connect = calls_to_connect

    def connect(self):
        self.call.receive(self.calls_to_connect)


class SideEffect(object):
    '''
    1. You call someone.
    2. Some batty but beautiful behavior happens (or at least starts happening).
    3. You get a Response ("Thanks for calling the chocobo farm, etc.")

    This class is step 2.
    '''

    has_started = False

    def __iter__(self):
        raise StopIteration

    def __call__(self):
        return self.start()

    def start(self):
        self.has_started = True

    def is_finished(self):
        return False


class CallBlast(SideEffect):
    '''
    Place outgoing calls to a bunch of recipients, with each following the same action.
    '''
    def __init__(self, name, recipients=None):
        self.name = name
        self.recipients = recipients

    def __iter__(self):
        pass
        
    def __unicode__(self):
        return self.name