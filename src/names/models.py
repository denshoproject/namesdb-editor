from datetime import datetime, date
import difflib
import json

from dateutil import parser
from httpx import RequestError
from tabulate import tabulate

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import connections, models
from django.urls import reverse
from django.utils import timezone

from names import csvfile,fileio,noidminter
from namesdb_public.models import Person as ESPerson, FIELDS_PERSON
from namesdb_public.models import Facility as ESFacility
from namesdb_public.models import PersonFacility as ESPersonFacility
from namesdb_public.models import PersonLocation as ESPersonLocation
from namesdb_public.models import FIELDS_PERSONFACILITY
from namesdb_public.models import FarRecord as ESFarRecord, FIELDS_FARRECORD
from namesdb_public.models import WraRecord as ESWraRecord, FIELDS_WRARECORD
from namesdb_public.models import FarPage as ESFarPage, FIELDS_FARPAGE
from namesdb_public.models import FIELDS_BY_MODEL
from ireizo_public.models import IreiRecord as ESIreiRecord, FIELDS_IREIRECORD


INDEX_PREFIX = 'names'

ELASTICSEARCH_CLASSES = {
    'all': [
        {'doctype': 'person', 'class': ESPerson},
        {'doctype': 'farrecord', 'class': ESFarRecord},
        {'doctype': 'wrarecord', 'class': ESWraRecord},
        {'doctype': 'ireirecord', 'class': ESIreiRecord},
        {'doctype': 'farpage', 'class': ESFarPage},
        {'doctype': 'facility', 'class': ESFacility},
        {'doctype': 'personlocation', 'class': ESPersonLocation},
    ]
}

