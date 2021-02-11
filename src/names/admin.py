from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline

from .models import FarRecord, WraRecord, Person, Facility, PersonFacility
from .models import Revision


@admin.register(Revision)
class RevisionAdmin(admin.ModelAdmin):
    list_display = (
        'content_type',
        'object_id',
        'content_object',
        'username',
        'timestamp',
    )
    list_display_links = ('content_object',)
    list_filter = (
        'content_type',
        'username',
    )
    search_fields = (
        #'content_type',
        'object_id',
        #'content_object',
        'username',
        #'note',
        'diff',
    )
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp','content_object')
    fieldsets = (
        (None, {'fields': (
            ('timestamp', 'content_object'),
            ('content_type', 'object_id'),
            ('username'),
            'diff',
            #'note',
        )}),
    )


class RevisionInline(GenericTabularInline):
    model = Revision
    extra = 0
    show_change_link = True
    readonly_fields = ('timestamp',)
    max_num=5
    fields = (
        'timestamp', 'username', 'diff',
    )

    def has_add_permission(self, request, obj): return False
    def has_change_permission(self, request, obj): return False
    def has_delete_permission(self, request, obj): return False


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = (
        'facility_id', 'facility_type', 'facility_name',
    )
    list_display_links = ('facility_id',)
    list_filter = ('facility_type',)
    search_fields = (
        'facility_id', 'facility_type', 'facility_name',
    )
    fieldsets = (
        (None, {'fields': (
            'facility_id', 'facility_type', 'facility_name'
        )}),
    )


@admin.register(FarRecord)
class FarRecordAdmin(admin.ModelAdmin):
    list_display = (
        'far_record_id', 'facility', 'last_name', 'first_name', 'year_of_birth',
    )
    list_display_links = ('far_record_id',)
    list_filter = ('facility', 'sex', 'citizenship')
    search_fields = (
        'facility', 'original_order', 'family_number', 'far_line_id',
        'last_name', 'first_name', 'other_names',
        'date_of_birth', 'year_of_birth',
        'sex', 'marital_status', 'citizenship', 'alien_registration',
        'entry_type_code', 'entry_type', 'entry_category', 'entry_facility',
        'pre_evacuation_address', 'pre_evacuation_state', 'date_of_original_entry',
        'departure_type_code', 'departure_type', 'departure_category',
        'departure_facility', 'departure_date', 'departure_state',
        'camp_address_original', 'camp_address_block', 'camp_address_barracks',
        'camp_address_room', 'reference', 'original_notes',
    )
    autocomplete_fields = ['person',]
    readonly_fields = ('timestamp',)
    inlines = (RevisionInline,)
    fieldsets = (
        (None, {'fields': (
            ('person', 'timestamp'),
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
    search_fields = (
        'facility',
        'lastname', 'firstname', 'middleinitial',
        'birthyear', 'gender', 'originalstate', 'familyno', 'individualno',
        'notes', 'assemblycenter', 'originaladdress', 'birthcountry',
        'fatheroccupus', 'fatheroccupabr', 'yearsschooljapan', 'gradejapan',
        'schooldegree', 'yearofusarrival', 'timeinjapan', 'ageinjapan',
        'militaryservice', 'martitalstatus', 'ethnicity', 'birthplace',
        'citizenshipstatus', 'highestgrade', 'language', 'religion',
        'occupqual1', 'occupqual2', 'occupqual3', 'occupotn1', 'occupotn2',
        'wra_filenumber',
    )
    autocomplete_fields = ['person',]
    readonly_fields = ('timestamp',)
    inlines = (RevisionInline,)
    fieldsets = (
        (None, {'fields': (
            ('person', 'timestamp'),
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

    def save_model(self, request, obj, form, change):
        # request.user is used by Revision
        obj.user = request.user
        super().save_model(request, obj, form, change)


class PersonFacilityInline(admin.TabularInline):
    model = PersonFacility
    extra = 0
    show_change_link = True
    autocomplete_fields = ['facility',]

    def has_add_permission(self, request, obj): return True
    def has_change_permission(self, request, obj): return True
    def has_delete_permission(self, request, obj): return True


class FarRecordInline(admin.TabularInline):
    model = FarRecord
    extra = 0
    show_change_link = True
    fields = (
        'far_record_id', 'facility', 'original_order',
        'family_number',
        'far_line_id',
        'last_name', 'first_name','other_names',
        'date_of_birth', 'year_of_birth',
        'reference',
    )

    def has_add_permission(self, request, obj): return False
    def has_change_permission(self, request, obj): return False
    def has_delete_permission(self, request, obj): return False


class WraRecordInline(admin.TabularInline):
    model = WraRecord
    extra = 0
    show_change_link = True
    fields = (
        'wra_record_id',
        'facility',
        'lastname', 'firstname', 'middleinitial',
        'birthyear',
        'gender',
        'originalstate',
        'familyno', 'individualno',
        'assemblycenter',
        'originaladdress',
    )

    def has_add_permission(self, request, obj): return False
    def has_change_permission(self, request, obj): return False
    def has_delete_permission(self, request, obj): return False


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = (
        'nr_id', 'family_name', 'given_name', 'preferred_name', 'gender', 'birth_date',
    )
    list_display_links = ('nr_id', 'family_name', 'given_name',)
    list_filter = (
        'gender', 'citizenship',
        'preexclusion_residence_state', 'postexclusion_residence_state',
    )
    search_fields = (
        'family_name', 'given_name', 'given_name_alt', 'other_names',
        'middle_name', 'prefix_name', 'suffix_name', 'jp_name',
        'preferred_name',
    )
    inlines = [
        PersonFacilityInline, FarRecordInline, WraRecordInline, RevisionInline,
    ]
    readonly_fields = ('nr_id', 'timestamp',)
    fieldsets = (
        (None, {'fields': (
            ('nr_id', 'timestamp'),
            ('family_name', 'given_name'),
            'given_name_alt',
            'other_names',
            'middle_name',
            ('prefix_name', 'suffix_name'),
            'jp_name',
            'preferred_name',
            ('birth_date', 'birth_date_text'),
            'birth_place',
            ('death_date', 'death_date_text'),
            ('wra_family_no', 'wra_individual_no'),
            ('citizenship', 'alien_registration_no'),
            'gender',
            ('preexclusion_residence_city', 'preexclusion_residence_state'),
            ('postexclusion_residence_city', 'postexclusion_residence_state'),
            ('exclusion_order_title', 'exclusion_order_id'),
        )}),
    )

    def save_model(self, request, obj, form, change):
        # request.user is used by Revision
        obj.user = request.user
        super().save_model(request, obj, form, change)
