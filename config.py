from what_apps.comm.factories import PhonecallFactory


def setup(from_number):
    PhonecallFactory.create(from_number=from_number)
    