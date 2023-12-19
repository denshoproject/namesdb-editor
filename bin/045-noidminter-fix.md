# Fix malformed NRIDs

See https://github.com/denshoproject/namesdb-editor/issues/45


## Generate CSV matching the malformed NRIDs to new good ones

Run the following on `kyuzo`:

``` bash
sudo su ddr
cd /opt/namesdb-editor/
make shell
```

Run the following in the `namesdb-editor` virtualenv:

``` python
# Get the 184 bad NRIDs
from names import models
bad_nrids = [
    person.nr_id
    for person in models.Person.objects.filter(nr_id__icontains='88922/ddr00')
]

# Get a copy with the names just because
bad_nrids_annotated = [
    (person.nr_id, person.preferred_name)
    for person in models.Person.objects.filter(nr_id__icontains='88922/ddr00')
]
# write to a file
FILENAME = '/tmp/20231206-noids-bad-annotated.csv'
lines = [f'{nr_id}, "{preferred_name}"\n' for nr_id,preferred_name in bad_nrids_annotated]
with open(FILENAME, 'w') as f:
    f.writelines(lines)

# Generate 184 new NRIDs
# Source: https://github.com/denshoproject/names-merge-explorer/blob/master/densho-names-nrimportprep.ipynb
import requests
def getNRIds(num,endpoint,user,pswd):
    #idservice fails if number of requested ids is too high
    max_jobs = 5000
    template = 'nr.zeedeedk'
    url = '{}/noid/api/1.0/{}/'.format(endpoint,template)
    ids = []
    idreqs = []
    if num <= max_jobs:
        idreqs.append(num)
    else:
        idreqs = [max_jobs for number in range(num//max_jobs)]
        idreqs.append(num % max_jobs)
    for job in idreqs:
        print(f"Requesting batch of {job} ids")
        r = requests.post(url, data={'num': job}, auth=(user,pswd))
        if r.status_code == 200:
            for id_item in r.json():
                ids.append(id_item)
            print(f"Request complete")
        else:
            print(f"Something went wrong. Status code: {r.status_code}")
    return ids

ENDPOINT = 'http://127.0.0.1:8082'
USERNAME = 'gfroh'
PASSWORD = 'REDACTED'

new_nrids = getNRIds(184, ENDPOINT, USERNAME, PASSWORD)

# pair each existing bad NRID with a new good one
lines = [
    f"{bad_nrid},{new_nrids[n]}\n"
    for n,bad_nrid in enumerate(bad_nrids)
]

# write to a file
FILENAME = '/tmp/20231206-noids-to-fix.csv'
with open(FILENAME, 'w') as f:
    f.writelines(lines)
```

Move file
``` bash
sudo mv /tmp/20231206-noids-to-fix.csv /opt/namesdb-editor/
```

Get timestamp of earliest bad NRID
``` python
from datetime import datetime, timezone
earliest = datetime.now(timezone.utc)
for person in models.Person.objects.filter(nr_id__icontains='88922/ddr00'):
    if person.timestamp < earliest:
        earliest = person.timestamp

earliest
>>> datetime.datetime(2023, 6, 27, 4, 25, 50, 751000, tzinfo=datetime.timezone.utc)
```


## Narrow the list of Collections to those containing bad NRIDs

Get list of Collections with last-modified timestamps from CGIT.  Select collections modified since the earliest bad NRID.

Run the following on `kyuzo`:

``` bash
sudo su ddr
cd /opt/ddr-cmdln/
make shell
```

Run the following in the `ddr-cmdln` virtualenv:

``` python
EARLIEST = datetime.datetime(2023, 6, 27, 4, 25, 50, 751000, tzinfo=datetime.timezone.utc)
CGIT_USERNAME = 'gjost'
CGIT_PASSWORD = 'REDACTED'

import datetime
from dateutil import parser
from DDR import dvcs
from DDR import identifier
cgit = dvcs.Cgit()
cgit.username = CGIT_USERNAME
cgit.password = CGIT_PASSWORD
repositories = []
for repo in cgit.repositories():
    try:
        oi = identifier.Identifier(repo['id'])
    except:
        oi = None
    if oi and oi.model in ['collection', 'entity', 'segment']:
        if repo.get('timestamp'):
            repo['ts'] = parser.parse(repo['timestamp'])
            if repo['ts'] >= EARLIEST:
                repositories.append(repo)

lines = [
    f"{repo['id']},{repo['timestamp']}\n"
    for repo in repositories
]
FILENAME = '/tmp/20231206-repos-to-fix.csv'
with open(FILENAME, 'w') as f:
    f.writelines(lines)
```


