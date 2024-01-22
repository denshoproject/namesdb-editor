from django import forms
from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.urls import reverse

from .admin_actions import export_as_csv_action
from . import converters
from .models import Facility, Location, FarRecord, FarPage, WraRecord
from .models import Person, PersonLocation
from .models import IreiRecord
from .models import Revision


admin.site.site_header = "Densho Names Registry Editor"
admin.site.site_title = "Densho Names Registry Editor"
#admin.site.index_title = "index title"


@admin.register(Revision)
class RevisionAdmin(admin.ModelAdmin):
    list_display = (
        'content_type',
        'object_id',
        'content_object',
        'username',
        'timestamp',
        'note',
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
        'note',
        'diff',
    )
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp','content_object','content_type','username','object_id','note','diff',)
    fieldsets = (
        (None, {'fields': (
            ('timestamp', 'content_object'),
            ('content_type', 'object_id'),
            ('username'),
            'diff',
            'note',
        )}),
    )


class RevisionInline(GenericTabularInline):
    model = Revision
    ordering = ('-timestamp',)
    extra = 0
    show_change_link = True
    readonly_fields = ('timestamp',)
    max_num=5
    fields = (
        'timestamp', 'diff', 'username', 'note',
    )

    def has_add_permission(self, request, obj): return False
    def has_change_permission(self, request, obj): return False
    def has_delete_permission(self, request, obj): return False


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    actions = [export_as_csv_action()]
    list_display = (
        'facility_id', 'facility_type', 'title',
    )
    list_display_links = ('facility_id',)
    list_filter = ('facility_type',)
    search_fields = (
        'facility_id', 'facility_type', 'title',
    )
    fieldsets = (
        (None, {'fields': (
            ('facility_id', 'facility_type'),
            'title',
            'location_label',
             ('location_lat', 'location_lng'),
            'tgn_id',
            #('encyc_title', 'encyc_url'),
        )}),
    )


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    actions = [export_as_csv_action()]
    list_display = (
        'id',
        'address',
        'lat',
        'lng',
        'facility',
    )
    list_display_links = ('id', 'address',)
    list_filter = ()
    search_fields = (
        'lat',
        'lng',
        'address',
        'address_components',
        'notes',
    )
    fieldsets = (
        (None, {'fields': (
            'address',
            'address_components',
            ('lat', 'lng'),
            'facility',
            'notes',
        )}),
    )


class FarRecordAdminForm(forms.ModelForm):
    """Adds link to Person in Person field help_text"""
    def __init__(self, *args, **kwargs):
        super(FarRecordAdminForm, self).__init__(*args, **kwargs)
        person = self.instance.person
        if person:
            url = person.admin_url()
            name = person.preferred_name
            self.fields['person'].help_text = f'&#8618; <a href="{url}">{name}</a>'

    """Add Revision `note` field to autogenerated FarRecordForm"""
    note = forms.CharField(
        required=True, label='Revision notes',
        widget=forms.Textarea(attrs={"rows":"3"}),
        help_text='Briefly explain the <b>reason</b> for these edits, including provenance if available.'
    )

    class Meta:
        model = FarRecord
        fields = []


