from dateutil import parser
import difflib

from django.db import models

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


class FarRecord(models.Model):
    """FAR/WRA record model
    
    m_pseudoid = m_camp + lastname + birthyear + firstname
    """
    timestamp = models.DateTimeField(auto_now_add=True)
    dataset = models.CharField(max_length=30)
    pseudoid = models.CharField(max_length=30, primary_key=True, verbose_name='Pseudo ID')
    camp = models.CharField(max_length=30, blank=1)
    lastname = models.CharField(max_length=30, blank=1, verbose_name='Last Name')
    firstname = models.CharField(max_length=30, blank=1, verbose_name='First Name')
    birthyear = models.CharField(max_length=30, blank=1, verbose_name='Birth Year')
    gender = models.CharField(max_length=30, blank=1)
    originalstate = models.CharField(max_length=30, blank=1, verbose_name='Original State')
    familyno = models.CharField(max_length=30, blank=1, verbose_name='Family Number')
    individualno = models.CharField(max_length=30, blank=1, verbose_name='Individual Number')
    altfamilyid = models.CharField(max_length=30, blank=1, verbose_name='Alt Family ID')
    altindividualid = models.CharField(max_length=30, blank=1, verbose_name='Alt Indiv ID')
    ddrreference = models.CharField(max_length=30, blank=1, verbose_name='DDR Reference')
    notes = models.CharField(max_length=30, blank=1)
    #
    othernames = models.CharField(max_length=30, blank=1, verbose_name='Other Names')
    maritalstatus = models.CharField(max_length=30, blank=1, verbose_name='Marital Status')
    citizenship = models.CharField(max_length=30, blank=1)
    alienregistration = models.CharField(max_length=30, blank=1, verbose_name='Alien Registration')
    entrytype = models.CharField(max_length=30, blank=1, verbose_name='Entry Type')
    entrydate = models.CharField(max_length=30, blank=1, verbose_name='Entry Date')
    originalcity = models.CharField(max_length=30, blank=1, verbose_name='Original City')
    departuretype = models.CharField(max_length=30, blank=1, verbose_name='Departure Type')
    departuredate = models.CharField(max_length=30, blank=1, verbose_name='Departure Date')
    destinationcity = models.CharField(max_length=30, blank=1, verbose_name='Destination City')
    destinationstate = models.CharField(max_length=30, blank=1, verbose_name='Destination State')
    campaddress = models.CharField(max_length=30, blank=1, verbose_name='Camp Address')
    farlineid = models.CharField(max_length=30, blank=1, verbose_name='FAR Line ID')
    errors = models.TextField(blank=1)

    class Meta:
        verbose_name = "FAR Record"

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.pseudoid}>'

    def save(self, username=None, *args, **kwargs):
        # request.user added to obj in names.admin.FarRecordAdmin.save_model
        if getattr(self, 'user', None):
            username = getattr(self, 'user').username
        # get existing record
        try:
            old = FarRecord.objects.get(pseudoid=self.pseudoid)
        except FarRecord.DoesNotExist:
            old = None
        # should be field in admin
        note = ''
        r = Revision(
            dataset=self.dataset, pseudoid=self.pseudoid,
            username=username, note=note, diff=make_diff(old, self)
        )
        r.save()
        super(FarRecord, self).save()

    def revisions(self):
        return Revision.objects.filter(pseudoid=self.pseudoid)


