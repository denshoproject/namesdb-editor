# namesdb-editor - Names Registry Editor


## But first, the original NamesDB Editor

If you need to update the *original* [Names Registry](https://ddr.densho.org/names/) you are probably looking for [denshoproject/namesdb/](https://github.com/denshoproject/namesdb/).


## Installation

Clone the repo and install:
```
$ git clone https://github.com/denshoproject/namesdb-editor.git
$ sudo mv namesdb-editor /opt/
$ cd /opt/namesdb-editor/
$ sudo make install
```

Edit `etc/ddr/namesdbeditor-local.cfg`.
```
[debug]
debug=1

[security]
allowed_hosts=namesdb-editor.densho.org, namesdb-editor.local, 192.168.1.101
```

Become the `ddr` user and set up the database:
```
$ sudo su ddr
$ source venv/names/bin/activate
$ python src/manage.py migrate
$ python src/manage.py createsuperuser
```

## Running the web application

```
$ sudo su ddr
$ source venv/names/bin/activate
$ python src/manage.py runserver 0.0.0.0:8000
```


## Importing FAR/WRA data

Use the Django shell:

```
$ python src/manage.py shell

>>> from names import models

>>> # username will be written to Revision metadata for each record
>>> # num_records limits the number of records imported (useful for testing)
>>> models.load_csv(models.WraRecord, '/opt/namesdb-data/0.2/0_2-wra-master.csv', username='gjost', num_records=10)

>>> models.load_csv(models.FarRecord, '/opt/namesdb-data/0.2/0_2-far-master.csv', username='gjost', num_records=10)

>>> models.load_facilities('/opt/namesdb-data/0.2/0_2-far-master.csv')
```
