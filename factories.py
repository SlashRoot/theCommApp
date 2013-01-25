import factory
import datetime
from models import PhoneCall
from contact.factories import PhoneNumberFactory, PhoneServiceFactory


class PhonecallFactory(factory.Factory):
    FACTORY_FOR = PhoneCall
    service = factory.Subfactory(PhoneServiceFactory)
    call_id = factory.Sequence(lambda n: n)
    account_id = factory.Sequence(lambda n: n)
    dial = True
    from_number = factory.Subfactory(PhoneNumberFactory)
    to_number = factory.Subfactory(PhoneNumberFactory)
    ended = datetime.datetime.now()

    @class_method
    def _prepare(cls,
                 create,
                 from_number=None,
                 to_number=None,
                 from_user=None,
                 to_user=None,
                 is_twilio=False
                 **kwargs):

        if from_user and from_number:
            raise TypeError('Specify either from_user or from_number - not both.')

        if to_user and to_number:
            raise TypeError('Specify either to_user or to_number - not both.')

        if from_user:
            UserProfile.objects.get_or_create(user=from_user, defaults={'contact_info':ContactInfo.objects.create()})
            from_number = PhoneNumber.objects.get_or_create(owner=from_user.userprofile.contact_info, defaults=dict(number="+15551231234"))[0]
        else:

        if to_number:
            pass #We'll just use this.
        elif to_user:
            UserProfile.objects.get_or_create(user=to_user, defaults={'contact_info':ContactInfo.objects.create()})
            to_number = PhoneNumber.objects.create(owner=to_user.userprofile.contact_info, number="+15551231234")
        else:
            to_number = PhoneNumber.objects.get_or_create(type='mobile', number='+18455551234')[0]