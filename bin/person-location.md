# PersonLocation


## Geocode FarRecord addresses

(Skip this whole step if you already have `namesdb-far-addresses-1.csv` and `-2.csv`.)

Collect a giant list of deduplicated and sorted addresses from FAR, WRA records, geocode them, and write to CSV so we don't have to keep hitting Geocod.io.

First get a Geocod.io account.  Actually, get two of them because you can only geocode 2500 at a time and we have ~3700.  Make an API key for each of them and plug them into the `API_KEY` variables below.

``` python
# Make the giant deduplicated and sort list
from names import models
farrecords = models.FarRecord.objects.all()
# Make tuples from pre_evac and departure fields
# (state, city) for sorting
far_pre_evacuation = list(set([
    (far.pre_evacuation_state, far.pre_evacuation_address)
    for far in farrecords
    if far.pre_evacuation_address and far.pre_evacuation_state
]))
far_departure = list(set([
    (far.departure_state, far.departure_destination)
    for far in farrecords
    if far.departure_destination and far.departure_state
]))
# set() deduplicates list items
# list() turns that into a normal list
# sorted() sorts the list
addresses_sorted = sorted(list(set(far_pre_evacuation + far_departure)))
# Flip the (state,city) tuples back to "city, state" strings
addresses = [f"{address}, {state}" for state,address in addresses_sorted]

import requests
def geocodio_batch_address(API_KEY, addresses=[]):
    """Geocode a whole list of addresses at once."""
    url = f'https://api.geocod.io/v1.7/geocode?api_key={API_KEY}'
    response = requests.post(url, json=addresses)
    data = response.json()
    try:
        results = data['results']
    except KeyError:
        print(data)
        import sys; sys.exit(1)
    address_latlngs = []
    for n,result in enumerate(results):
        try:
            address_latlngs.append({
                'lat': result['response']['results'][0]['location']['lat'],
                'lng': result['response']['results'][0]['location']['lng'],
                'address': addresses[n],
                'address_components': result['response']['input']['address_components'],
            })
        except:
            print(result)
            #TODO keep in list so we know what to fix
            assert False
    return address_latlngs

# geocode them and write to CSV

API_KEY = FIRST_API_KEY_HERE
addrs1 = geocodio_batch_address(API_KEY, addresses[:2000])
import csv
with open('/tmp/namesdb-far-addresses-1.csv', 'w', newline='') as csvfile:
    fieldnames = ['lat', 'lng', 'address', 'address_components']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for addr in addrs1:
        writer.writerow(addr)

API_KEY = SECOND_API_KEY_HERE
addrs2 = models.geocodio_batch_address(api_key, addresses[2000:])
import csv
with open('/tmp/namesdb-far-addresses-2.csv', 'w', newline='') as csvfile:
    fieldnames = ['lat', 'lng', 'address', 'address_components']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for addr in addrs2:
        writer.writerow(addr)
```


## Back up current data

``` bash
# supervisorctl stop namesdbeditor
# su ddr
$ cd /opt/namesdb-editor/db
$ cp namesregistry.db namesregistry.db.kyuzo.20230908-1651
$ cp django.db django.db.kyuzo.20230908-1651
$ tar czf django.db.kyuzo.20230908-1651.tgz django.db.kyuzo.20230908-1651
$ tar czf namesregistry.db.kyuzo.20230908-1651.tgz namesregistry.db.kyuzo.20230908-1651
$ mv *.tgz backups/
```

## TODO Update `namesdb-editor`

``` bash
cd /opt/densho-vocab
git pull
cd /opt/namesdb-editor
git checkout develop
git pull
make install
```


## TODO Add Facility.tgn field

``` sql
ALTER TABLE names_facility ADD COLUMN tgn_id varchar(32) NULL;
```

Add tgn data from facility.json

``` python
import json
from names import models
with open('/opt/densho-vocab/api/0.2/facility.json', 'r') as f:
    data = json.loads(f.read())

for f in data['terms']:
    if f['location'].get('tgn_id'):
        facility = models.Facility.objects.get(facility_id=f['sos_facility_id'])
        facility.tgn_id = f['location']['tgn_id']
        facility.save()

# show that we in fact imported them
for f in models.Facility.objects.all():
    f, f.tgn_id
```


## Location

Add names_location table

``` sql
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
```

Make `Locations` from `Facility` objects

``` python
from names import models
facilities = sorted(models.Facility.objects.all())
for facility in facilities:
    facility
    location = models.Location()
    location.lat     = facility.location_lat
    location.lng     = facility.location_lng
    location.address     = facility.location_label
    location.address_components = ''
    location.facility    = facility
    location.notes       = 'source: Facility'
    location.save()
```

Load FarRecord location data from `namesdb-far-addresses-1.csv` and `-2.csv`

``` python
from names import models
import csv
CSV_FILES = [
    'namesdb-far-addresses-1.csv',
    'namesdb-far-addresses-2.csv',
]
for csvpath in CSV_FILES:
    print(f"{csvpath=}")
    locations = []
    with open(csvpath, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            #print(row)
            location = models.Location(
                lat=row['lat'],
                lng=row['lng'],
                address=row['address'],
                address_components=row['address_components'],
            )
            #print(location)
            locations.append(location)
    print(f"{len(locations)} Locations")
    objects = models.Location.objects.bulk_create(locations)
    print(f"{len(objects)} saved")
```


