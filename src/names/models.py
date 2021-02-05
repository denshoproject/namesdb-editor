import difflib

from django.db import models
from django.utils import timezone

from names import csvfile,fileio


class NamesRouter:
    """Write all Names DB data to separate DATABASES['names'] database.
    """
    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'names':
            return 'names'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'names':
            return 'names'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if ((obj1._meta.app_label == 'names') or
            (obj2._meta.app_label == 'names')):
           return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'names':
            return db == 'names'
        return None


class Facility(models.Model):
    facility_id   = models.CharField(max_length=30, primary_key=True, verbose_name='Facility ID',   help_text='ID of facility where detained')
    facility_type = models.CharField(max_length=30,                   verbose_name='Facility Type', help_text='Type of facility where detained')
    facility_name = models.CharField(max_length=30,                   verbose_name='Facility Name', help_text='Name of facility where detained')

    class Meta:
        verbose_name = 'Facility'
        verbose_name_plural = 'Facilities'


class Person(models.Model):
    nr_id                         = models.CharField(max_length=30,          verbose_name='Names Registry ID',         help_text='Names Registry unique identifier')
    family_name                   = models.CharField(max_length=30,          verbose_name='Last Name',                 help_text='Preferred family or last name')
    given_name                    = models.CharField(max_length=30,          verbose_name='First Name',                help_text='Preferred given or first name')
    given_name_alt                = models.TextField(max_length=30, blank=True, null=True, verbose_name='Alternative First Names',   help_text='List of alternative first names')
    other_names                   = models.TextField(max_length=30, blank=True, null=True, verbose_name='Other Names',               help_text='List of other names')
    middle_name                   = models.CharField(max_length=30, blank=True, null=True, verbose_name='Middle Name',               help_text='Middle name or initial')
    prefix_name                   = models.CharField(max_length=30, blank=True, null=True, verbose_name='Name Prefix',               help_text='Professional/titular prefix. E.g., "Dr.", "Rev."')
    suffix_name                   = models.CharField(max_length=30, blank=True, null=True, verbose_name='Name Suffix',               help_text='Name suffix. E.g., "Jr.", "Esq."')
    jp_name                       = models.CharField(max_length=30, blank=True, null=True, verbose_name='Japanese Name',             help_text='Name in kana')
    preferred_name                = models.CharField(max_length=30,          verbose_name='Preferred Full Name',       help_text='Preferred form of full name for display')
    birth_date                    = models.DateField(max_length=30, blank=True, null=True, verbose_name='Date of Birth',             help_text='Full birthdate')
    birth_date_text               = models.CharField(max_length=30, blank=True, null=True, verbose_name='Birthdate Text',            help_text='Text representation of birthdate, if necessary')
    birth_place                   = models.CharField(max_length=30, blank=True, null=True, verbose_name='Birthplace',                help_text='Place of birth')
    death_date                    = models.DateField(max_length=30, blank=True, null=True, verbose_name='Date of Death',             help_text='Date of death')
    death_date_text               = models.CharField(max_length=30, blank=True, null=True, verbose_name='Death Date Text',           help_text='Text representation of death date, if necessary')
    wra_family_no                 = models.CharField(max_length=30, blank=True, null=True, verbose_name='Family Number',             help_text='WRA-assigned family number')
    wra_individual_no             = models.CharField(max_length=30, blank=True, null=True, verbose_name='Individual Number',         help_text='WRA-assigned individual number')
    citizenship                   = models.CharField(max_length=30,          verbose_name='Country of Citizenship',    help_text='Country of citizenship')
    alien_registration_no         = models.CharField(max_length=30, blank=True, null=True, verbose_name='Alien Registration Number', help_text='INS-assigned alien registration number')
    gender                        = models.CharField(max_length=30,          verbose_name='Gender',                    help_text='Gender')
    preexclusion_residence_city   = models.CharField(max_length=30, blank=True, null=True, verbose_name='Pre-exclusion City',        help_text='Last city of residence prior to exclusion')
    preexclusion_residence_state  = models.CharField(max_length=30, blank=True, null=True, verbose_name='Pre-exclusion State',       help_text='Last state of residence prior to exclusion')
    postexclusion_residence_city  = models.CharField(max_length=30, blank=True, null=True, verbose_name='Post-detention City',       help_text='City of residence immediately following detention')
    postexclusion_residence_state = models.CharField(max_length=30, blank=True, null=True, verbose_name='Post-detention State',      help_text='State of residence immediately following detention')
    exclusion_order_title         = models.CharField(max_length=30, blank=True, null=True, verbose_name='Exclusion Order',           help_text='Name of U.S. Army exclusion order')
    exclusion_order_id            = models.CharField(max_length=30, blank=True, null=True, verbose_name='Exclusion Order ID',        help_text='Order ID ')
