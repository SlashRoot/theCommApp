from what_apps.utility.admin import autoregister
from django.contrib import admin


from models import PhoneCall

class PhoneCallAdmin(admin.ModelAdmin): 
    model = PhoneCall
    list_display = ('created', 'from_number')

admin.site.register(PhoneCall, PhoneCallAdmin)

autoregister('comm')