## PersonLocation

Add names_personlocation table

``` sql
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
```

TODO Make PersonLocation records from FarRecords `pre_exclusion_*`, `facility`, and `departure_*` fields.

``` python
from datetime import date
from dateutil import parser
from names import models
note = f'Imported {date.today()} gjost'
locations = models.Location.objects.all()
farrecords = models.FarRecord.objects.all()
persons = models.Person.objects.all()
facilities_by_id = {
    facility.facility_id: facility for facility in models.Facility.objects.all()
}
locations_by_facilityid = {
    location.facility_id: location
    for location in locations
    if location.facility
}
locations_by_citystate = {
    location.address: location for location in locations
}
persons_by_nrid = {
    person.nr_id: person for person in persons
}
persons_by_farrecordid = {
    fr.far_record_id: persons_by_nrid[fr.person_id]
    for fr in farrecords
    if fr.person_id
}

def add_date(farrecord, frfield, personlocation, plfield):
    text = getattr(farrecord, frfield)
    try:
        setattr(
            personlocation, plfield, parser.parse(text).date()
        )
    except parser._parser.ParserError:
        lines = personlocation.notes.splitlines()
        lines.append(f'ERROR {plfield} farrecord.{frfield} "{text}"')
        personlocation.notes = '\n'.join(lines)

def make_personlocation(n, farrecord):
    pre_evac_pl = None; facility_pl = None; departure_pl = None

    try:
        person = persons_by_farrecordid[farrecord.far_record_id]
    except KeyError:
        return None

    pre_evac_loc = locations_by_citystate[
        f"{farrecord.pre_evacuation_address}, {farrecord.pre_evacuation_state}"
    ]
    if pre_evac_loc:
        pre_evac_pl = models.PersonLocation(
            person=person,
            location=pre_evac_loc,
            notes=note,
        )
        add_date(farrecord, 'date_of_original_entry', pre_evac_pl, 'exit_date')
        add_date(farrecord, 'date_of_original_entry', pre_evac_pl, 'sort_end')

    if farrecord.facility:
        facility_pl = models.PersonLocation(
            person=person,
            location=locations_by_facilityid[farrecord.facility],
            facility=facilities_by_id[farrecord.facility],
            facility_address=farrecord.camp_address_original,
            notes=note,
        )
        add_date(farrecord, 'date_of_original_entry', facility_pl, 'entry_date')
        add_date(farrecord, 'departure_date',         facility_pl, 'exit_date')
        add_date(farrecord, 'date_of_original_entry', facility_pl, 'sort_start')
        add_date(farrecord, 'departure_date',         facility_pl, 'sort_end')

    departure_loc = locations_by_citystate[
        f"{farrecord.departure_destination}, {farrecord.departure_state}"
    ]
    if departure_loc:
        departure_pl = models.PersonLocation(
            person=person,
            location=departure_loc,
            notes=note,
        )
        add_date(farrecord, 'departure_date', departure_pl, 'entry_date')
        add_date(farrecord, 'departure_date', departure_pl, 'sort_start')

    return pre_evac_pl,facility_pl,departure_pl

personlocations = []
errors = []
for n,farrecord in enumerate(farrecords):
    try:
        result = make_personlocation(n, farrecord)
    except KeyError:
        result = None
    if result:
        for item in result:
            if item:
                personlocations.append(item)
            else:
                errors.append(farrecord)
    else:
        errors.append(farrecord)

# write FarRecord IDs for errors
with open('db/personlocation-error-fars.csv', 'w') as f:
    f.write(
        '\n'.join([
            far.far_record_id for far in errors
        ])
    )

from itertools import zip_longest
def grouper(iterable, n, fillvalue=None):
    """Breaks up a list into chunks"""
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)

group_size = 1000
total_saved = 0
total = len(personlocations)
for plgroup in grouper(personlocations, n=group_size):
    objects = models.PersonLocation.objects.bulk_create(
        [pl for pl in plgroup if pl]
    )
    total_saved += group_size
    print(f"{total_saved}/{total}")
```


## Fix JSON

Find any `Locations` where `address_components` includes a single-quote, and fix these manually:
``` python
import json
from names import models
for l in models.Location.objects.all():
    if l.address_components == '':
        continue
    if l.address_components.count("'") % 2:
        l,l.address_components
```

Then run this script to convert all single-quotes in `address_components` to double-quotes:
``` python
import json
from names import models
for l in models.Location.objects.all():
    if l.address_components == '':
        continue
    try:
        data = json.loads(l.address_components)
        l.address_components
    except json.decoder.JSONDecodeError:
        f'UPDATING {l.address_components}'
        l.address_components = l.address_components.replace("'", '"')
        l.save()
```

And then run this to see if any non-parseable JSON is left:
``` python
import json
from names import models
for l in models.Location.objects.all():
    if l.address_components == '':
        continue
    try:
        data = json.loads(l.address_components)
    except json.decoder.JSONDecodeError:
        f'ERROR {l} {l.address_components}'
```

There may be `Locations` with a single-quote in the city name e.g. "O'Brien".
