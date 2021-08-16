from datetime import datetime
import difflib
import json

from dateutil import parser
from requests.exceptions import ConnectionError
from tabulate import tabulate

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import connections, models
from django.urls import reverse
from django.utils import timezone

from names import csvfile,fileio,noidminter
from namesdb_public.models import Person as ESPerson, FIELDS_PERSON
from namesdb_public.models import FarRecord as ESFarRecord, FIELDS_FARRECORD
from namesdb_public.models import WraRecord as ESWraRecord, FIELDS_WRARECORD
from namesdb_public.models import FIELDS_BY_MODEL

ELASTICSEARCH_CLASSES = {
    'all': [
        {'doctype': 'person', 'class': ESPerson},
        {'doctype': 'farrecord', 'class': ESFarRecord},
        {'doctype': 'wrarecord', 'class': ESWraRecord},
    ]
}

ELASTICSEARCH_CLASSES_BY_MODEL = {
    'person': ESPerson,
    'farrecord': ESFarRecord,
    'wrarecord': ESWraRecord,
}


class NamesRouter:
    """Write all Names DB data to separate DATABASES['names'] database.
    
    Write Django-specific data to one file and Person/FAR/WRA data to another.
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

    @staticmethod
    def load_rowd(rowd):
        """Given a rowd dict from a CSV, return a Facility object
        """
        def normalize_fieldname(rowd, data, fieldname, choices):
            for field in choices:
                if rowd.get(field):
                    data[fieldname] = rowd.get(field)
        data = {}
        normalize_fieldname(rowd, data, 'facility_id',   ['facility_id', 'id'])
        normalize_fieldname(rowd, data, 'facility_name', ['facility_name', 'name'])
        normalize_fieldname(rowd, data, 'facility_type', ['facility_type', 'type', 'category'])
        if not data.get('facility_type'):
            data['facility_type'] = 'other'
        # update or new
        try:
            facility = Facility.objects.get(
                facility_id=data['facility_id']
            )
        except Facility.DoesNotExist:
            facility = Facility()
        for key,val in data.items():
            setattr(facility, key, val)
        return facility

    def save(self, *args, **kwargs):
        """Save Facility, ignoring usernames and notes"""
        super(Facility, self).save()


class Person(models.Model):
    nr_id                         = models.CharField(max_length=255, primary_key=True,      verbose_name='Names Registry ID',         help_text='Names Registry unique identifier')
    family_name                   = models.CharField(max_length=30,                        verbose_name='Last Name',                 help_text='Preferred family or last name')
    given_name                    = models.CharField(max_length=30,                        verbose_name='First Name',                help_text='Preferred given or first name')
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
    facility = models.ManyToManyField(Facility, through='PersonFacility',  related_name='facilities')
    
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

    def admin_url(self):
         return reverse('admin:names_person_change', args=(self.nr_id,))

    def dump_rowd(self, fieldnames):
        """Return a rowd dict suitable for inclusion in a CSV
        """
        return {
            fieldname: getattr(self, fieldname, '') for fieldname in fieldnames
        }

    @staticmethod
    def load_rowd(rowd):
        """Given a rowd dict from a CSV, return a Person object
        """
        try:
            o = Person.objects.get(nr_id=rowd['nr_id'])
        except Person.DoesNotExist:
            o = Person()
        # special cases
        if rowd.get('other_names'):
            names = rowd.pop('other_names')
            names = names.replace('[','').replace(']','')
            names = names.replace("'",'').replace('"','').split(',')
            if names:
                o.other_names = '\n'.join(names)
        try:
            o.birth_date = parser.parse(rowd.pop('birth_date'))
        except parser._parser.ParserError:
            pass
        try:
            o.death_date = parser.parse(rowd.pop('death_date'))
        except parser._parser.ParserError:
            pass
        if rowd.get('facility'):
            f = PersonFacility
            o.facility = None
        # everything else
        for key,val in rowd.items():
            if val:
                if isinstance(val, str):
                    val = val.replace('00:00:00', '').strip()
                setattr(o, key, val)
        return o

    def save(self, *args, **kwargs):
        """Save Person, adding NOID if absent and Revision with request.user
        """
        # request.user added to obj in names.admin.FarRecordAdmin.save_model
        if getattr(self, 'user', None):
            username = getattr(self, 'user').username
        # ...or comes from names.cli.load
        elif kwargs.get('username'):
            username = kwargs['username']
        else:
            username = 'UNKNOWN'
        # note is added to obj in names.admin.FarRecordAdmin.save_model
        if getattr(self, 'note', None):
            note = getattr(self, 'note')
        # ...or comes from names.cli.load
        elif kwargs.get('note'):
            note = kwargs['note']
        else:
            note = 'DEFAULT NOTE TEXT'
        
        # New NR ID if none exists
        if not self.nr_id:
            self.nr_id = self._get_noid()
        # has the record changed?
        try:
            old = Person.objects.get(nr_id=self.nr_id)
        except Person.DoesNotExist:
            old = None
        changed = Revision.object_has_changed(self, old, Person)
        # now save
        self.timestamp = timezone.now()
        super(Person, self).save()
        if changed:
            r = Revision(
                content_object=self,
                username=username, note=note, diff=make_diff(old, self)
            )
            r.save()

    def _make_nr_id(self, username):
        """[Deprecated] Generate a new unique ID
        """
        import hashlib
        m = hashlib.sha256()
        m.update(bytes('namesdb-editor', 'utf-8'))
        m.update(bytes(username, 'utf-8'))
        m.update(bytes(timezone.now().isoformat(), 'utf-8'))
        return m.hexdigest()[:10]

    def _get_noid(self):
        """Get a fresh NOID from ddr-idservice noidminter API
        """
        try:
            return noidminter.get_noid()
        except ConnectionError:
            raise Exception(
                f'Could not connect to ddr-idservice at {settings.NOIDMINTER_URL}.' \
                ' Please check settings.'
            )

    def revisions(self):
        """List of object Revisions
        """
        return Revision.objects.filter(model='persopn', record_id=self.nr_id)

    @staticmethod
    def related_facilities():
        """Build dict of Person->Facility relations
        """
        query = """
            SELECT names_person.nr_id,
                names_personfacility.facility_id,
                names_personfacility.entry_date, names_personfacility.exit_date
            FROM names_person INNER JOIN names_personfacility
                ON names_person.id = names_personfacility.person_id;
        """
        x = {}
        with connections['names'].cursor() as cursor:
            cursor.execute(query)
            for nr_id, facility_id, entry_date, exit_date in cursor.fetchall():
                if nr_id:
                    if not x.get(nr_id):
                        x[nr_id] = []
                    x[nr_id].append({
                        'facility_id': facility_id,
                        'entry_date': entry_date,
                        'exit_date': exit_date,
                    })
        return x

    @staticmethod
    def related_farrecords():
        """Build dict of Person->FarRecord relations
        """
        query = """
            SELECT names_person.nr_id,
                   names_farrecord.far_record_id,
                   names_farrecord.last_name, names_farrecord.first_name
            FROM names_farrecord INNER JOIN names_person
            ON names_farrecord.person_id = names_person.id;
        """
        x = {}
        with connections['names'].cursor() as cursor:
            cursor.execute(query)
            for nr_id,far_record_id,last_name,first_name in cursor.fetchall():
                if nr_id:
                    if not x.get(nr_id):
                        x[nr_id] = []
                    x[nr_id].append({
                        'far_record_id': far_record_id,
                        'last_name': last_name,
                        'first_name': first_name,
                    })
        return x

    @staticmethod
    def related_wrarecords():
        """Build dict of Person->WraRecord relations
        """
        query = """
            SELECT names_person.nr_id,
                   names_wrarecord.wra_record_id,
                   names_wrarecord.lastname, names_wrarecord.firstname
            FROM names_wrarecord INNER JOIN names_person
            ON names_wrarecord.person_id = names_person.id;
        """
        x = {}
        with connections['names'].cursor() as cursor:
            cursor.execute(query)
            for nr_id,wra_record_id,lastname,firstname in cursor.fetchall():
                if nr_id:
                    if not x.get(nr_id):
                        x[nr_id] = []
                    x[nr_id].append({
                        'wra_record_id': wra_record_id,
                        'lastname': lastname,
                        'firstname': firstname,
                    })
        return x

    def dict(self, related):
        """JSON-serializable dict
        """
        d = {'id': self.nr_id}
        for fieldname in FIELDS_PERSON:
            value = None
            if fieldname == 'facilities':
                if related['facilities'].get(self.nr_id):
                    value = related['facilities'][self.nr_id]
            elif fieldname == 'far_records':
                if related['far_records'].get(self.nr_id):
                    value = related['far_records'][self.nr_id]
            elif fieldname == 'wra_records':
                if related['wra_records'].get(self.nr_id):
                    value = related['wra_records'][self.nr_id]
            else:
                if getattr(self, fieldname):
                    value = getattr(self, fieldname)
            d[fieldname] = value
        return d

    def post(self, related, ds):
        """Post record to Elasticsearch
        """
        data = self.dict(related)
        es_class = ELASTICSEARCH_CLASSES_BY_MODEL['person']
        d = es_class.from_dict(data['id'], data)
        result = d.save(index=ds.index_name('person'), using=ds.es)
        return result


class PersonFacility(models.Model):
    person     = models.ForeignKey(Person, on_delete=models.DO_NOTHING)
    facility   = models.ForeignKey(Facility, on_delete=models.DO_NOTHING)
    entry_date = models.DateField(blank=1, null=1, verbose_name='Facility Entry Date', help_text='Date of entry to detention facility')
    exit_date  = models.DateField(blank=1, null=1, verbose_name='Facility Exit Date',  help_text='Date of exit from detention facility')

    @staticmethod
    def load_rowd(rowd):
        """Given a rowd dict from a CSV, return a PersonFacility object
        """
        def normalize_fieldname(rowd, data, fieldname, choices):
            for field in choices:
                if rowd.get(field):
                    data[fieldname] = rowd.get(field)
        data = {}
        normalize_fieldname(rowd, data, 'person_id',   ['nr_id', 'person_id'])
        normalize_fieldname(rowd, data, 'facility_id', ['facility', 'facility_id'])
        normalize_fieldname(rowd, data, 'entry_date',  ['facility_entry_date', 'entry_date'])
        normalize_fieldname(rowd, data, 'exit_date',   ['facility_exit_date', 'exit_date'])
        # update or new
        try:
            p = Person.objects.get(nr_id=data['person_id'])
            f = Facility.objects.get(facility_id=data['facility_id'])
            pf = PersonFacility.objects.get(
                person=p, facility=f,
            )
        except PersonFacility.DoesNotExist:
            pf = PersonFacility()
        for key,val in data.items():
            if key in ['entry_date', 'exit_date']:
                val = parser.parse(val)
            setattr(pf, key, val)
        return pf

    def save(self, *args, **kwargs):
        """Save PersonFacility"""
        super(PersonFacility, self).save()


class FarRecord(models.Model):
    far_record_id           = models.CharField(max_length=255, primary_key=1, verbose_name='FAR Record ID', help_text="Derived from FAR ledger id + line id ('original_order')")
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
    alien_registration_no   = models.CharField(max_length=255, blank=1, verbose_name='Alien Registration Number', help_text='INS-assigned Alien Registration number')
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

    def dump_rowd(self, fieldnames):
        """Return a rowd dict suitable for inclusion in a CSV
        """
        return {
            fieldname: getattr(self, fieldname, '') for fieldname in fieldnames
        }

    @staticmethod
    def load_rowd(rowd):
        """Given a rowd dict from a CSV, return a FarRecord object
        """
        try:
            o = FarRecord.objects.get(
                far_record_id=rowd['far_record_id']
            )
        except FarRecord.DoesNotExist:
            o = FarRecord()
        for key,val in rowd.items():
            if val:
                if isinstance(val, str):
                    val = val.replace('00:00:00', '').strip()
                setattr(o, key, val)
        return o

    def save(self, *args, **kwargs):
        """Save FarRecord, adding Revision with request.user
        """
        # request.user added to obj in names.admin.FarRecordAdmin.save_model
        if getattr(self, 'user', None):
            username = getattr(self, 'user').username
        # ...or comes from names.cli.load
        elif kwargs.get('username'):
            username = kwargs['username']
        else:
            username = 'UNKNOWN'
        # note is added to obj in names.admin.FarRecordAdmin.save_model
        if getattr(self, 'note', None):
            note = getattr(self, 'note')
        # ...or comes from names.cli.load
        elif kwargs.get('note'):
            note = kwargs['note']
        else:
            note = 'DEFAULT NOTE TEXT'
        
        # has the record changed?
        try:
            old = FarRecord.objects.get(far_record_id=self.far_record_id)
        except FarRecord.DoesNotExist:
            old = None
        changed = Revision.object_has_changed(self, old, FarRecord)
        # now save
        self.timestamp = timezone.now()
        super(FarRecord, self).save()
        if changed:
            r = Revision(
                content_object=self,
                username=username, note=note, diff=make_diff(old, self)
            )
            r.save()

    def revisions(self):
        """List of object Revisions
        """
        return Revision.objects.filter(model='far', record_id=self.far_record_id)

    @staticmethod
    def related_persons():
        query = """
            SELECT names_farrecord.far_record_id, names_person.nr_id,
                   names_person.preferred_name
            FROM names_farrecord
            INNER JOIN names_person ON names_farrecord.person_id = names_person.id
        """
        with connections['names'].cursor() as cursor:
            cursor.execute(query)
            return {
                far_record_id: {
                    'nr_id': nr_id, 'preferred_name': preferred_name
                }
                for far_record_id,nr_id,preferred_name in cursor.fetchall()
                if nr_id
            }

    def dict(self, related):
        """JSON-serializable dict
        @param related: dict of person_id: {'id':..., 'name':...}
        """
        d = {'id': self.far_record_id}
        for fieldname in FIELDS_FARRECORD:
            if fieldname == 'person':
                value = None
                if related['persons'].get(self.far_record_id):
                    person = related['persons'][self.far_record_id]
                    value = {
                        'id': person['nr_id'],
                        'name': person['preferred_name'],
                    }
            else:
                value = str(getattr(self, fieldname, ''))
            d[fieldname] = value
        return d

    def post(self, related, ds):
        """Post record to Elasticsearch
        """
        data = self.dict(related)
        es_class = ELASTICSEARCH_CLASSES_BY_MODEL['farrecord']
        return es_class.from_dict(data['id'], data).save(
            index=ds.index_name('farrecord'), using=ds.es
        )


class FarRecordPerson():
    """Fake class used for importing FarRecord->Person links"""

    @staticmethod
    def load_rowd(rowd):
        """Given a rowd dict from a CSV, return a FarRecord object
        """
        def normalize_fieldname(rowd, data, fieldname, choices):
            for field in choices:
                if rowd.get(field):
                    data[fieldname] = rowd.get(field)
        data = {}
        normalize_fieldname(rowd, data, 'far_record_id',['far_record_id', 'fk_far_id', 'id'])
        normalize_fieldname(rowd, data, 'person_id',   ['nr_id', 'person_id'])
        # update or new
        f = FarRecord.objects.get(far_record_id=data['far_record_id'])
        p = Person.objects.get(nr_id=data['person_id'])
        f.person = p
        return f

    def save(self, *args, **kwargs):
        """Save FarRecord"""
        super(FarRecord, self).save()


class WraRecord(models.Model):
    wra_record_id     = models.CharField(max_length=255, primary_key=1, verbose_name='WRA Record ID', help_text="Derived from WRA ledger id + line id ('original_order')")
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
    maritalstatus     = models.CharField(max_length=255, blank=1, verbose_name='Marital status', help_text='Marital status')
    ethnicity         = models.CharField(max_length=255, blank=1, verbose_name='Ethnicity', help_text='Ethnicity')
    birthplace        = models.CharField(max_length=255, blank=1, verbose_name='Birthplace', help_text='Birthplace')
    citizenshipstatus = models.CharField(max_length=255, blank=1, verbose_name='Citizenship status', help_text='Citizenship status')
    highestgrade      = models.CharField(max_length=255, blank=1, verbose_name='Highest degree achieved', help_text='Highest degree achieved')
    language          = models.CharField(max_length=255, blank=1, verbose_name='Languages spoken', help_text='Languages spoken')
    religion          = models.CharField(max_length=255, blank=1, verbose_name='Religion', help_text='Religion')
    occupqual1        = models.CharField(max_length=255, blank=1, verbose_name='Primary qualified occupation', help_text='Primary qualified occupation')
    occupqual2        = models.CharField(max_length=255, blank=1, verbose_name='Secondary qualified occupation', help_text='Secondary qualified occupation')
    occupqual3        = models.CharField(max_length=255, blank=1, verbose_name='Tertiary qualified occupation', help_text='Tertiary qualified occupation')
    occuppotn1        = models.CharField(max_length=255, blank=1, verbose_name='Primary potential occupation', help_text='Primary potential occupation')
    occuppotn2        = models.CharField(max_length=255, blank=1, verbose_name='Secondary potential occupation', help_text='Secondary potential occupation')
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

    def dump_rowd(self, fieldnames):
        """Return a rowd dict suitable for inclusion in a CSV
        """
        return {
            fieldname: getattr(self, fieldname, '') for fieldname in fieldnames
        }

    @staticmethod
    def load_rowd(rowd):
        """Given a rowd dict from a CSV, return a WraRecord object
        """
        try:
            o = WraRecord.objects.get(
                wra_record_id=rowd['wra_record_id']
            )
        except WraRecord.DoesNotExist:
            o = WraRecord()
        for key,val in rowd.items():
            if val:
                if isinstance(val, str):
                    val = val.replace('00:00:00', '').strip()
                setattr(o, key, val)
        return o

    def save(self, *args, **kwargs):
        """Save WraRecord, adding Revision with request.user
        """
        # request.user added to obj in names.admin.FarRecordAdmin.save_model
        if getattr(self, 'user', None):
            username = getattr(self, 'user').username
        # ...or comes from names.cli.load
        elif kwargs.get('username'):
            username = kwargs['username']
        else:
            username = 'UNKNOWN'
        # note is added to obj in names.admin.FarRecordAdmin.save_model
        if getattr(self, 'note', None):
            note = getattr(self, 'note')
        # ...or comes from names.cli.load
        elif kwargs.get('note'):
            note = kwargs['note']
        else:
            note = 'DEFAULT NOTE TEXT'
        
        # has the record changed?
        try:
            old = WraRecord.objects.get(wra_record_id=self.wra_record_id)
        except WraRecord.DoesNotExist:
            old = None
        changed = Revision.object_has_changed(self, old, WraRecord)
        # now save
        self.timestamp = timezone.now()
        super(WraRecord, self).save()
        if changed:
            r = Revision(
                content_object=self,
                username=username, note=note, diff=make_diff(old, self)
            )
            r.save()

    def revisions(self):
        """List of object Revisions
        """
        return Revision.objects.filter(
            model='wra', record_id=self.wra_record_id
        )

    @staticmethod
    def related_persons():
        query = """
            SELECT names_wrarecord.wra_record_id, names_person.nr_id,
                   names_person.preferred_name
            FROM names_wrarecord
            INNER JOIN names_person ON names_wrarecord.person_id = names_person.id
        """
        with connections['names'].cursor() as cursor:
            cursor.execute(query)
            return {
                wra_record_id: {
                    'nr_id': nr_id, 'preferred_name': preferred_name
                }
                for wra_record_id,nr_id,preferred_name in cursor.fetchall()
                if nr_id
            }

    def dict(self, related):
        """JSON-serializable dict
        """
        d = {'id': self.wra_record_id}
        for fieldname in FIELDS_WRARECORD:
            if fieldname == 'person':
                value = None
                if related['persons'].get(self.wra_record_id):
                    person = related['persons'][self.wra_record_id]
                    value = {
                        'id': person['nr_id'],
                        'name': person['preferred_name'],
                    }
            else:
                value = str(getattr(self, fieldname, ''))
            d[fieldname] = value
        return d

    def post(self, related, ds):
        """Post record to Elasticsearch
        """
        data = self.dict(related)
        es_class = ELASTICSEARCH_CLASSES_BY_MODEL['wrarecord']
        return es_class.from_dict(data['id'], data).save(
            index=ds.index_name('wrarecord'), using=ds.es
        )


class WraRecordPerson():
    """Fake class used for importing WraRecord->Person links"""

    @staticmethod
    def load_rowd(rowd):
        """Given a rowd dict from a CSV, return a WraRecord object
        """
        def normalize_fieldname(rowd, data, fieldname, choices):
            for field in choices:
                if rowd.get(field):
                    data[fieldname] = rowd.get(field)
        data = {}
        normalize_fieldname(rowd, data, 'wra_record_id',['wra_record_id', 'fk_wra_id', 'id'])
        normalize_fieldname(rowd, data, 'person_id',   ['nr_id', 'person_id'])
        # update or new
        w = WraRecord.objects.get(wra_record_id=data['wra_record_id'])
        p = Person.objects.get(nr_id=data['person_id'])
        w.person = p
        return w

    def save(self, *args, **kwargs):
        """Save WraRecord"""
        super(WraRecord, self).save()


class Revision(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=30)
    content_object = GenericForeignKey("content_type", "object_id")
    timestamp = models.DateTimeField(auto_now_add=True)
    username = models.CharField(max_length=30)
    note = models.CharField(max_length=255, blank=1)
    diff = models.TextField()

    def __repr__(self):
        return f'<Revision {self.content_object} {self.timestamp} {self.username}>'

    @staticmethod
    def object_has_changed(new_object, old_object, object_class):
        """Have values of any object fields changed?
        """
        if old_object:
            changed = 0
            fields_considered = []
            fields_diff = []
            fields_same = []
            for field in object_class._meta.get_fields():
                # ignore ManyToOneRel things, focus on django.db.models.fields.*
                if not hasattr(field, 'column'):
                    fields_considered.append(f'column - {field}')
                    continue
                # ignore timestamp changes
                if field.name == 'timestamp':
                    fields_considered.append(f'tmstmp - {field}')
                    continue
                # has value of this field (or lack thereof) changed?
                old_value = getattr(new_object, field.name)
                new_value = getattr(old_object, field.name)
                if not (old_value == new_value):
                    changed += 1
                    fields_diff.append((field.name, old_value, new_value))
                else:
                    fields_same.append((field.name, old_value, new_value))
            return changed
        else:
            return 1


def _jsonfriendly_value(value):
    if not isinstance(value, str):
        value = str(value)
    return value

def jsonlines(obj, excluded_fields=[]):
    """JSONlines representation of object fields, for making diffs
    see https://jsonlines.org/
    """
    if obj:
        return [
            json.dumps({
                fieldname: _jsonfriendly_value(getattr(obj, fieldname))
            })
            for fieldname in [field.name for field in obj._meta.fields]
            if not fieldname in excluded_fields
        ]
    return ''

def make_diff(old, new):
    EXCLUDED_FIELDS = ['timestamp']
    if not old:
        # no diff for revision 0
        # get object id
        oid = None
        fieldnames = ['far_record_id', 'wra_record_id', 'nr_id',]
        for fieldname in fieldnames:
            if getattr(new, fieldname, None):
                oid = getattr(new, fieldname)
        return f'{oid}: object created'
    return '\n'.join([
        line
        for line in difflib.unified_diff(
                jsonlines(old, EXCLUDED_FIELDS),
                jsonlines(new, EXCLUDED_FIELDS),
                fromfile=f'{old.timestamp}',
                tofile=f'{new.timestamp}',
                n=1
        )
    ]).replace('\n\n', '\n')


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

def model_fields(class_, exclude_fields=[]):
    """Return name, type, and verbose description for each field in the model.
    """
    fields = class_._meta.get_fields()
    data = [
        [x.name, x.get_internal_type(), x.verbose_name]
        for x in fields
        if (
            not (x.many_to_one or x.many_to_many
                 or x.one_to_one or x.one_to_many
                 or x.related_model)
        ) and (
            not x.name in exclude_fields
        )
    ]
    for x in fields:
        if x.one_to_one:
            data.append( [x.name, x.get_internal_type()] )
    for x in fields:
        if x.one_to_many:
            data.append( [x.name, x.get_internal_type()] )
    for x in fields:
        if x.many_to_one:
            data.append( [x.name, x.get_internal_type(), x.verbose_name] )
    for x in fields:
        if x.many_to_many:
            data.append( [x.name, x.get_internal_type()] )
    return data

def format_model_fields(fields):
    """Return output of model_fields() as a table formatted string
    """
    return tabulate(fields)

MODEL_CLASSES = {
    'facility': Facility,
    'person': Person,
    'personfacility': PersonFacility,
    'farrecord': FarRecord,
    'wrarecord': WraRecord,
    'farrecordperson': FarRecordPerson,
    'wrarecordperson': WraRecordPerson,
}

def write_csv(csv_path, model_class, cols, limit=None, debug=False):
    """Writes rowds of specified model class to CSV file
    """
    with open(csv_path, 'w', newline='') as f:
        writer = fileio.csv_writer(f)
        if debug: print(f'header {cols}')
        writer.writerow(cols)
        n = 0
        if limit:
            for o in model_class.objects.all()[:limit]:
                row = list(o.dump_rowd(cols).values())
                if debug: print(f'{n}/{limit} row {row}')
                writer.writerow(row)
                n += 1
        else:
            num = model_class.objects.count()
            for o in model_class.objects.all():
                row = list(o.dump_rowd(cols).values())
                if debug: print(f'{n}/{num} {row[0]}')
                writer.writerow(row)
                n += 1
