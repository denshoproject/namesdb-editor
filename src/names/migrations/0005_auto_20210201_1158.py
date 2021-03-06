# Generated by Django 3.1.5 on 2021-02-01 19:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('names', '0004_auto_20210129_1153'),
    ]

    operations = [
        migrations.RenameField(
            model_name='revision',
            old_name='dataset',
            new_name='model',
        ),
        migrations.RemoveField(
            model_name='farrecord',
            name='alienregistration',
        ),
        migrations.RemoveField(
            model_name='farrecord',
            name='altfamilyid',
        ),
        migrations.RemoveField(
            model_name='farrecord',
            name='altindividualid',
        ),
        migrations.RemoveField(
            model_name='farrecord',
            name='birthyear',
        ),
        migrations.RemoveField(
            model_name='farrecord',
            name='camp',
        ),
        migrations.RemoveField(
            model_name='farrecord',
            name='campaddress',
        ),
        migrations.RemoveField(
            model_name='farrecord',
            name='dataset',
        ),
        migrations.RemoveField(
            model_name='farrecord',
            name='ddrreference',
        ),
        migrations.RemoveField(
            model_name='farrecord',
            name='departuredate',
        ),
        migrations.RemoveField(
            model_name='farrecord',
            name='departuretype',
        ),
        migrations.RemoveField(
            model_name='farrecord',
            name='destinationcity',
        ),
        migrations.RemoveField(
            model_name='farrecord',
            name='destinationstate',
        ),
        migrations.RemoveField(
            model_name='farrecord',
            name='entrydate',
        ),
        migrations.RemoveField(
            model_name='farrecord',
            name='entrytype',
        ),
        migrations.RemoveField(
            model_name='farrecord',
            name='errors',
        ),
        migrations.RemoveField(
            model_name='farrecord',
            name='familyno',
        ),
        migrations.RemoveField(
            model_name='farrecord',
            name='farlineid',
        ),
        migrations.RemoveField(
            model_name='farrecord',
            name='firstname',
        ),
        migrations.RemoveField(
            model_name='farrecord',
            name='gender',
        ),
        migrations.RemoveField(
            model_name='farrecord',
            name='individualno',
        ),
        migrations.RemoveField(
            model_name='farrecord',
            name='lastname',
        ),
        migrations.RemoveField(
            model_name='farrecord',
            name='maritalstatus',
        ),
        migrations.RemoveField(
            model_name='farrecord',
            name='notes',
        ),
        migrations.RemoveField(
            model_name='farrecord',
            name='originalcity',
        ),
        migrations.RemoveField(
            model_name='farrecord',
            name='originalstate',
        ),
        migrations.RemoveField(
            model_name='farrecord',
            name='othernames',
        ),
        migrations.RemoveField(
            model_name='farrecord',
            name='pseudoid',
        ),
        migrations.RemoveField(
            model_name='revision',
            name='pseudoid',
        ),
        migrations.RemoveField(
            model_name='wrarecord',
            name='altfamilyid',
        ),
        migrations.RemoveField(
            model_name='wrarecord',
            name='altindividualid',
        ),
        migrations.RemoveField(
            model_name='wrarecord',
            name='camp',
        ),
        migrations.RemoveField(
            model_name='wrarecord',
            name='dataset',
        ),
        migrations.RemoveField(
            model_name='wrarecord',
            name='ddrreference',
        ),
        migrations.RemoveField(
            model_name='wrarecord',
            name='errors',
        ),
        migrations.RemoveField(
            model_name='wrarecord',
            name='filenumber',
        ),
        migrations.RemoveField(
            model_name='wrarecord',
            name='maritalstatus',
        ),
        migrations.RemoveField(
            model_name='wrarecord',
            name='notimesinjapan',
        ),
        migrations.RemoveField(
            model_name='wrarecord',
            name='occuppotn1',
        ),
        migrations.RemoveField(
            model_name='wrarecord',
            name='occuppotn2',
        ),
        migrations.RemoveField(
            model_name='wrarecord',
            name='pseudoid',
        ),
        migrations.AddField(
            model_name='farrecord',
            name='alien_registration',
            field=models.CharField(blank=1, help_text='INS-assigned Alien Registration number', max_length=255, verbose_name='Alien Registration Number'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='camp_address_barracks',
            field=models.CharField(blank=1, help_text='Barrack identifier of camp address', max_length=255, verbose_name='Camp Address Barrack'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='camp_address_block',
            field=models.CharField(blank=1, help_text='Block identifier of camp address', max_length=255, verbose_name='Camp Address Block'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='camp_address_original',
            field=models.CharField(blank=1, help_text='Physical address in camp in the form, "Block-Barrack-Room"', max_length=255, verbose_name='Camp Address'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='camp_address_room',
            field=models.CharField(blank=1, help_text='Room identifier of camp address', max_length=255, verbose_name='Camp Address Room'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='date_of_birth',
            field=models.CharField(blank=1, help_text='Full birth date', max_length=255, verbose_name='Birthdate'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='date_of_original_entry',
            field=models.CharField(blank=1, help_text='Date of arrival at facility', max_length=255, verbose_name='Entry Date'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='departure_category',
            field=models.CharField(blank=1, help_text='Category of departure type', max_length=255, verbose_name='Departure Category'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='departure_date',
            field=models.CharField(blank=1, help_text='Date of departure from facility', max_length=255, verbose_name='Departure Date'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='departure_facility',
            field=models.CharField(blank=1, help_text='Departure facility, if applicable', max_length=255, verbose_name='Departure Facility'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='departure_state',
            field=models.CharField(blank=1, help_text='Destination after departure; state-only', max_length=255, verbose_name='Departure Destination'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='departure_type',
            field=models.CharField(blank=1, help_text='Normalized type of final departure', max_length=255, verbose_name='Departure Type'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='departure_type_code',
            field=models.CharField(blank=1, help_text='Coded type of leave or reason for departure from facility', max_length=255, verbose_name='Departure Type (Coded)'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='entry_category',
            field=models.CharField(blank=1, help_text='Category of entry type; assigned by Densho', max_length=255, verbose_name='Entry Category'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='entry_facility',
            field=models.CharField(blank=1, help_text='Last facility prior to entry', max_length=255, verbose_name='Entry Facility'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='entry_type',
            field=models.CharField(blank=1, help_text='Normalized type of original entry', max_length=255, verbose_name='Entry Type'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='entry_type_code',
            field=models.CharField(blank=1, help_text='Coded type of original admission and assignment to facility', max_length=255, verbose_name='Entry Type (Coded)'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='facility',
            field=models.CharField(default='unspecified', help_text='Identifier of WRA facility', max_length=255, verbose_name='Facility'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='farrecord',
            name='family_number',
            field=models.CharField(blank=1, help_text='WRA-assigned family number', max_length=255, verbose_name='WRA Family Number'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='far_id',
            field=models.CharField(default='unspecified', help_text="Derived from FAR ledger id + line id ('original_order')", max_length=255, primary_key=1, serialize=False, verbose_name='FAR Record ID'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='farrecord',
            name='far_line_id',
            field=models.CharField(blank=1, help_text='Line number in FAR ledger, recorded in original ledger', max_length=255, verbose_name='FAR Line Number'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='first_name',
            field=models.CharField(blank=1, help_text='First name corrected by transcription team', max_length=255, verbose_name='First Name'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='last_name',
            field=models.CharField(blank=1, help_text='Last name corrected by transcription team', max_length=255, verbose_name='Last Name'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='marital_status',
            field=models.CharField(blank=1, help_text='Marital status', max_length=255, verbose_name='Marital Status'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='original_notes',
            field=models.CharField(blank=1, help_text='Notes from original statistics section recorder, often a reference to another name in the roster', max_length=255, verbose_name='Original Notes'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='original_order',
            field=models.CharField(blank=1, help_text='Absolute line number in physical FAR ledger', max_length=255, verbose_name='Original Order'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='other_names',
            field=models.CharField(blank=1, help_text='Alternate first names', max_length=255, verbose_name='Other Names'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='pre_evacuation_address',
            field=models.CharField(blank=1, help_text='Address at time of removal; city and state', max_length=255, verbose_name='Pre-exclusion Address'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='pre_evacuation_state',
            field=models.CharField(blank=1, help_text='Address at time of removal, state-only', max_length=255, verbose_name='Pre-exclusion State'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='reference',
            field=models.CharField(blank=1, help_text='Pointer to another row in the roster; page number in source pdf and the original order in the consolidated roster for the camp', max_length=255, verbose_name='Internal FAR Reference'),
        ),
        migrations.AddField(
            model_name='farrecord',
            name='sex',
            field=models.CharField(default='unspecified', help_text='Gender identifier', max_length=255, verbose_name='Gender'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='farrecord',
            name='year_of_birth',
            field=models.CharField(blank=1, help_text='Year of birth', max_length=255, verbose_name='Year of Birth'),
        ),
        migrations.AddField(
            model_name='revision',
            name='record_id',
            field=models.CharField(default='unspecified', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='wrarecord',
            name='facility',
            field=models.CharField(default='unspecified', help_text='Facility identifier', max_length=255, verbose_name='Facility identifier'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='wrarecord',
            name='martitalstatus',
            field=models.CharField(blank=1, help_text='Marital status', max_length=255, verbose_name='Marital status'),
        ),
        migrations.AddField(
            model_name='wrarecord',
            name='middleinitial',
            field=models.CharField(blank=1, help_text='Middle initial', max_length=255, verbose_name='Middle initial'),
        ),
        migrations.AddField(
            model_name='wrarecord',
            name='occupotn1',
            field=models.CharField(blank=1, help_text='Primary potential occupation', max_length=255, verbose_name='Primary potential occupation'),
        ),
        migrations.AddField(
            model_name='wrarecord',
            name='occupotn2',
            field=models.CharField(blank=1, help_text='Secondary potential occupation', max_length=255, verbose_name='Secondary potential occupation'),
        ),
        migrations.AddField(
            model_name='wrarecord',
            name='wra_filenumber',
            field=models.CharField(default='unspecified', help_text='WRA-assigned 6-digit filenumber identifier', max_length=255, verbose_name='WRA Filenumber'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='wrarecord',
            name='wra_record_id',
            field=models.IntegerField(default=0, help_text='Unique identifier; absolute row in original RG210.JAPAN.WRA26 datafile', primary_key=1, serialize=False, verbose_name='WRA Form 26 ID'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='farrecord',
            name='citizenship',
            field=models.CharField(help_text='Citizenship status', max_length=255, verbose_name='Citizenship Status'),
        ),
        migrations.AlterField(
            model_name='farrecord',
            name='timestamp',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Last Updated'),
        ),
        migrations.AlterField(
            model_name='revision',
            name='username',
            field=models.CharField(max_length=30),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='ageinjapan',
            field=models.CharField(blank=1, help_text='Age while visiting or living in Japan', max_length=255, verbose_name='Oldest age visiting or living in Japan'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='assemblycenter',
            field=models.CharField(help_text='Assembly center prior to camp', max_length=255, verbose_name='Assembly center prior to camp'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='birthcountry',
            field=models.CharField(help_text='Birth countries of father and mother; coded by WRA', max_length=255, verbose_name='Birth countries of father and mother (coded)'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='birthplace',
            field=models.CharField(blank=1, help_text='Birthplace', max_length=255, verbose_name='Birthplace'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='birthyear',
            field=models.CharField(blank=1, help_text='Year of birth', max_length=255, verbose_name='Year of birth'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='citizenshipstatus',
            field=models.CharField(blank=1, help_text='Citizenship status', max_length=255, verbose_name='Citizenship status'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='ethnicity',
            field=models.CharField(blank=1, help_text='Ethnicity', max_length=255, verbose_name='Ethnicity'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='familyno',
            field=models.CharField(blank=1, help_text='WRA-assigned family identifier', max_length=255, verbose_name='WRA-assigned family identifier'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='fatheroccupabr',
            field=models.CharField(blank=1, help_text="Father's occupation pre-emigration; coded by WRA", max_length=255, verbose_name="Father's occupation pre-emigration (coded)"),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='fatheroccupus',
            field=models.CharField(blank=1, help_text="Father's occupation in the US; coded by WRA", max_length=255, verbose_name="Father's occupation in the US (coded)"),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='firstname',
            field=models.CharField(blank=1, help_text='First name, truncated to 8 chars', max_length=255, verbose_name='First name, truncated to 8 chars'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='gender',
            field=models.CharField(blank=1, help_text='Gender', max_length=255, verbose_name='Gender'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='gradejapan',
            field=models.CharField(blank=1, help_text='Highest grade of schooling attained in Japan; coded by WRA', max_length=255, verbose_name='Highest grade of schooling attained in Japan (coded)'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='highestgrade',
            field=models.CharField(blank=1, help_text='Highest degree achieved', max_length=255, verbose_name='Highest degree achieved'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='individualno',
            field=models.CharField(blank=1, help_text='Family identifier + alpha char by birthdate', max_length=255, verbose_name='Family identifier + alpha char by birthdate'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='language',
            field=models.CharField(blank=1, help_text='Languages spoken', max_length=255, verbose_name='Languages spoken'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='lastname',
            field=models.CharField(blank=1, help_text='Last name, truncated to 10 chars', max_length=255, verbose_name='Last name, truncated to 10 chars'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='militaryservice',
            field=models.CharField(blank=1, help_text='Military service, public assistance status and major disabilities', max_length=255, verbose_name='Military service, pensions and disabilities'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='notes',
            field=models.CharField(blank=1, help_text='Notes added by Densho during processing', max_length=255, verbose_name='Notes added by Densho during processing'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='occupqual1',
            field=models.CharField(blank=1, help_text='Primary qualified occupation', max_length=255, verbose_name='Primary qualified occupation'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='occupqual2',
            field=models.CharField(blank=1, help_text='Secondary qualified occupation', max_length=255, verbose_name='Secondary qualified occupation'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='occupqual3',
            field=models.CharField(blank=1, help_text='Tertiary qualified occupation', max_length=255, verbose_name='Tertiary qualified occupation'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='originaladdress',
            field=models.CharField(blank=1, help_text='County/city + state of pre-exclusion address; coded by WRA', max_length=255, verbose_name='County/city + state of pre-exclusion address (coded)'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='originalstate',
            field=models.CharField(blank=1, help_text='State of residence immediately prior to census', max_length=255, verbose_name='State of residence immediately prior to census'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='religion',
            field=models.CharField(blank=1, help_text='Religion', max_length=255, verbose_name='Religion'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='schooldegree',
            field=models.CharField(blank=1, help_text='Highest educational degree attained; coded by WRA', max_length=255, verbose_name='Highest educational degree attained (coded)'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='timeinjapan',
            field=models.CharField(blank=1, help_text='Description of time in Japan', max_length=255, verbose_name='Time in Japan'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='timestamp',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Last Updated'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='yearofusarrival',
            field=models.CharField(blank=1, help_text='Year of immigration to US, if applicable', max_length=255, verbose_name='Year of immigration to US, if applicable'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='yearsschooljapan',
            field=models.CharField(blank=1, help_text='Years of school attended in Japan', max_length=255, verbose_name='Years of school attended in Japan'),
        ),
    ]