ELASTICSEARCH_CLASSES_BY_MODEL = {
    'person': ESPerson,
    'farrecord': ESFarRecord,
    'wrarecord': ESWraRecord,
    'ireirecord': ESIreiRecord,
    'farpage': ESFarPage,
    'facility': ESFacility,
    'personlocation': ESPersonLocation,
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


FIELDS_FACILITY = [
    'facility_id',
    'facility_type',
    'title',
    'location_label',
    'location_lat',
    'location_lng',
    'tgn_id',
    'encyc_title',
    'encyc_url',
]

class Facility(models.Model):
    facility_id   = models.CharField(max_length=30, primary_key=True, verbose_name='Facility ID',   help_text='ID of facility where detained')
    facility_type = models.CharField(max_length=255,  blank=0, verbose_name='Facility Type', help_text='Type of facility where detained')
    title         = models.CharField(max_length=255,  blank=0, verbose_name='Facility Name', help_text='Name of facility where detained')
    location_label = models.CharField(max_length=255, blank=1, verbose_name='Location Label', help_text='')
    location_lat   = models.FloatField(               blank=1, verbose_name='Latitude',       help_text='')
    location_lng   = models.FloatField(               blank=1, verbose_name='Longitude',      help_text='')
    tgn_id         = models.CharField(max_length=32,  blank=1, verbose_name='TGN ID', help_text='Thesaurus of Geographic Names (TGN)')
    # ALTER TABLE names_facility ADD COLUMN tgn_id varchar(32) NULL;
    encyc_title    = models.CharField(max_length=255, blank=1, verbose_name='Encyclopedia title', help_text='')
    encyc_url      = models.URLField(max_length=255,  blank=1, verbose_name='Encyclopedia URL',   help_text='')

    class Meta:
        verbose_name = 'Facility'
        verbose_name_plural = 'Facilities'

    def __eq__(self, other):
        """Enable Pythonic sorting"""
        if other and isinstance(other, Facility):
            self_id = self.facility_id.split('-'); self_id[0] = int(self_id[0])
            other_id = other.facility_id.split('-'); other_id[0] = int(other_id[0])
            return self_id == other_id
        return False

    def __lt__(self, other):
        """Enable Pythonic sorting"""
        if other and isinstance(other, Facility):
            self_id = self.facility_id.split('-'); self_id[0] = int(self_id[0])
            other_id = other.facility_id.split('-'); other_id[0] = int(other_id[0])
            return self_id < other_id
        return False

    @staticmethod
    def prep_data():
        """Prepare data for loading CSV full of Facilities
        """
        return {}

    @staticmethod
    def load_rowd(rowd, prepped_data):
        """Given a rowd dict from a CSV, return a Facility object
        """
        def normalize_fieldname(rowd, data, fieldname, choices):
            for field in choices:
                if rowd.get(field):
                    data[fieldname] = rowd.get(field)
        data = {}
        normalize_fieldname(rowd, data, 'facility_id',   ['facility_id', 'id'])
        normalize_fieldname(rowd, data, 'facility_type', ['facility_type', 'type', 'category'])
        normalize_fieldname(rowd, data, 'title', ['facility_name', 'name', 'title'])
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
        return facility,prepped_data

    @staticmethod
    def load_from_vocab(rowd):
        """Load data files from densho-vocab/api/0.2/facility.json
        """
        data = {
            'facility_id':   rowd['sos_facility_id'],
            'facility_type': rowd['type'],
            'title':         rowd['title'],
            'location_label': rowd['location']['label'],
            'location_lat':   rowd['location']['geopoint']['lat'],
            'location_lng':   rowd['location']['geopoint']['lng'],
            'tgn_id':         rowd['location']['tgn_id'],
            #'encyc_title': rowd['elinks']['label'],
            #'encyc_url':   rowd['elinks']['url'],
        }
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

    def dict(self, related):
        """JSON-serializable dict
        """
        d = {'id': self.facility_id}
        for fieldname in FIELDS_FACILITY:
            value = None
            if hasattr(self, fieldname):
                value = getattr(self, fieldname)
            d[fieldname] = value
        return d

    def post(self, related, ds):
        """Post Facility record to Elasticsearch
        """
        data = self.dict(related)
        es_class = ELASTICSEARCH_CLASSES_BY_MODEL['facility']
        return es_class.from_dict(data['facility_id'], data).save(
            index=ds.index_name('facility'), using=ds.es
        )


FIELDS_LOCATION = [
    'title',
    'lat',
    'lng',
    'facility',
    'address',
    'address_components',
    'notes',
]

class Location(models.Model):
    """
    CREATE TABLE IF NOT EXISTS "names_location" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "lat" float NULL,
        "lng" float NULL,
        "facility_id" varchar(30) REFERENCES "names_facility" ("facility_id") DEFERRABLE INITIALLY DEFERRED,
        "address" varchar(255),
        "address_components" text,
        "notes" text
    );
    CREATE INDEX "names_location_id" ON "names_location" ("id");
    CREATE INDEX "names_location_facility_id" ON "names_location" ("facility_id");
    """
    lat         = models.FloatField(blank=1,                verbose_name='Latitude',  help_text='Geocoded latitude')
    lng         = models.FloatField(blank=1,                verbose_name='Longitude', help_text='Geocoded longitude')
    facility    = models.ForeignKey(Facility, null=1, blank=1, on_delete=models.DO_NOTHING, verbose_name='Facility', help_text='Facility from Densho CV (if applicable)')
    address     = models.CharField(max_length=255, blank=1, verbose_name='Address',   help_text='')
    address_components = models.TextField(blank=1,          verbose_name='Address components',  help_text='Using component names from geocodejson-spec.')
    notes       = models.TextField(blank=1,                 verbose_name='Notes',     help_text='')

    def __repr__(self):
        return f'<{self.__class__.__name__}(id={self.id}, title={self.address})>'

    def __str__(self):
        return f'<{self.address} ({self.lat}, {self.lng})>'

    def __eq__(self, other):
        """Enable Pythonic sorting"""
        if other and isinstance(other, Location):
            return self.id == other.id
        return False

    def __lt__(self, other):
        """Enable Pythonic sorting"""
        if other and isinstance(other, Location):
            return self.id < other.id
        return False

    @staticmethod
    def prep_data():
        """Prepare data for loading CSV full of Locations
        """
        return {
            'facilities': {
                f.facility_id:
                f for f in Facility.objects.all()
            },
        }

    @staticmethod
    def load_rowd(rowd, prepped_data):
        """Given a rowd dict from a CSV, return a Location object
        """
        print(f"{rowd=}")
        def normalize_fieldname(rowd, data, fieldname, choices):
            for field in choices:
                if rowd.get(field):
                    data[fieldname] = rowd.get(field)
        data = {}
        normalize_fieldname(rowd, data, 'location_id', ['id', 'location', 'location_id'])
        normalize_fieldname(rowd, data, 'facility_id', ['facility', 'facility_id'])
        # update or new
        if data.get('location_id'):
            try:
                location = Location.objects.get(
                    location_id=data['location_id']
                )
            except Location.DoesNotExist:
                location = Location()
        else:
            location = Location()
        try:
            f = prepped_data['facilities'][data.pop('facility_id')]
            location.facility = f
        except KeyError:  # some rows are missing facility_id
            return None,prepped_data
        for key,val in rowd.items():
            if val and not getattr(location, key):
                setattr(location, key, val)
        if location.lat:
            location.lat = float(location.lat)
        if location.lng:
            location.lng = float(location.lng)
        return location,prepped_data

    def save(self, *args, **kwargs):
        """Save Location, ignoring usernames and notes"""
        super(Location, self).save()

    def dict(self, n=None):
        """JSON-serializable dict
        """
        d = {}
        if n:
            d['n'] = n
        for fieldname in FIELDS_LOCATION:
            if getattr(self, fieldname):
                value = getattr(self, fieldname)
                d[fieldname] = value
        return d


class Person(models.Model):
    nr_id                         = models.CharField(max_length=255, primary_key=True,      verbose_name='Names Registry ID',         help_text='Names Registry unique identifier')
    family_name                   = models.CharField(max_length=255,                        verbose_name='Last Name',                 help_text='Preferred family or last name')
    given_name                    = models.CharField(max_length=255,                        verbose_name='First Name',                help_text='Preferred given or first name')
    given_name_alt                = models.TextField(blank=True, null=True, verbose_name='Alternative First Names',   help_text='List of alternative first names')
    other_names                   = models.TextField(blank=True, null=True, verbose_name='Other Names',               help_text='List of other names')
    middle_name                   = models.CharField(max_length=255, blank=True, null=True, verbose_name='Middle Name',               help_text='Middle name or initial')
    prefix_name                   = models.CharField(max_length=255, blank=True, null=True, verbose_name='Name Prefix',               help_text='Professional/titular prefix. E.g., "Dr.", "Rev."')
    suffix_name                   = models.CharField(max_length=255, blank=True, null=True, verbose_name='Name Suffix',               help_text='Name suffix. E.g., "Jr.", "Esq."')
    jp_name                       = models.CharField(max_length=255, blank=True, null=True, verbose_name='Japanese Name',             help_text='Name in kana')
    preferred_name                = models.CharField(max_length=255,          verbose_name='Preferred Full Name',       help_text='Preferred form of full name for display')
    birth_date                    = models.DateField(max_length=30, blank=True, null=True, verbose_name='Date of Birth',             help_text='Full birthdate')
    birth_date_text               = models.CharField(max_length=255, blank=True, null=True, verbose_name='Birthdate Text',            help_text='Text representation of birthdate, if necessary')
    birth_place                   = models.CharField(max_length=255, blank=True, null=True, verbose_name='Birthplace',                help_text='Place of birth')
    death_date                    = models.DateField(max_length=30, blank=True, null=True, verbose_name='Date of Death',             help_text='Date of death')
    death_date_text               = models.CharField(max_length=255, blank=True, null=True, verbose_name='Death Date Text',           help_text='Text representation of death date, if necessary')
    wra_family_no                 = models.CharField(max_length=255, blank=True, null=True, verbose_name='Family Number',             help_text='WRA-assigned family number')
    wra_individual_no             = models.CharField(max_length=255, blank=True, null=True, verbose_name='Individual Number',         help_text='WRA-assigned individual number')
    citizenship                   = models.CharField(max_length=255,          verbose_name='Citizenship Status',    help_text='Status of US citizenship as of 1946')
    alien_registration_no         = models.CharField(max_length=255, blank=True, null=True, verbose_name='Alien Registration Number', help_text='INS-assigned alien registration number')
    gender                        = models.CharField(max_length=255,          verbose_name='Gender',                    help_text='Gender')
    preexclusion_residence_city   = models.CharField(max_length=255, blank=True, null=True, verbose_name='Pre-exclusion City',        help_text='Reported city of residence at time of registration')
    preexclusion_residence_state  = models.CharField(max_length=255, blank=True, null=True, verbose_name='Pre-exclusion State',       help_text='Reported state of residence at time of registration')
    postexclusion_residence_city  = models.CharField(max_length=255, blank=True, null=True, verbose_name='Post-detention City',       help_text='Reported city of residence immediately following detention')
    postexclusion_residence_state = models.CharField(max_length=255, blank=True, null=True, verbose_name='Post-detention State',      help_text='Reported state of residence immediately following detention')
    exclusion_order_title         = models.CharField(max_length=255, blank=True, null=True, verbose_name='Exclusion Order',           help_text='Name of U.S. Army exclusion order')
    exclusion_order_id            = models.CharField(max_length=255, blank=True, null=True, verbose_name='Exclusion Order ID',        help_text='Order ID ')
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
    def prep_data():
        """Prepare data for loading CSV full of Persons
        """
        return {}

    @staticmethod
    def load_rowd(rowd, prepped_data):
        """Given a rowd dict from a CSV, return a Person object
        """
        if rowd.get('nr_id'):
            try:
                # update existing Person
                o = Person.objects.get(nr_id=rowd['nr_id'])
            except Person.DoesNotExist:
                # new Person
                o = Person(nr_id=rowd['nr_id'])
        else:
            # new Person and get noid
            o = Person()
            o.nr_id = o._get_noid()
        # special cases
        if rowd.get('other_names'):
            names = rowd.pop('other_names')
            names = names.replace('[','').replace(']','')
            names = names.replace("'",'').replace('"','').split(',')
            if names:
                o.other_names = '\n'.join(names)
        if rowd.get('birth_date'):
            try:
                o.birth_date = parser.parse(rowd.pop('birth_date')).date()
            except parser._parser.ParserError:
                pass
        elif rowd.get('birth_date_text'):
            try:
                o.birth_date = parser.parse(rowd.pop('birth_date_text')).date()
            except parser._parser.ParserError:
                pass
        if rowd.get('death_date'):
            try:
                o.death_date = parser.parse(rowd.pop('death_date')).date()
            except parser._parser.ParserError:
                pass
        elif rowd.get('death_date_text'):
            try:
                o.death_date = parser.parse(rowd.pop('death_date_text')).date()
            except parser._parser.ParserError:
                pass
        if rowd.get('facility'):
            f = PersonFacility
            o.facility = None
        # everything else
        for key,val in rowd.items():
            val = val.strip()
            if isinstance(val, str):
                val = val.replace('00:00:00', '').strip()
            setattr(o, key, val)
        # Django doesn't like date values of ''
        if o.birth_date == '':
            o.birth_date = None
        if o.death_date == '':
            o.death_date = None
        return o,prepped_data

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

    def revisions(self):
        """List of object Revisions"""
        return Revision.revisions(self, 'nr_id')

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
            return noidminter.get_noids()[0]
        except RequestError as err:
            raise Exception(
                f'Could not connect to ddr-idservice at {err.request.url}.' \
                ' Please check settings.'
            )

    @staticmethod
    def related_facilities():
        """Build dict of Person->Facility relations
        """
        facility_titles = {f.facility_id: f.title for f in Facility.objects.all()}
        query = """
            SELECT names_person.nr_id,
                names_personfacility.facility_id,
                names_personfacility.entry_date, names_personfacility.exit_date
            FROM names_person INNER JOIN names_personfacility
                ON names_person.nr_id = names_personfacility.person_id;
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
                        'facility_title': facility_titles.get(facility_id, 'UNSPECIFIED'),
                        'entry_date': entry_date,
                        'exit_date': exit_date,
                    })
        return x

    @staticmethod
    def related_farrecords():
        """Build dict of Person->FarRecord relations
        """
        facility_titles = {f.facility_id: f.title for f in Facility.objects.all()}
        query = """
            SELECT names_person.nr_id,
                   names_farrecord.far_record_id,
                   names_farrecord.facility,
                   names_farrecord.last_name, names_farrecord.first_name
            FROM names_farrecord INNER JOIN names_person
            ON names_farrecord.person_id = names_person.nr_id;
        """
        x = {}
        with connections['names'].cursor() as cursor:
            cursor.execute(query)
            for nr_id,far_record_id,facility_id,last_name,first_name in cursor.fetchall():
                if nr_id:
                    if not x.get(nr_id):
                        x[nr_id] = []
                    facility_title = facility_titles.get(facility_id, 'UNSPECIFIED')
                    x[nr_id].append({
                        'far_record_id': far_record_id,
                        'facility_id': facility_id,
                        'facility_title': facility_title,
                        'last_name': last_name,
                        'first_name': first_name,
                    })
        return x

    @staticmethod
    def related_wrarecords():
        """Build dict of Person->WraRecord relations
        """
        facility_titles = {f.facility_id: f.title for f in Facility.objects.all()}
        query = """
            SELECT names_person.nr_id,
                   names_wrarecord.wra_record_id,
                   names_wrarecord.facility,
                   names_wrarecord.lastname, names_wrarecord.firstname
            FROM names_wrarecord INNER JOIN names_person
            ON names_wrarecord.person_id = names_person.nr_id;
        """
        x = {}
        with connections['names'].cursor() as cursor:
            cursor.execute(query)
            for nr_id,wra_record_id,facility_id,lastname,firstname in cursor.fetchall():
                if nr_id:
                    if not x.get(nr_id):
                        x[nr_id] = []
                    facility_title = facility_titles.get(facility_id, 'UNSPECIFIED')
                    x[nr_id].append({
                        'wra_record_id': wra_record_id,
                        'facility_id': facility_id,
                        'facility_title': facility_title,
                        'lastname': lastname,
                        'firstname': firstname,
                    })
        return x

    @staticmethod
    def related_family():
        """Build dict of Person wra_family_no->nr_id relations
        """
        query = """
            SELECT names_person.wra_family_no,
                   names_person.nr_id,
                   names_person.preferred_name,
                   names_person.birth_date,
                   names_person.wra_individual_no,
                   names_person.gender
            FROM names_person;
        """
        x = {}
        with connections['names'].cursor() as cursor:
            cursor.execute(query)
            for row in cursor.fetchall():
                wra_family_no,nr_id,preferred_name,birth_date,wra_individual_no,gender = row
                if not x.get(wra_family_no):
                    x[wra_family_no] = []
                # redact exact birth date
                try:
                    birth_year = birth_date.year
                except:
                    birth_year = None
                data = {
                    'nr_id': nr_id,
                    'preferred_name': preferred_name,
                    'birth_year': birth_year,
                    'wra_individual_no': wra_individual_no,
                    'gender': gender,
                }
                x[wra_family_no].append(data)
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
                if hasattr(self, fieldname):
                    value = getattr(self, fieldname)
            d[fieldname] = value
        d['family'] = []
        if self.wra_family_no and related['family'].get(self.wra_family_no):
            d['family'] = [
                person for person in related['family'][self.wra_family_no]
            ]
        return d

    def post(self, related, ds):
        """Post Person record to Elasticsearch
        """
        data = self.dict(related)
        es_class = ELASTICSEARCH_CLASSES_BY_MODEL['person']
        return es_class.from_dict(data['nr_id'], data).save(
            index=ds.index_name('person'), using=ds.es
        )


class PersonFacility(models.Model):
    person     = models.ForeignKey(Person, on_delete=models.DO_NOTHING)
    facility   = models.ForeignKey(Facility, on_delete=models.DO_NOTHING)
    entry_date = models.DateField(blank=1, null=1, verbose_name='Facility Entry Date', help_text='Date of entry to detention facility')
    exit_date  = models.DateField(blank=1, null=1, verbose_name='Facility Exit Date',  help_text='Date of exit from detention facility')

    def __repr__(self):
        return f'<{self.__class__.__name__}(person={self.person}, facility={self.facility})>'

    def __str__(self):
        return '({} {})'.format(
            self.person, self.facility
        )

    @staticmethod
    def combo_id(person_id, facility_id):
        return f'{person_id}:{facility_id}'

    @staticmethod
    def prep_data():
        """Prepare data for loading CSV full of PersonFacility data
        """
        return {
            'facilities': {
                f.facility_id:
                f for f in Facility.objects.all()
            },
            'personfacilities': {
                pf.combo_id(pf.person_id, pf.facility_id): pf
                for pf in PersonFacility.objects.all()
            },
        }

    @staticmethod
    def load_rowd(rowd, prepped_data):
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
            f = prepped_data['facilities'][data['facility_id']]
        except KeyError:  # some rows are missing facility_id
            return None,prepped_data
        p = Person.objects.get(nr_id=data['person_id'])
        try:
            pfid = PersonFacility.combo_id(p.nr_id, f.facility_id)
            pf = prepped_data['personfacilities'][pfid]
        except KeyError:
            pf = PersonFacility(person=p, facility=f)
            pfid = PersonFacility.combo_id(p.nr_id, f.facility_id)
        for key,val in data.items():
            if key in ['entry_date', 'exit_date']:
                try:
                    val = parser.parse(val)
                    setattr(pf, key, val)
                except parser._parser.ParserError:
                    pass
        prepped_data[pfid] = pf
        return pf,prepped_data

    def save(self, *args, **kwargs):
        """Save PersonFacility"""
        super(PersonFacility, self).save()

    def dict(self, n=None):
        """JSON-serializable dict
        """
        d = {}
        if n:
            d['n'] = n
        for fieldname in FIELDS_PERSONFACILITY:
            if getattr(self, fieldname):
                value = getattr(self, fieldname)
                d[fieldname] = value
        return d


FIELDS_PERSONLOCATION = [
    'person',
    'location',
    'facility',
    'facility_address',
    'entry_date',
    'exit_date',
    'sort_start',
    'sort_end',
    'notes',
]

class PersonLocation(models.Model):
    """
TODO (namesdb) like PersonLocation, more general than PersonFacility
include things like precamp city and postcamp city
diff levels of accuracy, from street addr to just country ("Japan")
don't use separate Locations table, just store e.g. startdate, edndate, coutnry, region, state, city, addr, lat, lng

# TODO load PersonLocation
# - CACHE country,state,city,address for facility
# - FOR Person MAKE PersonLocations
#   - birthdate and birthplace  (sort 00)
#   - preexclusion city,state   (sort 20)
#   - FOR PersonFacility,       (sort 40)
#     - entry_date, exit_date, facilty id
#       PLUS country,state,city,address for facility
#   - postdetention city,state  (sort 60)

https://docs.google.com/spreadsheets/d/1Kh1uuCtufA2bJTSF_gyAR83Ai4YmeKiiZcwQM3EhNio/edit?pli=1#gid=843779669
NAME             LABEL	          TYPE	REQUIRED  REPEATABLE  DESCRIPTION
location_text	 Location	  str	TRUE		      Display text of location name
lat	         Latitude	  float	FALSE		      Geocoded latitude
lng     	 Longitude	  float	FALSE		      Geocoded longitude
entry_date	 From	          date	FALSE		      Date of arrival
exit_date	 To	          date	FALSE		      Date of departure
sort_date_start	 Sort Order Start date	FALSE		      Date of arrival for sort purposes only. Not for display.
sort_date_end	 Sort Order End	  date	FALSE		      Date of departure for sort purposes only. Not for display.
facility_id	 Facility ID		FALSE		      Facility from Densho CV (if applicable)
facility_address Facility Address str	FALSE		      Address inside facility (if applicable)
description	 Notes	          str	FALSE		      Details of the Person's time at the location

CREATE TABLE IF NOT EXISTS "names_personlocation" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "person_id" varchar(255) NOT NULL REFERENCES "names_person" ("nr_id") DEFERRABLE INITIALLY DEFERRED,
    "location_id" varchar(30) REFERENCES "names_location" ("id") DEFERRABLE INITIALLY DEFERRED,
    "facility_id" varchar(30) REFERENCES "names_facility" ("facility_id") DEFERRABLE INITIALLY DEFERRED,
    "facility_address" varchar(255),
    "entry_date" date NULL,
    "exit_date" date NULL,
    "sort_start" date NULL,
    "sort_end" date NULL,
    "notes" varchar(255)
);
CREATE INDEX "names_personlocation_person_id" ON "names_personlocation" ("person_id");
CREATE INDEX "names_personlocation_location_id" ON "names_personlocation" ("id");
CREATE INDEX "names_personlocation_facility_id" ON "names_personlocation" ("facility_id");

