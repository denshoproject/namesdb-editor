PROJECT=namesdb-editor
USER=ddr
SHELL = /bin/bash

SRC_REPO_EDITOR=https://github.com/denshoproject/namesdb-editor
SRC_REPO_PUBLIC=https://github.com/denshoproject/namesdb-public.git
SRC_REPO_IREIZO=https://github.com/denshoproject/ireizo-public.git

INSTALL_BASE=/opt
INSTALLDIR=$(INSTALL_BASE)/namesdb-editor
INSTALL_PUBLIC=$(INSTALL_BASE)/namesdb-public
INSTALL_IREIZO=$(INSTALL_BASE)/ireizo-public
APPDIR=$(INSTALLDIR)/src
REQUIREMENTS=$(INSTALLDIR)/requirements.txt
PIP_CACHE_DIR=$(INSTALL_BASE)/pip-cache

CWD := $(shell pwd)
INSTALL_STATIC=$(INSTALLDIR)/static

VIRTUALENV=$(INSTALLDIR)/venv/names

CONF_BASE=/etc/ddr
CONF_PRODUCTION=$(CONF_BASE)/namesdbeditor.cfg
CONF_LOCAL=$(CONF_BASE)/namesdbeditor-local.cfg
CONF_SECRET=$(CONF_BASE)/namesdbeditor-secret-key.txt

SQLITE_BASE=$(INSTALLDIR)/db
LOG_BASE=/var/log/ddr

MEDIA_BASE=/var/www/namesdbeditor
MEDIA_ROOT=$(MEDIA_BASE)/media
STATIC_ROOT=$(MEDIA_BASE)/static

LIBMARIADB_PKG=libmariadb-dev
ifeq ($(DEBIAN_CODENAME), buster)
	LIBMARIADB_PKG=libmariadbclient-dev
endif

RUNSERVER_PORT=8004
SUPERVISOR_GUNICORN_CONF=/etc/supervisor/conf.d/namesdbeditor.conf
NGINX_CONF=/etc/nginx/sites-available/namesdbeditor.conf
NGINX_CONF_LINK=/etc/nginx/sites-enabled/namesdbeditor.conf

# Release name e.g. jessie
DEBIAN_CODENAME := $(shell lsb_release -sc)
# Release numbers e.g. 8.10
DEBIAN_RELEASE := $(shell lsb_release -sr)
# Sortable major version tag e.g. deb8
DEBIAN_RELEASE_TAG = deb$(shell lsb_release -sr | cut -c1)

PYTHON_VERSION=
ifeq ($(DEBIAN_CODENAME), bullseye)
	PYTHON_VERSION=3.9
endif
ifeq ($(DEBIAN_CODENAME), bookworm)
	PYTHON_VERSION=3.11.2
endif
ifeq ($(DEBIAN_CODENAME), trixie)
	PYTHON_VERSION=3.11.6
endif


.PHONY: help

help:
	@echo "namesdb-editor Install Helper"
	@echo ""
	@echo "install - Does a complete install. Idempotent, so run as many times as you like."
	@echo "          IMPORTANT: Run 'adduser encyc' first to install encycddr user and group."
	@echo ""
	@echo "syncdb  - Initialize or update Django app's database tables."
	@echo ""
	@echo "uninstall - Deletes 'compiled' Python files. Leaves build dirs and configs."
	@echo "clean   - Deletes files created by building the program. Leaves configs."
	@echo ""


install: install-prep get-app install-app install-configs install-static

update: update-app

uninstall: uninstall-app

clean: clean-app


install-prep: apt-update install-core git-config install-misc-tools


apt-update:
	@echo ""
	@echo "Package update ---------------------------------------------------------"
	apt-get --assume-yes update

apt-upgrade:
	@echo ""
	@echo "Package upgrade --------------------------------------------------------"
	apt-get --assume-yes upgrade

install-core:
	apt-get --assume-yes install bzip2 curl gdebi-core git-core logrotate ntp p7zip-full wget

git-config:
	git config --global alias.st status
	git config --global alias.co checkout
	git config --global alias.br branch
	git config --global alias.ci commit

install-misc-tools:
	@echo ""
	@echo "Installing miscellaneous tools -----------------------------------------"
	apt-get --assume-yes install ack-grep byobu elinks htop iftop iotop mg multitail