@admin.register(FarRecord)
class FarRecordAdmin(admin.ModelAdmin):
    actions = [export_as_csv_action()]
    list_display = (
        'far_record_id', 'facility', 'far_page', 'family_number', 'last_name', 'first_name',
        'year_of_birth',
    )
    list_display_links = ('far_record_id',)
    list_filter = ('facility', 'sex', 'citizenship')
    search_fields = (
        'far_record_id', 'facility', 'far_page', 'original_order', 'family_number', 'far_line_id',
        'last_name', 'first_name', 'other_names',
        'date_of_birth', 'year_of_birth',
        'sex', 'marital_status', 'citizenship', 'alien_registration_no',
        'entry_type_code', 'entry_type', 'entry_category', 'entry_facility',
        'pre_evacuation_address', 'pre_evacuation_state', 'date_of_original_entry',
        'departure_type_code', 'departure_type', 'departure_category',
        'departure_facility', 'departure_date', 'departure_destination', 'departure_state',
        'camp_address_original', 'camp_address_block', 'camp_address_barracks',
        'camp_address_room', 'reference', 'original_notes',
    )
    autocomplete_fields = ['person',]
    readonly_fields = ('timestamp','far_record_id','facility','far_page', 'original_order','far_line_id',)
    inlines = (RevisionInline,)
    form = FarRecordAdminForm
    fieldsets = (
        (None, {'fields': (
            ('person', 'timestamp'),
            ('far_record_id', 'facility', 'far_page', 'original_order',),
            'family_number',
            'far_line_id',
            ('last_name', 'first_name','other_names',),
            ('date_of_birth', 'year_of_birth',),
            ('sex', 'marital_status',),
            ('citizenship', 'alien_registration_no',),
            ('entry_type_code', 'entry_type',),
            'entry_category',
            'entry_facility',
            ('pre_evacuation_address', 'pre_evacuation_state',),
            'date_of_original_entry',
            ('departure_type_code', 'departure_type',),
            'departure_category',
            'departure_facility',
            'departure_date',
            ('departure_destination', 'departure_state',),
            'camp_address_original',
            ('camp_address_block', 'camp_address_barracks', 'camp_address_room',),
            'reference',
            'original_notes',
            'note',
        )}),
    )

    def get_form(self, request, obj=None, **kwargs):
        # Add link to far_page field.
        # Can't do this in FarRecordAdminForm.__init__ bc field is readonly
        far_page = FarPage.objects.get(facility=obj.facility, page=obj.far_page)
        url = reverse(
            f'admin:{far_page._meta.app_label}_{far_page._meta.model_name}_change',
            args=[far_page.file_id]
        )
        help_texts = {
            'far_page': f'<a href="{url}">Page in FAR ledger</a>, recorded in original ledger'
        }
        kwargs.update({'help_texts': help_texts})
        return super().get_form(request, obj, **kwargs)

    def save_model(self, request, obj, form, change):
        # request.user and notes are used by Revision
        obj.user = request.user
        obj.note = form.cleaned_data['note']
        super().save_model(request, obj, form, change)


class FarPageAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(FarPageAdminForm, self).__init__(*args, **kwargs)


@admin.register(FarPage)
class FarPageAdmin(admin.ModelAdmin):
    actions = [export_as_csv_action()]
    list_display = (
        'facility', 'page', 'file_id', 'file_label',
    )
    list_display_links = ('file_id',)
    list_filter = ('facility',)
    ordering = ('facility', 'page',)
    search_fields = (
        'file_id', 'file_label',
    )
    readonly_fields = ('facility', 'page', 'file_id', 'file_label',)
    form = FarPageAdminForm
    fieldsets = (
        (None, {'fields': (
            'facility', 'page', 'file_id', 'file_label',
        )}),
    )

    def get_form(self, request, obj=None, **kwargs):
        # Add DDR link to file_id field.
        # Can't do this in FarPageAdminForm.__init__ bc field is readonly
        url = f'https://ddr.densho.org/{obj.file_id}/'
        help_texts = {
            'file_id': f'<a href="{url}">DDR file page</a>'
        }
        kwargs.update({'help_texts': help_texts})
        return super().get_form(request, obj, **kwargs)


class WraRecordAdminForm(forms.ModelForm):
    """Adds link to Person in Person field help_text"""
    def __init__(self, *args, **kwargs):
        super(WraRecordAdminForm, self).__init__(*args, **kwargs)
        person = self.instance.person
        if person:
            url = person.admin_url()
            name = person.preferred_name
            self.fields['person'].help_text = f'&#8618; <a href="{url}">{name}</a>'