# Migrate PersonFacility data using simple brute-force
from names.models import PersonFacility, PersonLocation
objects = PersonFacility.objects.all()
num = len(objects)
for n,pf in enumerate(objects):
    if n % 100 == 0:
        print(f"{n}/{num} {pf}")
    pl = PersonLocation(person=pf.person, facility=pf.facility, entry_date=pf.entry_date, exit_date=pf.exit_date, sort_start=pf.entry_date, sort_end=pf.exit_date).save()

# Dump PersonFacility, process the JSONL, loaddata
python src/manage.py dumpdata --database=names --format=jsonl -o ./db/namesdb-kyuzo-YYYYMMDD-HHMM.jsonl names.PersonFacility
import json
with open('./db/namesdb-kyuzo-YYYYMMDD-HHMM.jsonl', 'r') as f:
    data = [json.loads(line) for line in f.readlines()]
for d in data:
    d['model'] = 'names.personlocation'
    d['fields']['sort_start'] = d['fields'].get('entry_date', '')
    d['fields']['sort_end']   = d['fields'].get('exit_date',  '')
lines = '\n'.join([json.dumps(d) for d in data])
with open('./db/namesdb-kyuzo-YYYYMMDD-HHMM-sorts.jsonl', 'w') as f:
    f.write(lines)