#    record_id		blank=1	Record ID	ID of related record
#    record_type		blank=1	Record Source	Type of related record. e.g., 'far', 'wra' 
    timestamp                     = models.DateTimeField(auto_now_add=True,   verbose_name='Last Updated')
    facility = models.ManyToManyField(Facility, through='PersonFacility')

    class Meta:
        verbose_name = 'Person'
        verbose_name_plural = 'People'

    def __repr__(self):
        return '<{}(nr_id={})>'.format(
            self.__class__.__name__, self.nr_id
        )

    def __str__(self):
        return '{} ({})'.format(
            self.preferred_name, self.nr_id
        )

    def save(self, username=None, *args, **kwargs):
        # request.user added to obj in names.admin.FarRecordAdmin.save_model
        if getattr(self, 'user', None):
            username = getattr(self, 'user').username
        # get existing record
        try:
            old = Person.objects.get(nr_id=self.nr_id)
        except Person.DoesNotExist:
            old = None
        # should be field in admin
        note = ''
        r = Revision(
            model=self.__class__.__name__,
            record_id=self.nr_id,
            username=username, note=note, diff=make_diff(old, self)
        )
        r.save()
        self.timestamp = timezone.now()
        super(Person, self).save()

    def revisions(self):
        return Revision.objects.filter(model='persopn', record_id=self.nr_id)


class PersonFacility(models.Model):
    person     = models.ForeignKey(Person, on_delete=models.DO_NOTHING)
    facility   = models.ForeignKey(Facility, on_delete=models.DO_NOTHING)
    entry_date = models.DateField(blank=1, verbose_name='Facility Entry Date', help_text='Date of entry to detention facility')
    exit_date  = models.DateField(blank=1, verbose_name='Facility Exit Date',  help_text='Date of exit from detention facility')


