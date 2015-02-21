class CallBlast(object):
    '''
    Place outgoing calls to a bunch of recipients, with each following the same action.
    '''
    pass

    def __init__(self, name):
        self.name = name
        
    def __unicode__(self):
        return self.name