install-daemons: install-db install-nginx install-redis install-supervisor

remove-daemons: remove-db remove-nginx remove-redis remove-supervisor

install-nginx:
	@echo ""
	@echo "Nginx ------------------------------------------------------------------"
	apt-get --assume-yes install nginx

remove-nginx:
	apt-get --assume-yes remove nginx

install-db:
	@echo ""
	@echo "SQLite3 ----------------------------------------------------------------"
	apt-get --assume-yes install sqlite3

remove-mariadb:
	apt-get --assume-yes remove sqlite3

install-redis:
	@echo ""
	@echo "Redis ------------------------------------------------------------------"
	apt-get --assume-yes install redis-server

remove-redis:
	apt-get --assume-yes remove redis-server

install-supervisor:
	@echo ""
	@echo "Supervisor -------------------------------------------------------------"
	apt-get --assume-yes install supervisor

remove-supervisor:
	apt-get --assume-yes remove supervisor


install-virtualenv:
	@echo ""
	@echo "install-virtualenv -----------------------------------------------------"
	apt-get --assume-yes install python3-pip python3-venv
	python3 -m venv $(VIRTUALENV)
	source $(VIRTUALENV)/bin/activate; \
	pip3 install -U --cache-dir=$(PIP_CACHE_DIR) uv


get-app: get-namesdb-editor get-namesdb-public get-ireizo-public

install-app: install-namesdb-editor install-namesdb-public install-ireizo-public

uninstall-app: uninstall-namesdb-editor uninstall-namesdb-public uninstall-ireizo-public

clean-app: clean-namesdb-editor clean-namesdb-public clean-ireizo-public


get-namesdb-editor:
	@echo ""
	@echo "get-namesdb-editor -----------------------------------------------------"
	git pull

install-namesdb-editor: install-virtualenv git-safe-dir
	@echo ""
	@echo "install namesdb-editor -------------------------------------------------"
	apt-get --assume-yes install imagemagick libjpeg-dev $(LIBMARIADB_PKG) libxml2 libxslt1.1 libxslt1-dev
	source $(VIRTUALENV)/bin/activate; \
	uv pip install -U -r $(INSTALLDIR)/requirements.txt
	source $(VIRTUALENV)/bin/activate; \
	cd $(APPDIR)/ && python setup.py install
# logs dir
	-mkdir $(LOG_BASE)
	chown -R ddr.root $(LOG_BASE)
	chmod -R 755 $(LOG_BASE)
# sqlite db dir
	-mkdir $(SQLITE_BASE)
	chown -R ddr.ddr $(SQLITE_BASE)
	chmod -R 775 $(SQLITE_BASE)
# static dir
	-mkdir -p $(STATIC_ROOT)
	chown -R ddr.root $(STATIC_ROOT)
	chmod -R 755 $(STATIC_ROOT)
# media dir
	-mkdir -p $(MEDIA_ROOT)
	chown -R ddr.root $(MEDIA_BASE)
	chmod -R 755 $(MEDIA_BASE)

git-safe-dir:
	@echo ""
	@echo "git-safe-dir -----------------------------------------------------------"
	sudo -u ddr git config --global --add safe.directory $(INSTALLDIR)
	sudo -u ddr git config --global --add safe.directory $(INSTALL_PUBLIC)
	sudo -u ddr git config --global --add safe.directory $(INSTALL_IREIZO)

setup-names-editor:
	-rm $(APPDIR)/namesdb_public/namesdb_public
	source $(VIRTUALENV)/bin/activate; \
	cd $(APPDIR)/ && python setup.py install

shell:
	source $(VIRTUALENV)/bin/activate; \
	python src/manage.py shell

runserver:
	source $(VIRTUALENV)/bin/activate; \
	python src/manage.py runserver 0.0.0.0:$(RUNSERVER_PORT)

uninstall-namesdb-editor:
	cd $(APPDIR)
	source $(VIRTUALENV)/bin/activate; \
	-pip uninstall -r $(INSTALLDIR)/requirements.txt