python src/manage.py loaddata --database=names ./db/namesdb-kyuzo-YYYYMMDD-HHMM-sorts.jsonl

    """
    person      = models.ForeignKey(Person, on_delete=models.DO_NOTHING)
    location    = models.ForeignKey(Location, on_delete=models.DO_NOTHING)
    facility    = models.ForeignKey(Facility, null=1, blank=1, on_delete=models.DO_NOTHING, verbose_name='Facility', help_text='Facility from Densho CV (if applicable)')
    facility_address = models.CharField(max_length=255, blank=1, verbose_name='Facility Address', help_text='Address inside facility (if applicable)')
    entry_date  = models.DateField(blank=1, verbose_name='From', help_text='Date of arrival')
    exit_date   = models.DateField(blank=1, verbose_name='To',   help_text='Date of departure')
    sort_start  = models.DateField(blank=1, verbose_name='Sort Start', help_text='Date of arrival for sort purposes only. Not for display.')
    sort_end    = models.DateField(blank=1, verbose_name='Sort End',   help_text='Date of departure for sort purposes only. Not for display.')
    notes       = models.TextField(blank=1, verbose_name='Notes', help_text="Details of the Person's time at the location")

    class Meta:
        verbose_name = 'Person-Location'
        verbose_name_plural = 'Person-Locations'

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.person_id} {self.location} {self.sort_start} {self.sort_end}>'

    def related_persons():
        """dict of Person info by nr_id
        """
        return {
            person.nr_id: {
                'nr_id': person.nr_id,
                'preferred_name': person.preferred_name,
            }
            for person in Person.objects.all()
        }

    def related_locations():
        """dict of Person info by id
        """
        return {
            str(location.id): {
                'lat': location.lat,
                'lng': location.lng,
                'address': location.address,
                'address_components': location.address_components,
                'facility_id': location.facility_id,
            }
            for location in Location.objects.all()
        }

    def related_facilities():
        """dict of Facility info by id
        """
        return {
            facility.facility_id: {
                fieldname: getattr(facility, fieldname, None)
                for fieldname in FIELDS_FACILITY
            }
            for facility in Facility.objects.all()
        }

    def dict(self, related):
        """JSON-serializable dict
        """
        # get person,location values from related instead of database
        person = related['persons'][self.person_id]
        location = related['locations'][self.location_id]
        facility = related['facilities'].get(self.facility_id, {})
        data = {
            'id': PersonLocation._make_id(
                self.person_id, self.location_id, self.entry_date
            ),
            'person_id': self.person_id,
            'person_name': person['preferred_name'],
            'location_id': self.location_id,
            'lat': location['lat'],
            'lng': location['lng'],
            'address': location['address'],
            'address_components': location['address_components'],
            'facility_id': location['facility_id'],
            'facility_name': None,
            'entry_date': self.entry_date,
            'exit_date': self.exit_date,
        }
        if facility:
            data['facility_name'] = facility['title']
        return data

    @staticmethod
    def _make_id(person_id, location_id, entry_date=''):
        if entry_date:
            if isinstance(entry_date, date):
                entry_date = entry_date.strftime('%Y%m%d')
        else:
            entry_date=''
        return '_'.join([person_id, str(location_id), entry_date])

    def post(self, related, ds):
        """Post FarRecord to Elasticsearch
        """
        data = self.dict(related)
        es_class = ELASTICSEARCH_CLASSES_BY_MODEL['personlocation']
        return es_class.from_dict(data['id'], data).save(
            index=ds.index_name('personlocation'), using=ds.es
        )


class FarRecord(models.Model):
    far_record_id           = models.CharField(max_length=255, primary_key=1, verbose_name='FAR Record ID', help_text="Derived from FAR ledger id + line id ('original_order')")
    facility                = models.CharField(max_length=255,          verbose_name='Facility', help_text='Identifier of WRA facility')
    far_page                = models.IntegerField(blank=1, verbose_name='FAR Page', help_text='Page in FAR ledger, recorded in original ledger')
    original_order          = models.CharField(max_length=255, blank=1, verbose_name='Original Order', help_text='Absolute line number in physical FAR ledger')
    family_number           = models.CharField(max_length=255, blank=1, verbose_name='WRA Family Number', help_text='WRA-assigned family number')
    far_line_id             = models.CharField(max_length=255, blank=1, verbose_name='FAR Line Number', help_text='Line number in FAR ledger, recorded in original ledger')
    last_name               = models.CharField(max_length=255, blank=1, verbose_name='Last Name', help_text='Last name corrected by transcription team')
    first_name              = models.CharField(max_length=255, blank=1, verbose_name='First Name', help_text='First name corrected by transcription team')
    other_names             = models.CharField(max_length=255, blank=1, verbose_name='Other Names', help_text='Alternate first names')
    date_of_birth           = models.CharField(max_length=255, blank=1, verbose_name='Birthdate', help_text='Full birth date')
    year_of_birth           = models.CharField(max_length=255, blank=1, verbose_name='Year of Birth', help_text='Year of birth')
    sex                     = models.CharField(max_length=255, blank=1, verbose_name='Gender', help_text='Gender identifier')
    marital_status          = models.CharField(max_length=255, blank=1, verbose_name='Marital Status', help_text='Marital status')
    citizenship             = models.CharField(max_length=255, blank=1, verbose_name='Citizenship Status', help_text='Status of US citizenship')
    alien_registration_no   = models.CharField(max_length=255, blank=1, verbose_name='Alien Registration Number', help_text='INS-issued Alien Registration number')
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
    departure_destination   = models.CharField(max_length=255, blank=1, verbose_name='Departure City/Town', help_text='Destination after departure; city/town only')
    departure_state         = models.CharField(max_length=255, blank=1, verbose_name='Departure State', help_text='Destination after departure; state only')
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
    def prep_data():
        """Prepare data for loading CSV full of FarRecords
        """
        return {}

    @staticmethod
    def load_rowd(rowd, prepped_data):
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
        return o,prepped_data

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
        """List of object Revisions"""
        return Revision.revisions(self, 'far_record_id')

    @staticmethod
    def related_persons():
        query = """
            SELECT names_farrecord.far_record_id, names_person.nr_id,
                   names_person.preferred_name
            FROM names_farrecord
            INNER JOIN names_person ON names_farrecord.person_id = names_person.nr_id
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

    @staticmethod
    def related_family():
        """Build dict of FarRecord family_number->far_record_id relations
        """
        query = """
            SELECT names_farrecord.family_number, names_farrecord.far_record_id,
                   names_farrecord.last_name, names_farrecord.first_name
            FROM names_farrecord;
        """
        x = {}
        with connections['names'].cursor() as cursor:
            cursor.execute(query)
            for fields in cursor.fetchall():
                family_number,far_record_id,last_name,first_name = fields
                if not x.get(family_number):
                    x[family_number] = []
                x[family_number].append({
                    'far_record_id': far_record_id,
                    'last_name': last_name,
                    'first_name': first_name,
                })
        return x

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
                if hasattr(self, fieldname):
                    value = str(getattr(self, fieldname, ''))
            d[fieldname] = value
        d['family'] = []
        if self.family_number and related['family'].get(self.family_number):
            d['family'] = [
                person for person in related['family'][self.family_number]
            ]
        return d

    def post(self, related, ds):
        """Post FarRecord to Elasticsearch
        """
        data = self.dict(related)
        es_class = ELASTICSEARCH_CLASSES_BY_MODEL['farrecord']
        return es_class.from_dict(data['far_record_id'], data).save(
            index=ds.index_name('farrecord'), using=ds.es
        )