@admin.register(WraRecord)
class WraRecordAdmin(admin.ModelAdmin):
    actions = [export_as_csv_action()]
    list_display = (
        'wra_record_id', 'facility', 'familyno',
        'lastname', 'firstname', 'middleinitial', 'birthyear',
    )
    list_display_links = ('wra_record_id',)
    list_filter = ('facility', 'assemblycenter', 'birthcountry',)
    search_fields = (
        'wra_record_id', 'facility',
        'lastname', 'firstname', 'middleinitial',
        'birthyear', 'gender', 'originalstate', 'familyno', 'individualno',
        'notes', 'assemblycenter', 'originaladdress', 'birthcountry',
        'fatheroccupus', 'fatheroccupabr', 'yearsschooljapan', 'gradejapan',
        'schooldegree', 'yearofusarrival', 'timeinjapan', 'ageinjapan',
        'militaryservice', 'maritalstatus', 'ethnicity', 'birthplace',
        'citizenshipstatus', 'highestgrade', 'language', 'religion',
        'occupqual1', 'occupqual2', 'occupqual3', 'occuppotn1', 'occuppotn2',
    )
    autocomplete_fields = ['person',]
    readonly_fields = ('timestamp','wra_record_id', 'wra_filenumber','facility',)
    inlines = (RevisionInline,)
    form = WraRecordAdminForm
    fieldsets = (
        (None, {'fields': (
            ('person', 'timestamp'),
            ('wra_record_id', 'wra_filenumber'),
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
            'maritalstatus',
            'ethnicity',
            'birthplace',
            'citizenshipstatus',
            'highestgrade',
            'language',
            'religion',
            ('occupqual1', 'occupqual2', 'occupqual3'),
            ('occuppotn1', 'occuppotn2'),
        )}),
    )

    def save_model(self, request, obj, form, change):
        # request.user and notes are used by Revision
        obj.user = request.user
        obj.note = form.cleaned_data['note']
        super().save_model(request, obj, form, change)


class IreiRecordAdminForm(forms.ModelForm):
    """Adds link to Person in Person field help_text"""
    def __init__(self, *args, **kwargs):
        super(IreiRecordAdminForm, self).__init__(*args, **kwargs)
        person = self.instance.person
        if person:
            url = person.admin_url()
            name = person.preferred_name
            self.fields['person'].help_text = f'&#8618; <a href="{url}">{name}</a>'

@admin.register(IreiRecord)
class IreiRecordAdmin(admin.ModelAdmin):
    actions = [export_as_csv_action()]
    list_display = (
        'person', 'irei_id',
        'name',
        'lastname', 'firstname', 'middlename',
        'birthday',
        'camps',
        'fetch_ts', 'timestamp',
    )
    list_display_links = ('irei_id', 'name',)
    list_filter = ('fetch_ts', 'timestamp',)
    date_hierarchy = 'birthdate'
    search_fields = (
        # Enabling search on `person` causes error:
        #     "Related Field got invalid lookup: icontains"
        #'person',
        'irei_id',
        'name', 'lastname', 'firstname', 'middlename',
        'birthday',
        'camps',
    )
    # Without autocomplete on `person`, Django admin will try to load
    # *all* Person records into a dropdown menu, severely affecting performance!
    autocomplete_fields = ['person',]
    readonly_fields = (
        'irei_id',
        'name', 'lastname','firstname','middlename',
        'birthday', 'year',
        'camps',
        'fetch_ts', 'timestamp',
    )
    #form = IreiRecordAdminForm
    fieldsets = (
        (None, {'fields': (
            ('irei_id', 'person'),
        )}),
        (None, {'fields': (
            'name',
            ('lastname', 'firstname', 'middlename'),
            ('birthday', 'year'),
            'camps',
            ('fetch_ts', 'timestamp'),
        )}),
    )

    def save_model(self, request, obj, form, change):
        # request.user and notes are used by Revision
        obj.user = request.user
        obj.note = ''
        super().save_model(request, obj, form, change)


class PersonLocationInline(admin.TabularInline):
    model = PersonLocation
    ordering = ('sort_start',)
    extra = 0
    show_change_link = True
    fields = (
        'person',
        'location', 'facility', 'facility_address',
        'entry_date', 'exit_date',
    )
    #autocomplete_fields = ['person',]

    def has_add_permission(self, request, obj): return False
    def has_change_permission(self, request, obj): return False
    def has_delete_permission(self, request, obj): return False


class PersonLocationAdminForm(forms.ModelForm):
    """Adds link to Person in Person field help_text"""
    def __init__(self, *args, **kwargs):
        super(PersonLocationAdminForm, self).__init__(*args, **kwargs)
        person = self.instance.person
        if person:
            url = person.admin_url()
            name = person.preferred_name
            self.fields['person'].help_text = f'&#8618; <a href="{url}">{name}</a>'

