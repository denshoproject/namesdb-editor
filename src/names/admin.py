from django.contrib import admin
from .models import FarRecord, WraRecord


@admin.register(FarRecord)
class FarRecordAdmin(admin.ModelAdmin):
    list_display = (
        'dataset', 'pseudoid', 'camp', 'lastname', 'firstname', 'birthyear',
    )
    list_display_links = ('pseudoid',)
    list_filter = ('dataset', 'camp',)
    fieldsets = (
        ('Common', {'fields': (
            'dataset',
            'pseudoid',
            'camp',
            ('lastname', 'firstname'),
            'birthyear',
            'gender',
            'originalstate',
            ('familyno', 'individualno'),
            ('altfamilyid', 'altindividualid'),
            'ddrreference',
            'notes',
        )}),
        ('FAR', {'fields': (
            'othernames',
            'maritalstatus',
            'citizenship',
            'alienregistration',
            ('entrytype', 'entrydate'),
            'originalcity',
            ('departuretype', 'departuredate'),
            ('destinationcity', 'destinationstate'),
            'campaddress',
            'farlineid',
            'errors',
        )}),
    )

    def save_model(self, request, obj, form, change):
        # request.user is used by Revision
        obj.user = request.user
        super().save_model(request, obj, form, change)


@admin.register(WraRecord)
class WraRecordAdmin(admin.ModelAdmin):
    list_display = (
        'dataset', 'pseudoid', 'camp', 'lastname', 'firstname', 'birthyear',
    )
    list_display_links = ('pseudoid',)
    list_filter = ('dataset', 'assemblycenter', 'camp',)
    fieldsets = (
        ('Common', {'fields': (
            'dataset',
            'pseudoid',
            'camp',
            ('lastname', 'firstname'),
            'birthyear',
            'gender',
            'originalstate',
            ('familyno', 'individualno'),
            ('altfamilyid', 'altindividualid'),
            'ddrreference',
            'notes',
        )}),
        ('WRA', {'fields': (
            'assemblycenter',
            'originaladdress',
            'birthcountry',
            ('fatheroccupus', 'fatheroccupabr'),
            ('yearsschooljapan', 'gradejapan', 'schooldegree'),
            'yearofusarrival',
            ('timeinjapan', 'notimesinjapan', 'ageinjapan'),
            'militaryservice',
            'maritalstatus',
            'ethnicity',
            'birthplace',
            'citizenshipstatus',
            'highestgrade',
            'language',
            'religion',
            ('occupqual1', 'occupqual2', 'occupqual3'),
            ('occuppotn1', 'occuppotn2'),
            'filenumber',
            'errors',
        )}),
    )