class FarRecord(models.Model):
    far_record_id                  = models.CharField(max_length=255, primary_key=1, verbose_name='FAR Record ID', help_text="Derived from FAR ledger id + line id ('original_order')")
    facility                = models.CharField(max_length=255,          verbose_name='Facility', help_text='Identifier of WRA facility')
    original_order          = models.CharField(max_length=255, blank=1, verbose_name='Original Order', help_text='Absolute line number in physical FAR ledger')
    family_number           = models.CharField(max_length=255, blank=1, verbose_name='WRA Family Number', help_text='WRA-assigned family number')
    far_line_id             = models.CharField(max_length=255, blank=1, verbose_name='FAR Line Number', help_text='Line number in FAR ledger, recorded in original ledger')
    last_name               = models.CharField(max_length=255, blank=1, verbose_name='Last Name', help_text='Last name corrected by transcription team')
    first_name              = models.CharField(max_length=255, blank=1, verbose_name='First Name', help_text='First name corrected by transcription team')
    other_names             = models.CharField(max_length=255, blank=1, verbose_name='Other Names', help_text='Alternate first names')
    date_of_birth           = models.CharField(max_length=255, blank=1, verbose_name='Birthdate', help_text='Full birth date')
    year_of_birth           = models.CharField(max_length=255, blank=1, verbose_name='Year of Birth', help_text='Year of birth')
    sex                     = models.CharField(max_length=255,          verbose_name='Gender', help_text='Gender identifier')
    marital_status          = models.CharField(max_length=255, blank=1, verbose_name='Marital Status', help_text='Marital status')
    citizenship             = models.CharField(max_length=255,          verbose_name='Citizenship Status', help_text='Citizenship status')
    alien_registration      = models.CharField(max_length=255, blank=1, verbose_name='Alien Registration Number', help_text='INS-assigned Alien Registration number')
    entry_type_code         = models.CharField(max_length=255, blank=1, verbose_name='Entry Type (Coded)', help_text='Coded type of original admission and assignment to facility')
    entry_type              = models.CharField(max_length=255, blank=1, verbose_name='Entry Type', help_text='Normalized type of original entry')
    entry_category          = models.CharField(max_length=255, blank=1, verbose_name='Entry Category', help_text='Category of entry type; assigned by Densho')
    entry_facility          = models.CharField(max_length=255, blank=1, verbose_name='Entry Facility', help_text='Last facility prior to entry')
    pre_evacuation_address  = models.CharField(max_length=255, blank=1, verbose_name='Pre-exclusion Address', help_text='Address at time of removal; city and state')
    pre_evacuation_state    = models.CharField(max_length=255, blank=1, verbose_name='Pre-exclusion State', help_text='Address at time of removal, state-only')
    date_of_original_entry  = models.CharField(max_length=255, blank=1, verbose_name='Entry Date', help_text='Date of arrival at facility')
    departure_type_code     = models.CharField(max_length=255, blank=1, verbose_name='Departure Type (Coded)', help_text='Coded type of leave or reason for departure from facility')
    departure_type          = models.CharField(max_length=255, blank=1, verbose_name='Departure Type', help_text='Normalized type of final departure')
    departure_category      = models.CharField(max_length=255, blank=1, verbose_name='Departure Category', help_text='Category of departure type')
    departure_facility      = models.CharField(max_length=255, blank=1, verbose_name='Departure Facility', help_text='Departure facility, if applicable')
    departure_date          = models.CharField(max_length=255, blank=1, verbose_name='Departure Date', help_text='Date of departure from facility')
    departure_state         = models.CharField(max_length=255, blank=1, verbose_name='Departure Destination', help_text='Destination after departure; state-only')
    camp_address_original   = models.CharField(max_length=255, blank=1, verbose_name='Camp Address', help_text='Physical address in camp in the form, "Block-Barrack-Room"')
    camp_address_block      = models.CharField(max_length=255, blank=1, verbose_name='Camp Address Block', help_text='Block identifier of camp address')
    camp_address_barracks   = models.CharField(max_length=255, blank=1, verbose_name='Camp Address Barrack', help_text='Barrack identifier of camp address')
    camp_address_room       = models.CharField(max_length=255, blank=1, verbose_name='Camp Address Room', help_text='Room identifier of camp address')
    reference               = models.CharField(max_length=255, blank=1, verbose_name='Internal FAR Reference', help_text='Pointer to another row in the roster; page number in source pdf and the original order in the consolidated roster for the camp')
    original_notes          = models.CharField(max_length=255, blank=1, verbose_name='Original Notes', help_text='Notes from original statistics section recorder, often a reference to another name in the roster')
    person = models.ForeignKey(Person, on_delete=models.DO_NOTHING, blank=1, null=1)
    timestamp               = models.DateTimeField(auto_now_add=True, verbose_name='Last Updated')

    class Meta:
        verbose_name = "FAR Record"

    def __repr__(self):
        return '<{}(far_record_id={})>'.format(
            self.__class__.__name__, self.far_record_id
        )

    def __str__(self):
        return '{} {} ({}) {} {}'.format(
            self.last_name, self.first_name, self.sex, self.facility, self.far_record_id
        )

    def save(self, username=None, *args, **kwargs):
        # request.user added to obj in names.admin.FarRecordAdmin.save_model
        if getattr(self, 'user', None):
            username = getattr(self, 'user').username
        # get existing record
        try:
            old = FarRecord.objects.get(far_record_id=self.far_record_id)
        except FarRecord.DoesNotExist:
            old = None
        # should be field in admin
        note = ''
        r = Revision(
            model=self.__class__.__name__,
            record_id=self.far_record_id,
            username=username, note=note, diff=make_diff(old, self)
        )
        r.save()
        self.timestamp = timezone.now()
        super(FarRecord, self).save()

    def revisions(self):
        return Revision.objects.filter(model='far', record_id=self.far_record_id)