class FarRecordPerson():
    """Fake class used for importing FarRecord->Person links"""

    @staticmethod
    def prep_data():
        """Prepare data for loading CSV full of PersonFacility data
        """
        return {
            'farrecords': {
                r.far_record_id: r
                for r in FarRecord.objects.all()
            },
            'persons': {
                p.nr_id: p
                for p in Person.objects.all()
            },
        }

    @staticmethod
    def load_rowd(rowd, prepped_data):
        """Prepare data for loading CSV full of FarRecordPerson data
        """
        def normalize_fieldname(rowd, data, fieldname, choices):
            for field in choices:
                if rowd.get(field):
                    data[fieldname] = rowd.get(field)
        data = {}
        normalize_fieldname(rowd, data, 'far_record_id',['far_record_id', 'fk_far_id', 'id'])
        normalize_fieldname(rowd, data, 'person_id',   ['nr_id', 'person_id'])
        # update or new
        r = prepped_data['farrecords'][data['far_record_id']]
        p = prepped_data['persons'][data['person_id']]
        r.person = p
        return r,prepped_data

    def save(self, *args, **kwargs):
        """Save FarRecord"""
        super(FarRecord, self).save()


class FarPage(models.Model):
    """
    CREATE TABLE IF NOT EXISTS "names_farpage" (
        "facility_id" varchar(30) NOT NULL REFERENCES "names_facility" ("facility_id"),
        "page" integer NOT NULL,
        "file_id" varchar(255) NOT NULL,
        "file_label" varchar(255)
    );
    CREATE INDEX "names_farpage_index" ON "names_facility" ("facility_id");
    """
    facility = models.ForeignKey(Facility, on_delete=models.DO_NOTHING)
    page = models.IntegerField(blank=False)
    file_id = models.CharField(max_length=255, primary_key=True)
    file_label = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "FAR Page"
        unique_together = ('facility', 'file_id')

    def __str__(self):
        return f'{self.facility.facility_id}_{self.page}'

    def es_id(self):
        return f'{self.facility.facility_id}_{self.page}'

    @staticmethod
    def prep_data():
        return {
            'facilities': {
                f.facility_id: f
                for f in Facility.objects.all()
            },
        }

    @staticmethod
    def load_rowd(rowd, prepped_data):
        o = FarPage()
        for key,val in rowd.items():
            if val:
                if key == 'facility':
                    val = prepped_data['facilities'][val]
                setattr(o, key, val)
        return o,prepped_data

    def save(self, *args, **kwargs):
        super(FarPage, self).save()

    def dict(self, n=None):
        """JSON-serializable dict
        """
        d = {}
        if n:
            d['n'] = n
        for fieldname in FIELDS_FARPAGE:
            if fieldname == 'far_page_id':
                value = self.es_id()
                d[fieldname] = value
            elif getattr(self, fieldname):
                value = getattr(self, fieldname)
                d[fieldname] = value
        return d

    def post(self, related, ds):
        """Post FarPage to Elasticsearch
        """
        if not self.page:
            return
        data = self.dict()
        es_class = ELASTICSEARCH_CLASSES_BY_MODEL['farpage']
        return es_class.from_dict(data['far_page_id'], data).save(
            index=ds.index_name('farpage'), using=ds.es
        )


