from django.contrib import admin
from .models import FarRecord, WraRecord


@admin.register(FarRecord)
class FarRecordAdmin(admin.ModelAdmin):
    list_display = (
        'far_record_id', 'facility', 'last_name', 'first_name', 'year_of_birth',
    )
    list_display_links = ('far_record_id',)
    list_filter = ('facility', 'sex', 'citizenship')
    fieldsets = (
        (None, {'fields': (
            ('far_record_id', 'facility', 'original_order',),
            'family_number',
            'far_line_id',
            ('last_name', 'first_name','other_names',),
            ('date_of_birth', 'year_of_birth',),
            ('sex', 'marital_status',),
            ('citizenship', 'alien_registration',),
            ('entry_type_code', 'entry_type',),
            'entry_category',
            'entry_facility',
            ('pre_evacuation_address', 'pre_evacuation_state',),
            'date_of_original_entry',
            ('departure_type_code', 'departure_type',),
            'departure_category',
            'departure_facility',
            'departure_date',
            'departure_state',
            'camp_address_original',
            ('camp_address_block', 'camp_address_barracks', 'camp_address_room',),
            'reference',
            'original_notes',
        )}),
    )

    def save_model(self, request, obj, form, change):
        # request.user is used by Revision
        obj.user = request.user
        super().save_model(request, obj, form, change)


@admin.register(WraRecord)
class WraRecordAdmin(admin.ModelAdmin):
    list_display = (
        'wra_record_id', 'facility', 'lastname', 'firstname', 'middleinitial', 'birthyear',
    )
    list_display_links = ('wra_record_id',)
    list_filter = ('facility', 'assemblycenter', 'birthcountry',)
    fieldsets = (
        (None, {'fields': (
            'wra_record_id',
            'facility',
            ('lastname', 'firstname', 'middleinitial'),
            'birthyear',
            'gender',
            'originalstate',
            ('familyno', 'individualno'),
            'notes',
            'assemblycenter',
            'originaladdress',
            'birthcountry',
            ('fatheroccupus', 'fatheroccupabr'),
            ('yearsschooljapan', 'gradejapan', 'schooldegree'),
            'yearofusarrival',
            ('timeinjapan', 'ageinjapan'),
            'militaryservice',
            'martitalstatus',
            'ethnicity',
            'birthplace',
            'citizenshipstatus',
            'highestgrade',
            'language',
            'religion',
            ('occupqual1', 'occupqual2', 'occupqual3'),
            ('occupotn1', 'occupotn2'),
            'wra_filenumber',
        )}),
    )