## Search selected repositories for bad NRIDs, fix them, and commit changes

Run the following on `kyuzo`:

``` bash
sudo su ddr
cd /opt/ddr-cmdln/
ipython
```

Run the following in the `ddr-cmdln` virtualenv:

``` python

import os, pathlib, shlex, subprocess
import click
from DDR import identifier

def make_old_nrids_new(path='20231206-noids-to-fix.csv'):
    """Load list of (old_ids,new_ids), format as dict
    """
    with pathlib.Path(path).open('r') as f:
        lines = [line.strip().split(',') for line in f.readlines()]
        return {
            old_nrid: new_nrid
            for old_nrid,new_nrid in lines
        }

def list_repos_to_fix(repos_to_fix_path):
    """List list of recently modified repositories from Cgit
    """
    with pathlib.Path(repos_to_fix_path).open('r') as f:
        lines = [line.strip() for line in f.readlines()]
        lines = [line.split(',') for line in lines]
        return [{'collectionid': cid, 'timestamp': ts} for cid,ts in lines]

def update_collections(
        repos_to_fix, basedir,
        noid_template, old_nrids_new,
        git_name, git_mail, agent, modify, commit
):
    """Update a list of collections
    """
    for repo in repos_to_fix:
        collectionid = repo['collectionid']
        update_collection(
            basedir, collectionid, noid_template, old_nrids_new,
            modify, git_name, git_mail, agent, commit,
        )

def update_collection(
        basedir, collectionid, noid_template, old_nrids_new,
        git_name, git_mail, agent, modify, commit
):
    """Update files in one single collection
    """
    collectionpath = basedir / collectionid
    if not collectionpath.exists():
        print(f"MISS {collectionpath}")
        return
    paths = find_bad_files(basedir, collectionid, noid_template)
    for path_abs in paths:
        modded = update_object(
            path_abs, old_nrids_new,
            modify, git_name, git_mail, agent, commit,
        )

def find_bad_files(basedir, collectionid, noid_template):
    """Find files in collection containing {noid_template}
    Search using ack because faster
    """
    cmd = f'ack -Q "{noid_template}"'
    collectionpath = basedir / collectionid
    os.chdir(collectionpath)
    print(f"     {os.getcwd()}")
    try:
        output = subprocess.check_output(
            shlex.split(cmd), text=True
        ).strip()
    except subprocess.CalledProcessError as err:
        #print(f"{err=}")
        return []
    lines = output.split('\n')
    rel_paths = sorted(list(set(
        [line.split(':')[0] for line in lines]
    )))
    return [collectionpath / relpath for relpath in rel_paths]

def update_object(
        path_abs, old_nrids_new,
        modify, git_name, git_mail, agent, commit,
):
    """Update object, replacing old NRIDs with new ones
    """
    #print(f"{path_abs=}")
    obj = identifier.Identifier(path=path_abs).object()
    if hasattr(obj, 'creators'):
        update_persons(obj, 'creators', old_nrids_new,)
    if hasattr(obj, 'persons'):
        update_persons(obj, 'persons', old_nrids_new,)
    if obj.is_modified():
        if modify:
            obj.save(git_name, git_mail, agent, commit=commit)

def update_persons(obj, fieldname, old_nrids_new):
    """Update creators or persons field with new NRID if necessary
    """
    for person in getattr(obj, fieldname):
        if person.get('nr_id'):
            old_nrid = person['nr_id']
            new_nrid = old_nrids_new.get(person['nr_id'])
            if new_nrid:
                person['nr_id'] = new_nrid
                print(f"     {obj.identifier.path_abs()} {old_nrid} > {new_nrid}")

noid_template = '88922/ddr'
old_nrids_new_path = '/tmp/20231206-noids-to-fix.csv'
repos_to_fix_path = '/tmp/20231206-repos-to-fix.csv'
basedir = pathlib.Path('/media/qnfs/kinkura/gold')

collectionid = 'ddr-densho-151'
git_name = 'Geoffrey Jost'
git_mail = 'geoffrey.jost@densho.us'
agent = 'ddr-cmdln 045-noidminter-fix.md'
modify = True
commit = False

old_nrids_new = make_old_nrids_new(old_nrids_new_path)
repos_to_fix = list_repos_to_fix(repos_to_fix_path)


# update ONE collection
update_collection(basedir, collectionid, noid_template, old_nrids_new, git_name, git_mail, agent, modify=False, commit=False)

# update ALL collections
update_collections(repos_to_fix, basedir, noid_template, old_nrids_new, git_name, git_mail, agent, modify=True, commit=False)

```


