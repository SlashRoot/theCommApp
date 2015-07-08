from django.views.generic import View
from the_comm_app.plumbing import PhoneLine
from the_comm_app.voice.dispositions import ConferenceHoldingPattern, Voicemail
from the_comm_app.voice.voice_features import CallBlast


class ExampleCallBlast(CallBlast):

    recipients = ['+17773334444',
                  '+19991112222',
                  '+13335554444',
                  ]

class ExamplePhoneLine(PhoneLine, View):

    name = "example_phone_line"

    twilio_sid = "some_sid"
    twilio_auth = "some_auth"

    number_to_use_for_outgoing_calls = "+18883332222"

    greeting_text = "This is an awesome example phone line."
    disposition = [ConferenceHoldingPattern]
    features = [ExampleCallBlast]
    nobody_home = Voicemail