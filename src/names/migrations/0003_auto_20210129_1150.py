# Generated by Django 3.1.5 on 2021-01-29 19:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('names', '0002_auto_20210119_1217'),
    ]

    operations = [
        migrations.AlterField(
            model_name='farrecord',
            name='alienregistration',
            field=models.CharField(blank=1, max_length=30, verbose_name='Alien Registration'),
        ),
        migrations.AlterField(
            model_name='farrecord',
            name='altfamilyid',
            field=models.CharField(blank=1, max_length=30, verbose_name='Alt Family ID'),
        ),
        migrations.AlterField(
            model_name='farrecord',
            name='altindividualid',
            field=models.CharField(blank=1, max_length=30, verbose_name='Alt Indiv ID'),
        ),
        migrations.AlterField(
            model_name='farrecord',
            name='birthyear',
            field=models.CharField(blank=1, max_length=30, verbose_name='Birth Year'),
        ),
        migrations.AlterField(
            model_name='farrecord',
            name='camp',
            field=models.CharField(blank=1, max_length=30),
        ),
        migrations.AlterField(
            model_name='farrecord',
            name='campaddress',
            field=models.CharField(blank=1, max_length=30, verbose_name='Camp Address'),
        ),
        migrations.AlterField(
            model_name='farrecord',
            name='citizenship',
            field=models.CharField(blank=1, max_length=30),
        ),
        migrations.AlterField(
            model_name='farrecord',
            name='ddrreference',
            field=models.CharField(blank=1, max_length=30, verbose_name='DDR Reference'),
        ),
        migrations.AlterField(
            model_name='farrecord',
            name='departuredate',
            field=models.CharField(blank=1, max_length=30, verbose_name='Departure Date'),
        ),
        migrations.AlterField(
            model_name='farrecord',
            name='departuretype',
            field=models.CharField(blank=1, max_length=30, verbose_name='Departure Type'),
        ),
        migrations.AlterField(
            model_name='farrecord',
            name='destinationcity',
            field=models.CharField(blank=1, max_length=30, verbose_name='Destination City'),
        ),
        migrations.AlterField(
            model_name='farrecord',
            name='destinationstate',
            field=models.CharField(blank=1, max_length=30, verbose_name='Destination State'),
        ),
        migrations.AlterField(
            model_name='farrecord',
            name='entrydate',
            field=models.CharField(blank=1, max_length=30, verbose_name='Entry Date'),
        ),
        migrations.AlterField(
            model_name='farrecord',
            name='entrytype',
            field=models.CharField(blank=1, max_length=30, verbose_name='Entry Type'),
        ),
        migrations.AlterField(
            model_name='farrecord',
            name='errors',
            field=models.TextField(blank=1),
        ),
        migrations.AlterField(
            model_name='farrecord',
            name='familyno',
            field=models.CharField(blank=1, max_length=30, verbose_name='Family Number'),
        ),
        migrations.AlterField(
            model_name='farrecord',
            name='farlineid',
            field=models.CharField(blank=1, max_length=30, verbose_name='FAR Line ID'),
        ),
        migrations.AlterField(
            model_name='farrecord',
            name='firstname',
            field=models.CharField(blank=1, max_length=30, verbose_name='First Name'),
        ),
        migrations.AlterField(
            model_name='farrecord',
            name='gender',
            field=models.CharField(blank=1, max_length=30),
        ),
        migrations.AlterField(
            model_name='farrecord',
            name='individualno',
            field=models.CharField(blank=1, max_length=30, verbose_name='Individual Number'),
        ),
        migrations.AlterField(
            model_name='farrecord',
            name='lastname',
            field=models.CharField(blank=1, max_length=30, verbose_name='Last Name'),
        ),
        migrations.AlterField(
            model_name='farrecord',
            name='maritalstatus',
            field=models.CharField(blank=1, max_length=30, verbose_name='Marital Status'),
        ),
        migrations.AlterField(
            model_name='farrecord',
            name='notes',
            field=models.CharField(blank=1, max_length=30),
        ),
        migrations.AlterField(
            model_name='farrecord',
            name='originalcity',
            field=models.CharField(blank=1, max_length=30, verbose_name='Original City'),
        ),
        migrations.AlterField(
            model_name='farrecord',
            name='originalstate',
            field=models.CharField(blank=1, max_length=30, verbose_name='Original State'),
        ),
        migrations.AlterField(
            model_name='farrecord',
            name='othernames',
            field=models.CharField(blank=1, max_length=30, verbose_name='Other Names'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='ageinjapan',
            field=models.CharField(blank=1, max_length=30, verbose_name='Age In Japan'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='altfamilyid',
            field=models.CharField(blank=1, max_length=30, verbose_name='Alt Family ID'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='altindividualid',
            field=models.CharField(blank=1, max_length=30, verbose_name='Alt Indiv ID'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='assemblycenter',
            field=models.CharField(blank=1, max_length=30, verbose_name='Assembly Center'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='birthcountry',
            field=models.CharField(blank=1, max_length=30, verbose_name='Birth Country'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='birthplace',
            field=models.CharField(blank=1, max_length=30),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='birthyear',
            field=models.CharField(blank=1, max_length=30, verbose_name='Birth Year'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='camp',
            field=models.CharField(blank=1, max_length=30),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='citizenshipstatus',
            field=models.CharField(blank=1, max_length=30, verbose_name='Citizenship Status'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='ddrreference',
            field=models.CharField(blank=1, max_length=30, verbose_name='DDR Reference'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='errors',
            field=models.TextField(blank=1),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='ethnicity',
            field=models.CharField(blank=1, max_length=30),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='familyno',
            field=models.CharField(blank=1, max_length=30, verbose_name='Family Number'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='fatheroccupabr',
            field=models.CharField(blank=1, max_length=30, verbose_name='Father Occup abr'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='fatheroccupus',
            field=models.CharField(blank=1, max_length=30, verbose_name='Father Occup US'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='filenumber',
            field=models.CharField(blank=1, max_length=30, verbose_name='File Number'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='firstname',
            field=models.CharField(blank=1, max_length=30, verbose_name='First Name'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='gender',
            field=models.CharField(blank=1, max_length=30),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='gradejapan',
            field=models.CharField(blank=1, max_length=30, verbose_name='Grade Japan'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='highestgrade',
            field=models.CharField(blank=1, max_length=30, verbose_name='Highest Grade'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='individualno',
            field=models.CharField(blank=1, max_length=30, verbose_name='Individual Number'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='language',
            field=models.CharField(blank=1, max_length=30),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='lastname',
            field=models.CharField(blank=1, max_length=30, verbose_name='Last Name'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='maritalstatus',
            field=models.CharField(blank=1, max_length=30, verbose_name='Marital Status'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='militaryservice',
            field=models.CharField(blank=1, max_length=30, verbose_name='Military Service'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='notes',
            field=models.CharField(blank=1, max_length=30),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='notimesinjapan',
            field=models.CharField(blank=1, max_length=30, verbose_name='No times in japan'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='occuppotn1',
            field=models.CharField(blank=1, max_length=30),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='occuppotn2',
            field=models.CharField(blank=1, max_length=30),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='occupqual1',
            field=models.CharField(blank=1, max_length=30),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='occupqual2',
            field=models.CharField(blank=1, max_length=30),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='occupqual3',
            field=models.CharField(blank=1, max_length=30),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='originaladdress',
            field=models.CharField(blank=1, max_length=30, verbose_name='Original Address'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='originalstate',
            field=models.CharField(blank=1, max_length=30, verbose_name='Original State'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='religion',
            field=models.CharField(blank=1, max_length=30),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='schooldegree',
            field=models.CharField(blank=1, max_length=30, verbose_name='School Degree'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='timeinjapan',
            field=models.CharField(blank=1, max_length=30, verbose_name='Time in Japan'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='yearofusarrival',
            field=models.CharField(blank=1, max_length=30, verbose_name='Year of US Arrival'),
        ),
        migrations.AlterField(
            model_name='wrarecord',
            name='yearsschooljapan',
            field=models.CharField(blank=1, max_length=30, verbose_name='Years School Japan'),
        ),
    ]