class WraRecord(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    dataset = models.CharField(max_length=30)
    pseudoid = models.CharField(max_length=30, primary_key=True, verbose_name='Pseudo ID')
    camp = models.CharField(max_length=30, blank=1)
    lastname = models.CharField(max_length=30, blank=1, verbose_name='Last Name')
    firstname = models.CharField(max_length=30, blank=1, verbose_name='First Name')
    birthyear = models.CharField(max_length=30, blank=1, verbose_name='Birth Year')
    gender = models.CharField(max_length=30, blank=1)
    originalstate = models.CharField(max_length=30, blank=1, verbose_name='Original State')
    familyno = models.CharField(max_length=30, blank=1, verbose_name='Family Number')
    individualno = models.CharField(max_length=30, blank=1, verbose_name='Individual Number')
    altfamilyid = models.CharField(max_length=30, blank=1, verbose_name='Alt Family ID')
    altindividualid = models.CharField(max_length=30, blank=1, verbose_name='Alt Indiv ID')
    ddrreference = models.CharField(max_length=30, blank=1, verbose_name='DDR Reference')
    notes = models.CharField(max_length=30, blank=1)
    #
    assemblycenter = models.CharField(max_length=30, blank=1, verbose_name='Assembly Center')
    originaladdress = models.CharField(max_length=30, blank=1, verbose_name='Original Address')
    birthcountry = models.CharField(max_length=30, blank=1, verbose_name='Birth Country')
    fatheroccupus = models.CharField(max_length=30, blank=1, verbose_name='Father Occup US')
    fatheroccupabr = models.CharField(max_length=30, blank=1, verbose_name='Father Occup abr')
    yearsschooljapan = models.CharField(max_length=30, blank=1, verbose_name='Years School Japan')
    gradejapan = models.CharField(max_length=30, blank=1, verbose_name='Grade Japan')
    schooldegree = models.CharField(max_length=30, blank=1, verbose_name='School Degree')
    yearofusarrival = models.CharField(max_length=30, blank=1, verbose_name='Year of US Arrival')
    timeinjapan = models.CharField(max_length=30, blank=1, verbose_name='Time in Japan')
    notimesinjapan = models.CharField(max_length=30, blank=1, verbose_name='No times in japan')
    ageinjapan = models.CharField(max_length=30, blank=1, verbose_name='Age In Japan')
    militaryservice = models.CharField(max_length=30, blank=1, verbose_name='Military Service')
    maritalstatus = models.CharField(max_length=30, blank=1, verbose_name='Marital Status')
    ethnicity = models.CharField(max_length=30, blank=1)
    birthplace = models.CharField(max_length=30, blank=1)
    citizenshipstatus = models.CharField(max_length=30, blank=1, verbose_name='Citizenship Status')
    highestgrade = models.CharField(max_length=30, blank=1, verbose_name='Highest Grade')
    language = models.CharField(max_length=30, blank=1)
    religion = models.CharField(max_length=30, blank=1)
    occupqual1 = models.CharField(max_length=30, blank=1)
    occupqual2 = models.CharField(max_length=30, blank=1)
    occupqual3 = models.CharField(max_length=30, blank=1)
    occuppotn1 = models.CharField(max_length=30, blank=1)
    occuppotn2 = models.CharField(max_length=30, blank=1)
    filenumber = models.CharField(max_length=30, blank=1, verbose_name='File Number')
    errors = models.TextField(blank=1)

    class Meta:
        verbose_name = "WRA Record"

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.pseudoid}>'

    def save(self, username=None, *args, **kwargs):
        # request.user added to obj in names.admin.WraRecordAdmin.save_model
        if getattr(self, 'user', None):
            username = getattr(self, 'user').username
        # get existing record
        try:
            old = WraRecord.objects.get(pseudoid=self.pseudoid)
        except WraRecord.DoesNotExist:
            old = None
        # should be field in admin
        note = ''
        r = Revision(
            dataset=self.dataset, pseudoid=self.pseudoid,
            username=username, note=note, diff=make_diff(old, self)
        )
        r.save()
        super(WraRecord, self).save()

    def revisions(self):
        return Revision.objects.filter(pseudoid=self.pseudoid)


class Revision(models.Model):
    dataset = models.CharField(max_length=30)
    pseudoid = models.CharField(max_length=30, verbose_name='Pseudo ID')
    timestamp = models.DateTimeField(auto_now_add=True)
    username = models.CharField(max_length=255)
    note = models.CharField(max_length=255, blank=1)
    diff = models.TextField()

    def __repr__(self):
        return f'<Revision {self.timestamp} {self.pseudoid} {self.username}>'

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
    for n,rowd in enumerate(csvfile.make_rowds(fileio.read_csv(csv_path))):
        if num_records and (n > num_records):
            break
        record = class_()
        print(n,rowd['m_pseudoid'])
        for key,val in rowd.items():
            key = key[2:]  # remove prefix
            if val:
                setattr(record, key, val)
        record.save(username=username, note='CSV import')