clean-namesdb-editor:
	-rm -Rf $(INSTALLDIR)/venv/
	-rm -Rf $(APPDIR)/editor/__pycache__
	-rm -Rf $(APPDIR)/names/__pycache__
	-rm -Rf $(APPDIR)/build
	-rm -Rf $(APPDIR)/*.egg-info
	-rm -Rf $(APPDIR)/dist


get-namesdb-public:
	@echo ""
	@echo "get-names-public -------------------------------------------------------"
	git status | grep "On branch"
	if test -d $(INSTALL_PUBLIC); \
	then cd $(INSTALL_PUBLIC) && git pull; \
	else cd $(INSTALL_BASE) && git clone $(SRC_REPO_PUBLIC); \
	fi

install-namesdb-public: install-virtualenv
	@echo ""
	@echo "install namesdb-editor -------------------------------------------------"
	-rm -Rf $(APPDIR)/namesdb_public
	ln -s $(INSTALL_PUBLIC)/namessite/namesdb_public $(APPDIR)/namesdb_public
	source $(VIRTUALENV)/bin/activate; \
	uv pip install -U -r $(INSTALL_PUBLIC)/requirements.txt

uninstall-namesdb-public: install-virtualenv

clean-namesdb-public:
	-rm -Rf $(INSTALL_PUBLIC)/build
	-rm -Rf $(INSTALL_PUBLIC)/namesdb.egg-info
	-rm -Rf $(INSTALL_PUBLIC)/dist


get-ireizo-public:
	@echo ""
	@echo "get-ireizo-public -------------------------------------------------------"
	git status | grep "On branch"
	if test -d $(INSTALL_IREIZO); \
	then cd $(INSTALL_IREIZO) && git pull; \
	else cd $(INSTALL_BASE) && git clone $(SRC_REPO_IREIZO); \
	fi

install-ireizo-public: install-virtualenv
	@echo ""
	@echo "install ireizo-public -------------------------------------------------"
	-rm -Rf $(APPDIR)/ireizo_public
	ln -s $(INSTALL_IREIZO)/ireizo_public $(APPDIR)/ireizo_public
# 	source $(VIRTUALENV)/bin/activate; \
# 	uv pip install -U -r $(INSTALL_IREIZO)/requirements.txt

uninstall-ireizo-public: install-virtualenv

clean-ireizo-public:
	-rm -Rf $(INSTALL_IREIZO)/build
	-rm -Rf $(INSTALL_IREIZO)/namesdb.egg-info
	-rm -Rf $(INSTALL_IREIZO)/dist


clean-pip:
	-rm -Rf $(PIP_CACHE_DIR)/*


install-configs:
	@echo ""
	@echo "installing configs ----------------------------------------------------"
	-mkdir $(CONF_BASE)
	python -c 'import random; print "".join([random.choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)") for i in range(50)])' > $(CONF_SECRET)
	chown ddr.ddr $(CONF_SECRET)
	chmod 640 $(CONF_SECRET)
# web app settings
	cp $(INSTALLDIR)/conf/namesdbeditor.cfg $(CONF_BASE)
	chown root.ddr $(CONF_PRODUCTION)
	chmod 640 $(CONF_PRODUCTION)
	touch $(CONF_LOCAL)
	chown root.ddr $(CONF_LOCAL)
	chmod 640 $(CONF_LOCAL)

uninstall-configs:
	-rm $(CONF_PRODUCTION)
	-rm $(CONF_LOCAL)
	-rm $(CONF_SECRET)

install-daemons-configs:
	@echo ""
	@echo "configuring daemons -------------------------------------------------"
# nginx
	cp $(INSTALLDIR)/conf/nginx.conf $(NGINX_CONF)
	chown root.root $(NGINX_CONF)
	chmod 644 $(NGINX_CONF)
	-ln -s $(NGINX_CONF) $(NGINX_CONF_LINK)
# supervisord
	cp $(INSTALLDIR)/conf/supervisor.conf $(SUPERVISOR_GUNICORN_CONF)
	chown root.root $(SUPERVISOR_GUNICORN_CONF)
	chmod 644 $(SUPERVISOR_GUNICORN_CONF)

uninstall-daemons-configs:
	-rm $(NGINX_CONF_LINK)
	-rm $(NGINX_CONF)
	-rm $(SUPERVISOR_GUNICORN_CONF)


install-static: collectstatic

collectstatic:
	@echo ""
	@echo "collectstatic -------------------------------------------------------"
	source $(VIRTUALENV)/bin/activate; \
	python $(APPDIR)/manage.py collectstatic --noinput