## Make changes to the `Person` records

The following code uses a combination of Python objects and direct SQL to update the `Person` records and all their associated `FarRecords`, `WraRecords`, `PersonFacilities`, `PersonLocations`, and `Revisions`.  There were no `IreiRecords` with the borked NRIDs.

Before running it, drop into SQLite and look at the Persons and their associated records:
``` sql
SELECT nr_id, preferred_name                        FROM names_person    WHERE     nr_id LIKE "88922/ddr%";
SELECT far_record_id,person_id,first_name,last_name FROM names_farrecord WHERE person_id LIKE "88922/ddr%";
SELECT wra_record_id,person_id,firstname,lastname   FROM names_wrarecord WHERE person_id LIKE "88922/ddr%";
SELECT id,person_id,location_id,facility_id         FROM names_personlocation WHERE person_id LIKE "88922/ddr%";
SELECT * FROM names_personfacility WHERE person_id LIKE "88922/ddr%";
SELECT * FROM names_ireirecord     WHERE person_id LIKE "88922/ddr%";
SELECT id,content_type_id,object_id,username,note FROM names_revision       WHERE object_id LIKE "88922/ddr%";
```

Run the following in the `namesdb-editor` virtualenv:
``` bash
sudo su ddr
cd /opt/namesdb-editor/
make shell
```
``` python
from django.db import connections, transaction
from names import models
def update_person(old_nrid, new_nrid):
    """Update the Person and all linked objects
    """
    # load existing Person
    oldperson = models.Person.objects.get(nr_id=old_nrid)
    # create new Person and save
    with transaction.atomic():
        newperson = models.Person(
            nr_id=new_nrid,
            family_name                   = oldperson.family_name,
            given_name                    = oldperson.given_name,
            given_name_alt                = oldperson.given_name_alt,
            other_names                   = oldperson.other_names,
            middle_name                   = oldperson.middle_name,
            prefix_name                   = oldperson.prefix_name,
            suffix_name                   = oldperson.suffix_name,
            jp_name                       = oldperson.jp_name,
            preferred_name                = oldperson.preferred_name,
            birth_date                    = oldperson.birth_date,
            birth_date_text               = oldperson.birth_date_text,
            birth_place                   = oldperson.birth_place,
            death_date                    = oldperson.death_date,
            death_date_text               = oldperson.death_date_text,
            wra_family_no                 = oldperson.wra_family_no,
            wra_individual_no             = oldperson.wra_individual_no,
            citizenship                   = oldperson.citizenship,
            alien_registration_no         = oldperson.alien_registration_no,
            gender                        = oldperson.gender,
            preexclusion_residence_city   = oldperson.preexclusion_residence_city,
            preexclusion_residence_state  = oldperson.preexclusion_residence_state,
            postexclusion_residence_city  = oldperson.postexclusion_residence_city,
            postexclusion_residence_state = oldperson.postexclusion_residence_state,
            exclusion_order_title         = oldperson.exclusion_order_title,
            exclusion_order_id            = oldperson.exclusion_order_id,
            timestamp                     = oldperson.timestamp,
        )
        newperson.save(note='DELETE THIS REVISION')

        # Delete auto-generated Revision for newperson
        with connections["names"].cursor() as cursor:
            cursor.execute(
                "DELETE FROM names_revision WHERE object_id=%s", [new_nrid]
            )
        # Re-assign Revisions from old Person to new Person
        with connections["names"].cursor() as cursor:
            cursor.execute(
                "UPDATE names_revision SET object_id=%s WHERE object_id=%s",
                [new_nrid, old_nrid]
            )
        # Add Revision noting the change of NRID
        r = models.Revision(
            content_object=newperson,
            username='gjost',
            note='Update Persons created with bad noidminter_template',
            diff=models.make_diff(oldperson, newperson)
        )
        r.save()

        # load FarRecord(s)      and point to new Person
        # SELECT * FROM names_farrecord WHERE person_id LIKE "88922/ddr%";
        for farrecord in models.FarRecord.objects.filter(person_id=old_nrid):
            farrecord.person = newperson
            farrecord.save()
        # load WraRecord(s)      and point to new Person
        # SELECT * FROM names_wrarecord WHERE person_id LIKE "88922/ddr%";
        for wrarecord in models.WraRecord.objects.filter(person_id=old_nrid):
            wrarecord.person = newperson
            wrarecord.save()
        # load PersonLocation(s) and point to new Person
        # SELECT * FROM names_personlocation WHERE person_id LIKE "88922/ddr%";
        for personlocation in models.PersonLocation.objects.filter(person_id=old_nrid):
            personlocation.person = newperson
            personlocation.save()
        # load PersonFacility(s) and point to new Person
        # SELECT * FROM names_personfacility WHERE person_id LIKE "88922/ddr%";
        for personfacility in models.PersonFacility.objects.filter(person_id=old_nrid):
            personfacility.person = newperson
            personfacility.save()
        # NO IreiRecords WITH BAD NRID

    # have to add Facilities this way
    if oldperson.facility.all():
        for f in oldperson.facility.all():
            newperson.facility_set.add(f)

    # delete old Person
    oldperson.delete()

    return True

import pathlib
def make_old_nrids_new(
        path='20231206-noids-to-fix.csv',
        path_names='20231206-bad-noids-annotated.csv',
):
    """Load list of (old_ids,new_ids), format as dict
    """
    with pathlib.Path(path_names).open('r') as f:
        lines = [line.strip().split(',') for line in f.readlines()]
        old_nrids_names = {
            old_nrid: name.replace('"','').strip()
            for old_nrid,name in lines
        }
    with pathlib.Path(path).open('r') as f:
        lines = [line.strip().split(',') for line in f.readlines()]
        return [
            {'old_nrid': old_nrid, 'new_nrid': new_nrid, 'name': old_nrids_names.get(old_nrid,'')}
            for old_nrid,new_nrid in lines
        ]

# Load list of old/new NRIDs
old_nrids_new = make_old_nrids_new('/tmp/20231206-noids-to-fix.csv', '/tmp/20231206-bad-noids-annotated.csv')
# Update each of the Persons and their associated records
for n,p in enumerate(old_nrids_new):
    print(f"{n}/{len(old_nrids_new)} {p['old_nrid']} > {p['new_nrid']} - {p['name']}")
    update_person(p['old_nrid'], p['new_nrid'])
```

After running, confirm that none of the old `88922/ddr*` records remain.  There may be a single `names_revision` record left, but this seems to be left over from a deleted `Person` record.
``` sql
SELECT COUNT(*) FROM names_person         WHERE nr_id     LIKE "88922/ddr%";  -- 184 before updating
SELECT COUNT(*) FROM names_farrecord      WHERE person_id LIKE "88922/ddr%";  -- 269
SELECT COUNT(*) FROM names_wrarecord      WHERE person_id LIKE "88922/ddr%";  -- 156
SELECT COUNT(*) FROM names_personlocation WHERE person_id LIKE "88922/ddr%";  -- 162
SELECT COUNT(*) FROM names_personfacility WHERE person_id LIKE "88922/ddr%";  -- 1
SELECT COUNT(*) FROM names_ireirecord     WHERE person_id LIKE "88922/ddr%";  -- 0
SELECT COUNT(*) FROM names_revision       WHERE object_id LIKE "88922/ddr%";  -- 202
```