class WraRecord(models.Model):
    wra_record_id     = models.IntegerField(primary_key=1,        verbose_name='WRA Form 26 ID', help_text='Unique identifier; absolute row in original RG210.JAPAN.WRA26 datafile')
    facility          = models.CharField(max_length=255,          verbose_name='Facility identifier', help_text='Facility identifier')
    lastname          = models.CharField(max_length=255, blank=1, verbose_name='Last name, truncated to 10 chars', help_text='Last name, truncated to 10 chars')
    firstname         = models.CharField(max_length=255, blank=1, verbose_name='First name, truncated to 8 chars', help_text='First name, truncated to 8 chars')
    middleinitial     = models.CharField(max_length=255, blank=1, verbose_name='Middle initial', help_text='Middle initial')
    birthyear         = models.CharField(max_length=255, blank=1, verbose_name='Year of birth', help_text='Year of birth')
    gender            = models.CharField(max_length=255, blank=1, verbose_name='Gender', help_text='Gender')
    originalstate     = models.CharField(max_length=255, blank=1, verbose_name='State of residence immediately prior to census', help_text='State of residence immediately prior to census')
    familyno          = models.CharField(max_length=255, blank=1, verbose_name='WRA-assigned family identifier', help_text='WRA-assigned family identifier')
    individualno      = models.CharField(max_length=255, blank=1, verbose_name='Family identifier + alpha char by birthdate', help_text='Family identifier + alpha char by birthdate')
    notes             = models.CharField(max_length=255, blank=1, verbose_name='Notes added by Densho during processing', help_text='Notes added by Densho during processing')
    assemblycenter    = models.CharField(max_length=255,          verbose_name='Assembly center prior to camp', help_text='Assembly center prior to camp')
    originaladdress   = models.CharField(max_length=255, blank=1, verbose_name='County/city + state of pre-exclusion address (coded)', help_text='County/city + state of pre-exclusion address; coded by WRA')
    birthcountry      = models.CharField(max_length=255,          verbose_name='Birth countries of father and mother (coded)', help_text='Birth countries of father and mother; coded by WRA')
    fatheroccupus     = models.CharField(max_length=255, blank=1, verbose_name="Father's occupation in the US (coded)", help_text="Father's occupation in the US; coded by WRA")
    fatheroccupabr    = models.CharField(max_length=255, blank=1, verbose_name="Father's occupation pre-emigration (coded)", help_text="Father's occupation pre-emigration; coded by WRA")
    yearsschooljapan  = models.CharField(max_length=255, blank=1, verbose_name='Years of school attended in Japan', help_text='Years of school attended in Japan')
    gradejapan        = models.CharField(max_length=255, blank=1, verbose_name='Highest grade of schooling attained in Japan (coded)', help_text='Highest grade of schooling attained in Japan; coded by WRA')
    schooldegree      = models.CharField(max_length=255, blank=1, verbose_name='Highest educational degree attained (coded)', help_text='Highest educational degree attained; coded by WRA')
    yearofusarrival   = models.CharField(max_length=255, blank=1, verbose_name='Year of immigration to US, if applicable', help_text='Year of immigration to US, if applicable')
    timeinjapan       = models.CharField(max_length=255, blank=1, verbose_name='Time in Japan', help_text='Description of time in Japan')
    ageinjapan        = models.CharField(max_length=255, blank=1, verbose_name='Oldest age visiting or living in Japan', help_text='Age while visiting or living in Japan')
    militaryservice   = models.CharField(max_length=255, blank=1, verbose_name='Military service, pensions and disabilities', help_text='Military service, public assistance status and major disabilities')
    martitalstatus    = models.CharField(max_length=255, blank=1, verbose_name='Marital status', help_text='Marital status')
    ethnicity         = models.CharField(max_length=255, blank=1, verbose_name='Ethnicity', help_text='Ethnicity')
    birthplace        = models.CharField(max_length=255, blank=1, verbose_name='Birthplace', help_text='Birthplace')
    citizenshipstatus = models.CharField(max_length=255, blank=1, verbose_name='Citizenship status', help_text='Citizenship status')
    highestgrade      = models.CharField(max_length=255, blank=1, verbose_name='Highest degree achieved', help_text='Highest degree achieved')
    language          = models.CharField(max_length=255, blank=1, verbose_name='Languages spoken', help_text='Languages spoken')
    religion          = models.CharField(max_length=255, blank=1, verbose_name='Religion', help_text='Religion')
    occupqual1        = models.CharField(max_length=255, blank=1, verbose_name='Primary qualified occupation', help_text='Primary qualified occupation')
    occupqual2        = models.CharField(max_length=255, blank=1, verbose_name='Secondary qualified occupation', help_text='Secondary qualified occupation')
    occupqual3        = models.CharField(max_length=255, blank=1, verbose_name='Tertiary qualified occupation', help_text='Tertiary qualified occupation')
    occupotn1         = models.CharField(max_length=255, blank=1, verbose_name='Primary potential occupation', help_text='Primary potential occupation')
    occupotn2         = models.CharField(max_length=255, blank=1, verbose_name='Secondary potential occupation', help_text='Secondary potential occupation')
    wra_filenumber    = models.CharField(max_length=255,          verbose_name='WRA Filenumber', help_text='WRA-assigned 6-digit filenumber identifier')
    person = models.ForeignKey(Person, on_delete=models.DO_NOTHING, blank=1, null=1)
    timestamp         = models.DateTimeField(auto_now_add=True,   verbose_name='Last Updated')

    class Meta:
        verbose_name = "WRA Record"

    def __repr__(self):
        return '<{}(wra_record_id={})>'.format(
            self.__class__.__name__, self.wra_record_id
        )

    def __str__(self):
        return '{} {} ({}) {} {}'.format(
            self.lastname, self.firstname, self.gender, self.facility,self.wra_record_id
        )

    def save(self, username=None, *args, **kwargs):
        # request.user added to obj in names.admin.WraRecordAdmin.save_model
        if getattr(self, 'user', None):
            username = getattr(self, 'user').username
        # get existing record
        try:
            old = WraRecord.objects.get(wra_record_id=self.wra_record_id)
        except WraRecord.DoesNotExist:
            old = None
        # should be field in admin
        note = ''
        r = Revision(
            model=self.__class__.__name__,
            record_id=self.wra_record_id,
            username=username, note=note, diff=make_diff(old, self)
        )
        r.save()
        self.timestamp = timezone.now()
        super(WraRecord, self).save()

    def revisions(self):
        return Revision.objects.filter(
            model='wra', record_id=self.wra_record_id
        )