@admin.register(PersonLocation)
class PersonLocationAdmin(admin.ModelAdmin):
    list_display = (
        'person', 'location',
        'facility', 'facility_address',
        'entry_date', 'exit_date', 'sort_start', 'sort_end',
    )
    #list_display_links = ('title',)
    list_filter = ('facility',)
    #date_hierarchy = 'entry_date'
    search_fields = (
        'facility_address',
        'notes',
    )
    autocomplete_fields = ['person','facility',]
    fieldsets = (
        (None, {'fields': (
            'person',
            'location',
            ('facility', 'facility_address'),
            ('entry_date', 'sort_start'),
            ('exit_date', 'sort_end'),
            'notes',
        )}),
    )


class FarRecordInline(admin.TabularInline):
    model = FarRecord
    extra = 0
    show_change_link = True
    fields = (
        'far_record_id', 'facility', 'far_page', 'original_order',
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


class IreiRecordInline(admin.TabularInline):
    model = IreiRecord
    extra = 0
    show_change_link = True
    fields = (
        'irei_id',
        'name', 'birthday',
        'lastname', 'firstname', 'middlename',
    )

    def has_add_permission(self, request, obj): return False
    def has_change_permission(self, request, obj): return False
    def has_delete_permission(self, request, obj): return False


class PersonAdminForm(forms.ModelForm):
    """Add Revision `note` field to autogenerated PersonForm"""
    note = forms.CharField(
        required=True, label='Revision notes',
        widget=forms.Textarea(attrs={"rows":"3"}),
        help_text='Briefly explain the <b>reason</b> for these edits, including provenance if available.'
    )

    class Meta:
        model = Person
        fields = []


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    actions = [export_as_csv_action()]
    list_display = (
        'nr_id', 'family_name', 'given_name', 'preferred_name', 'gender',
        'birth_date', 'wra_family_no',
    )
    list_display_links = ('nr_id', 'family_name', 'given_name',)
    list_filter = (
        'gender', 'citizenship',
        'preexclusion_residence_state', 'postexclusion_residence_state',
    )
    date_hierarchy = 'birth_date'
    search_fields = (
            'nr_id', 'timestamp',
            'family_name', 'given_name',
            'given_name_alt',
            'other_names',
            'middle_name',
            'prefix_name', 'suffix_name',
            'jp_name',
            'preferred_name',
            'birth_date', 'birth_date_text',
            'birth_place',
            'death_date', 'death_date_text',
            'wra_family_no', 'wra_individual_no',
            'citizenship', 'alien_registration_no',
            'gender',
            'preexclusion_residence_city', 'preexclusion_residence_state',
            'postexclusion_residence_city', 'postexclusion_residence_state',
            'exclusion_order_title', 'exclusion_order_id',
    )
    inlines = [
        PersonLocationInline,
        FarRecordInline, WraRecordInline, RevisionInline,
        IreiRecordInline,
    ]
    readonly_fields = ('nr_id', 'timestamp', 'rolepeople_text')
    fieldsets = (
        (None, {'fields': (
            ('nr_id', 'timestamp'),
            'rolepeople_text',
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
            'note',
        )}),
    )
    form = PersonAdminForm

    @admin.display(description="web form/CSV text")
    def rolepeople_text(self, instance):
        # None can't be concatenated w str
        family_name = getattr(instance, 'family_name', '')
        given_name  = getattr(instance, 'given_name', '')
        middle_name = getattr(instance, 'middle_name', '')
        namepart = f'{family_name}, {given_name} {middle_name}'.strip()
        # some parts may be None but we don't want "None" in the name
        namepart = namepart.replace('None', '').replace('  ', ' ')
        return converters.rolepeople_to_text([{
            'namepart': namepart, 'nr_id': instance.nr_id,
        }]) + ';'

    def save_model(self, request, obj, form, change):
        # request.user and notes are used by Revision
        obj.user = request.user
        obj.note = form.cleaned_data['note']
        super().save_model(request, obj, form, change)