class WraRecord(models.Model):
    wra_record_id     = models.CharField(max_length=255, primary_key=1, verbose_name='WRA Record ID', help_text="Derived from WRA ledger id + line id ('original_order')")
    wra_filenumber    = models.CharField(max_length=255,          verbose_name='WRA Filenumber', help_text='WRA-assigned 6-digit filenumber identifier')
    facility          = models.CharField(max_length=255,          verbose_name='Facility identifier', help_text='Facility identifier')
    lastname          = models.CharField(max_length=255, blank=1, verbose_name='Last name', help_text='Last name, truncated to 10 chars')
    firstname         = models.CharField(max_length=255, blank=1, verbose_name='First name', help_text='First name, truncated to 8 chars')
    middleinitial     = models.CharField(max_length=255, blank=1, verbose_name='Middle initial', help_text='Middle initial')
    birthyear         = models.CharField(max_length=255, blank=1, verbose_name='Year of birth', help_text='Year of birth')
    gender            = models.CharField(max_length=255, blank=1, verbose_name='Gender', help_text='Gender')
    originalstate     = models.CharField(max_length=255, blank=1, verbose_name='State of residence immediately prior to census', help_text='State of residence immediately prior to census')
    familyno          = models.CharField(max_length=255, blank=1, verbose_name='WRA-assigned family identifier', help_text='WRA-assigned family identifier')
    individualno      = models.CharField(max_length=255, blank=1, verbose_name='Family identifier + alpha char by birthdate', help_text='Family identifier + alpha char by birthdate')
    notes             = models.CharField(max_length=255, blank=1, verbose_name='Notes added by Densho during processing', help_text='Notes added by Densho during processing')
    assemblycenter    = models.CharField(max_length=255,          verbose_name='Assembly center prior to camp', help_text='Assembly center prior to camp')
    originaladdress   = models.CharField(max_length=255, blank=1, verbose_name='County/city + state of pre-exclusion address (coded)', help_text='County/city + state of pre-exclusion address; coded by WRA')
    birthcountry      = models.CharField(max_length=255, blank=1, verbose_name='Birth countries of father and mother (coded)', help_text='Birth countries of father and mother; coded by WRA')
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
    occupqual1        = models.CharField(max_length=255, blank=1, verbose_name='Primary qualified occupation', help_text='Primary qualified occupation; coded')
    occupqual2        = models.CharField(max_length=255, blank=1, verbose_name='Secondary qualified occupation', help_text='Secondary qualified occupation; coded')
    occupqual3        = models.CharField(max_length=255, blank=1, verbose_name='Tertiary qualified occupation', help_text='Tertiary qualified occupation; coded')
    occuppotn1        = models.CharField(max_length=255, blank=1, verbose_name='Primary potential occupation', help_text='Primary potential occupation; coded')
    occuppotn2        = models.CharField(max_length=255, blank=1, verbose_name='Secondary potential occupation', help_text='Secondary potential occupation; coded')
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
    def prep_data():
        """Prepare data for loading CSV full of FarRecords
        """
        return {}

    @staticmethod
    def load_rowd(rowd, prepped_data):
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
        return o,prepped_data

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
        """List of object Revisions"""
        return Revision.revisions(self, 'wra_record_id')

    @staticmethod
    def related_persons():
        query = """
            SELECT names_wrarecord.wra_record_id, names_person.nr_id,
                   names_person.preferred_name
            FROM names_wrarecord
            INNER JOIN names_person ON names_wrarecord.person_id = names_person.nr_id
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

    @staticmethod
    def related_family():
        """Build dict of WraRecord family_number->far_record_id relations
        """
        query = """
            SELECT names_wrarecord.familyno, names_wrarecord.wra_record_id,
                   names_wrarecord.lastname, names_wrarecord.firstname
            FROM names_wrarecord;
        """
        x = {}
        with connections['names'].cursor() as cursor:
            cursor.execute(query)
            for fields in cursor.fetchall():
                familyno,wra_record_id,lastname,firstname = fields
                if not x.get(familyno):
                    x[familyno] = []
                x[familyno].append({
                    'wra_record_id': wra_record_id,
                    'lastname': lastname,
                    'firstname': firstname,
                })
        return x

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
        d['family'] = []
        if self.familyno and related['family'].get(self.familyno):
            d['family'] = [
                person for person in related['family'][self.familyno]
            ]
        return d

    def post(self, related, ds):
        """Post WraRecord to Elasticsearch
        """
        data = self.dict(related)
        es_class = ELASTICSEARCH_CLASSES_BY_MODEL['wrarecord']
        return es_class.from_dict(data['wra_record_id'], data).save(
            index=ds.index_name('wrarecord'), using=ds.es
        )


class WraRecordPerson():
    """Fake class used for importing WraRecord->Person links"""

    @staticmethod
    def prep_data():
        """Prepare data for loading CSV full of WraRecordPerson data
        """
        return {
            'wrarecords': {
                r.wra_record_id: r
                for r in WraRecord.objects.all()
            },
            'persons': {
                p.nr_id: p
                for p in Person.objects.all()
            },
        }

    @staticmethod
    def load_rowd(rowd, prepped_data):
        """Given a rowd dict from a CSV, return a WraRecord object
        """
        def normalize_fieldname(rowd, data, fieldname, choices):
            for field in choices:
                if rowd.get(field):
                    data[fieldname] = rowd.get(field)
        data = {}
        normalize_fieldname(rowd, data, 'wra_record_id',['wra_filenumber', 'fk_wra_id', 'id'])
        normalize_fieldname(rowd, data, 'person_id',   ['nr_id', 'person_id'])
        # update or new
        r = prepped_data['wrarecords'][data['wra_record_id']]
        p = prepped_data['persons'][data['person_id']]
        r.person = p
        return r,prepped_data

    def save(self, *args, **kwargs):
        """Save WraRecord"""
        super(WraRecord, self).save()


IREIRECORD_FIELDS = [
    'person_id',
    'irei_id',
    'fetch_ts',
    'year',
    'birthday',  # -> birthdate',
    'lastname',
    'firstname',
    'middlename',
    'preferredname',
    'camp',  # list
]

IREI_WALL_FIELDS = {
    'id': 'irei_id',
    'name': 'name',
    'birthday': 'birthday',
    'year': 'year',
    'camps': 'camps',
    '_fetch_ts': 'fetch_ts',
}

IREI_API_FIELDS = {
    'id': 'irei_id',
    'firstName': 'firstname',
    'middleName': 'middlename',
    'lastName': 'lastname',
    'birthday': 'birthday',
    '_fetch_ts': 'fetch_ts',
}

class IreiRecord(models.Model):
    """Irei data from the pubsite-people-*.json files, retrieved by ireizo-fetch/ireizo-pubsite-fetch.py
    
    For some reason Django did not make a migration for IreiRecord so...
    
    CREATE TABLE IF NOT EXISTS "names_ireirecord" (
        "irei_id" varchar(255) NOT NULL PRIMARY KEY,
        "person_id" varchar(255) NULL REFERENCES "names_person" ("nr_id") DEFERRABLE INITIALLY DEFERRED,
        "year" varchar(255),
        "birthday" varchar(255) NOT NULL,
        "birthdate" date,
        "name" varchar(255) NOT NULL,
        "lastname" varchar(255) NOT NULL,
        "firstname" varchar(255) NOT NULL,
        "middlename" varchar(255) NOT NULL,
        "camps" varchar(255) NOT NULL,
        "fetch_ts" date,
        "timestamp" datetime
    );
    CREATE INDEX "names_ireirecord_person_id_76c77728" ON "names_ireirecord" ("irei_id");
    CREATE INDEX "names_ireirecord_person_id_876c7772" ON "names_ireirecord" ("person_id");
    """
    irei_id   = models.CharField(max_length=255, primary_key=1, verbose_name='Irei ID')
    person    = models.ForeignKey(Person, on_delete=models.DO_NOTHING, blank=1, null=1)
    year       = models.CharField(max_length=255, blank=1, verbose_name='Birth year')
    birthday   = models.CharField(max_length=255, blank=1, verbose_name='Birthday')
    birthdate  = models.DateField(max_length=255, blank=1, verbose_name='Birth date')
    name       = models.CharField(max_length=255, blank=1, verbose_name='Name')
    lastname   = models.CharField(max_length=255, blank=1, verbose_name='Last name')
    firstname  = models.CharField(max_length=255, blank=1, verbose_name='First name')
    middlename = models.CharField(max_length=255, blank=1, verbose_name='Middle name')
    camps      = models.CharField(max_length=255, blank=1, verbose_name='Camps')
    fetch_ts  = models.DateField(auto_now_add=True, blank=1, null=1, verbose_name='Last fetched')
    timestamp  = models.DateTimeField(auto_now=True,       verbose_name='Last Modified')

    class Meta:
        verbose_name = "Irei Record"

    def __repr__(self):
        return '<{}(irei_id={})>'.format(
            self.__class__.__name__, self.irei_id
        )

    def __str__(self):
        return self.irei_id

    def save(self, *args, **kwargs):
        """Save IreiRecord
        """
        ## has the record changed?
        #try:
        #    old = IreiRecord.objects.get(irei_id=self.irei_id)
        #except IreiRecord.DoesNotExist:
        #    old = None
        #changed = Revision.object_has_changed(self, old, IreiRecord)
        ## now save
        self.timestamp = timezone.now()
        super(IreiRecord, self).save()
        #if changed:
        #    r = Revision(
        #        content_object=self,
        #        username=username, note=note, diff=make_diff(old, self)
        #    )
        #    r.save()

    @staticmethod
    def load_irei_data(rowds_api, rowds_wall):
        """Loads API & Wall data, reconciles them, adds/updates IreiRecord
        """
        irei_records = {}
        # load wall data into dict - already has irei_ids
        for rowd in rowds_wall:
            # convert keys from Irei's fieldnames to ours
            data = {
                modelfield: rowd.get(filefield)
                for filefield,modelfield in IREI_WALL_FIELDS.items()
            }
            irei_id = data['irei_id']
            irei_records[irei_id] = data
        # add API data to irei_people (depends on API data having irei_id)
        for rowd in rowds_api:
            # convert keys from Irei's fieldnames to ours
            data = {
                modelfield: rowd.get(filefield)
                for filefield,modelfield in IREI_API_FIELDS.items()
            }
            irei_id = data.get('irei_id')
            # if there's irei_id, match irei_people item and add API data
            # NOTE API data overwrites WALL data with same fieldname
            if irei_id and irei_records.get(irei_id):
                record = irei_records[irei_id]
                for field,value in data.items():
                    record[field] = value
                irei_records[irei_id] = record
        return irei_records

    @staticmethod
    def save_record(rowd, fetchdate=date.today()):
        """Add or update an IreiRecord based on rowd
        """
        irei_id = rowd.pop('irei_id')
        try:
            record = IreiRecord.objects.get(irei_id=irei_id)
            new = False
        except:
            record = IreiRecord(irei_id=irei_id)
            new = True
        changed = []
        # special formatting
        # year
        if rowd.get('year'):
            rowd['year'] = str(rowd['year'])
        # birthday -> birthdate
        if rowd.get('birthday') and rowd['birthday'] != record.birthday:
            record.birthday = rowd.pop('birthday')
            try:
                record.birthdate = parser.parse(record.birthday)
            except parser._parser.ParserError:
                record.birthdate = None
            changed.append('birthday')
        # camps
        camps = '; '.join(rowd.pop('camps'))
        if camps and camps != record.camps:
            record.camps = camps
            changed.append('camps')
        # everything else
        for fieldname,value in rowd.items():
            if rowd.get(fieldname) and rowd[fieldname] != getattr(record,fieldname):
                setattr(record, fieldname, value)
                changed.append(fieldname)
        if new:
            record.fetch_ts = fetchdate
            record.save()
            return 'created'
        elif changed:
            record.fetch_ts = fetchdate
            record.save()
            return f'updated {changed}'
        return None

    @staticmethod
    def related_persons():
        query = """
            SELECT names_ireirecord.irei_id, names_person.nr_id,
                   names_person.preferred_name
            FROM names_ireirecord
            INNER JOIN names_person ON names_ireirecord.person_id = names_person.nr_id
        """
        with connections['names'].cursor() as cursor:
            cursor.execute(query)
            return {
                irei_id: {
                    'nr_id': nr_id, 'preferred_name': preferred_name
                }
                for irei_id,nr_id,preferred_name in cursor.fetchall()
                if nr_id
            }

    def dict(self, related):
        """JSON-serializable dict
        """
        d = {'id': self.irei_id}
        for fieldname in FIELDS_IREIRECORD:
            if fieldname == 'person':
                value = None
                if related['persons'].get(self.irei_id):
                    person = related['persons'][self.irei_id]
                    value = {
                        'id': person['nr_id'],
                        'name': person['preferred_name'],
                    }
            else:
                value = str(getattr(self, fieldname, ''))
            d[fieldname] = value
        return d

    def post(self, related, ds):
        """Post IreiRecord to Elasticsearch
        """
        data = self.dict(related)
        es_class = ELASTICSEARCH_CLASSES_BY_MODEL['ireirecord']
        return es_class.from_dict(data['irei_id'], data).save(
            index=ds.index_name('ireirecord'), using=ds.es
        )

    

class IreiRecordPerson():
    """Fake class used for importing IreiRecord->Person links"""


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
    def revisions(obj, fieldname):
        """List of revisions for object
        
        @param obj: OBJECT The object
        @param fieldname: str Name of primary key field
        """
        return Revision.objects.filter(
            content_type=ContentType.objects.get(
                app_label=obj._meta.app_label, model=obj._meta.model_name
            ),
            object_id=getattr(obj, fieldname)
        )

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
                try:
                    old_value = getattr(old_object, field.name)
                except Person.DoesNotExist:  # Far/WraRecord.person is missing
                    old_value = None
                try:
                    new_value = getattr(new_object, field.name)
                except Person.DoesNotExist:  # Far/WraRecord.person is missing
                    new_value = None
                if new_value and (not (old_value == new_value)):
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
    'location': Location,
    'person': Person,
    'personfacility': PersonFacility,
    'personlocation': PersonLocation,
    'farrecord': FarRecord,
    'wrarecord': WraRecord,
    'farrecordperson': FarRecordPerson,
    'wrarecordperson': WraRecordPerson,
    'ireirecord': IreiRecord,
    'ireirecordperson': IreiRecordPerson,
    'farpage': FarPage,
}

def dump_csv(output, model_class, ids, search, cols, limit=None, debug=False):
    """Writes rowds of specified model class to STDOUT
    """
    writer = fileio.csv_writer(output)
    if debug: print(f'header {cols}')
    writer.writerow(cols)
    
    if ids:
        query = model_class.objects.filter(pk__in=ids)
    elif search:
        # TODO SEARCH IS HORRIBLY UNSAFE!!!
        query = model_class.objects.filter(**search)
    else:
        query = model_class.objects.all()
    
    n = 0
    if limit:
        for o in query[:limit]:
            row = list(o.dump_rowd(cols).values())
            if debug: print(f'{n}/{limit} row {row}')
            writer.writerow(row)
            n += 1
    else:
        num = len(query)
        for o in query:
            row = list(o.dump_rowd(cols).values())
            if debug: print(f'{n}/{num} {row[0]}')
            writer.writerow(row)
            n += 1