class Revision(models.Model):
    model = models.CharField(max_length=30)
    record_id = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    username = models.CharField(max_length=30)
    note = models.CharField(max_length=255, blank=1)
    diff = models.TextField()

    def __repr__(self):
        return f'<Revision {self.timestamp} {self.username} {self.model} {self.record_id}>'

def jsonlines(obj):
    """JSONlines representation of object fields, for making diffs
    see https://jsonlines.org/
    """
    if obj:
        return [
            str( { fieldname: getattr(obj, fieldname) } )
            for fieldname in [
                field.name for field in obj._meta.fields
            ]
        ]
    return ''

def make_diff(old, new):
    if not old:
        # no diff for revision 0
        return ''
    return '\n'.join([
        line
        for line in difflib.unified_diff(
                jsonlines(old),
                jsonlines(new),
                fromfile=f'{old.timestamp}',
                tofile=f'{new.timestamp}',
                n=1
        )
    ]).replace('\n\n', '\n')


def load_csv(class_, csv_path, username, num_records=None):
    """Load records from CSV
    """
    start = timezone.now()
    for n,rowd in enumerate(csvfile.make_rowds(fileio.read_csv(csv_path))):
        if num_records and (n > num_records):
            break
        record = class_()
        try:
            idkey = 'far_record_id'
            x = rowd[idkey]
        except:
            idkey = 'wra_record_id'
        print(n,rowd[idkey])
        for key,val in rowd.items():
            if val:
                if isinstance(val, str):
                    val = val.replace('00:00:00', '')
                    val = val.strip()
                setattr(record, key, val)
        record.save(username=username, note='CSV import')
    elapsed = timezone.now() - start
    return n,elapsed


def load_facilities(csv_path):
    unique = list(set([
        rowd['facility']
        for rowd in csvfile.make_rowds(fileio.read_csv(csv_path))
    ]))
    dicts = sorted(
        [
            {'num':int(f.split('-')[0]), 'name':f.split('-')[1], 'id':f}
            for f in unique
        ],
        key=lambda x: x['num']
    )
    facilities = [
        Facility(
            facility_id=d['id'],
            facility_name=d['name'],
            facility_type='unspecified',
        )
        for d in dicts
    ]
    return facilities
