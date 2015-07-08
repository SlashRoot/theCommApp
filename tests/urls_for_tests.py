from django.conf.urls import i18n, url
from django.views.decorators.csrf import csrf_exempt
from tests.examples import ExamplePhoneLine
from the_comm_app.plumbing import PhoneLine


urlpatterns = [
    url(r'^some_test_phone_line/(?P<phase_name>\w+)/',
        csrf_exempt(ExamplePhoneLine.as_view()),
        name=PhoneLine.name),
    url(r'^example_phone_line/(?P<phase_name>\w+)/',
        csrf_exempt(ExamplePhoneLine.as_view()),
        name=ExamplePhoneLine.name),
]