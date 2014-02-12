# -*- coding: utf-8 -*-
"""
Copyright 2014 Universitatea de Vest din Timișoara

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

@author: Marian Neagul <marian@info.uvt.ro>
@contact: marian@info.uvt.ro
@copyright: 2014 Universitatea de Vest din Timișoara
"""
import StringIO
from email.mime.application import MIMEApplication

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from string import Template

import yaml
import base64
import gzip


class BaseHandler(object):
    def to_mime(self):
        raise NotImplementedError()


class CloudConfig(BaseHandler):
    """
    Sadly Ubuntu 12.04 does not support CloudInit mergers...
    ToDo: find a way to work around
    """

    def __init__(self, configuration={}):
        self.__configuration = configuration

    def to_mime(self):
        buffer = StringIO.StringIO()
        yaml.dump(self.__configuration, buffer, default_flow_style=False)
        value = buffer.getvalue()
        message = MIMEText(value, "cloud-config", "utf8")
        return message

    def _get_configuration(self):
        return self.__configuration


    def add_apt_source(self, source):
        apt_sources = self.__configuration.setdefault('apt_sources', [])
        apt_sources.append(source)

    def add_package(self, package_spec):
        packages = self.__configuration.setdefault('packages', [])
        packages.append(package_spec)

    def set_option(self, key, value):
        if key in self.__configuration:
            raise KeyError("Duplicate key %s. It already has the value: %s", key, self.__configuration[key])
        self.__configuration[key] = value


class CloudUserScriptFile(BaseHandler):
    def __init__(self):
        raise NotImplementedError()


class CloudUserScript(BaseHandler):
    def __init__(self, content):
        self.__script_content = content

    def to_mime(self):
        message = MIMEText(self.__script_content, "x-shellscript", "utf8")
        return message


class CloudSHScript(CloudUserScript):
    def __init__(self, content):
        bash_content = "#!/bin/bash\n%s" % content
        CloudUserScript.__init__(self, bash_content)


class CloudConfigStoreFile(CloudSHScript):
    def __init__(self, content, destination_file):
        encoded_content = base64.encodestring(content)
        content = """
        cat <<EOF | base64 -d > %s
%s
EOF
        """ % (destination_file, encoded_content)
        CloudSHScript.__init__(self, content)


class DefaultJavaCloudCloudConfig(CloudConfig):
    configuration = {
        'apt_sources': [# Add puppet lab repository
                        {'source': 'deb http://ppa.launchpad.net/webupd8team/java/ubuntu precise main',
                         'keyid': 'EEA14886',
                         'filename': 'oracle-java.list'
                        },
        ]
    }

    def __init__(self):
        CloudConfig.__init__(self, self.configuration)


class DefaultPuppetCloudConfig(CloudConfig):
    puppet_apt_repos = [
        {'source': 'deb http://apt.puppetlabs.com precise main',
         'keyid': '4BD6EC30',
         'filename': 'puppet-labs-main.list'
        },
        {'source': 'deb http://apt.puppetlabs.com precise dependencies',
         'keyid': '4BD6EC30',
         'filename': 'puppet-labs-deps.list'
        },
    ]
    configuration = {
        #'apt_sources': puppet_apt_repos,  # Add puppet lab repository
        'packages': [
            "puppet",
            "puppetmaster-common",
            "git"
        ]
    }

    def __init__(self):
        CloudConfig.__init__(self, self.configuration)


class PuppetMasterCloudConfig(CloudConfig):
    puppet_agent_init_config = 'START=yes\nDAEMON_OPTS=""\n'

    puppet_apt_repos = [
        {'source': 'deb http://apt.puppetlabs.com precise main',
         'keyid': '4BD6EC30',
         'filename': 'puppet-labs-main.list'
        },
        {'source': 'deb http://apt.puppetlabs.com precise dependencies',
         'keyid': '4BD6EC30',
         'filename': 'puppet-labs-deps.list'
        },
    ]
    configuration = {
        'apt_sources': puppet_apt_repos, # Add puppet lab repository
        'packages': [
            "puppet",
            "puppetmaster-common",
            "puppetmaster",
            "git"
        ],
    }

    def __init__(self):
        CloudConfig.__init__(self, self.configuration)


class SimpleStringTemplate(Template):
    delimiter = "@"

    def __init__(self, *args, **kwargs):
        Template.__init__(self, *args, **kwargs)


class FormattedCloudInitShScript(CloudSHScript):
    def __init__(self, content, maps):
        tmpl = SimpleStringTemplate(content)
        new_content = tmpl.substitute(**maps)
        CloudSHScript.__init__(self, new_content)


class PuppetMasterInitCloudBashScript(FormattedCloudInitShScript):
    script = """
    . /etc/profile
    echo 'START=yes\nDAEMON_OPTS=""\n' > /etc/default/puppet
    sed -i 's|127.0.0.1|127.0.0.1 puppet|g' /etc/hosts

    SWAP_DISKS=$(blkid -s TYPE | grep -i swap | cut -d ":" -f 1)
    for DSK in $SWAP_DISKS; do
        swapon $DSK
    done


    curl -o /usr/local/bin/skapur http://ftp.info.uvt.ro/projects/scape/tools/skapur/skapur
    chmod +x /usr/local/bin/skapur
    mkdir -p /etc/puppet/manifests/nodes/
    chown puppet /etc/puppet/manifests/nodes/
    ln -s /etc/scape/modules/sct/files/templates /etc/puppet/manifests/templates
    ln -s /etc/scape/modules/sct/files/site.pp /etc/puppet/manifests/site.pp
    screen -A -m -d -S skapurpuppet sudo -u puppet /usr/local/bin/skapur  -address="0.0.0.0:8088" -store /etc/puppet/manifests/nodes/ -secret "@HMACSECREET"



    /etc/init.d/puppetmaster stop
    /etc/init.d/puppet stop
    echo "*" > /etc/puppet/autosign.conf
    rm -fr /var/lib/puppet/ssl/*
    /etc/init.d/puppetmaster start
    /etc/init.d/puppet start

    puppet module install --target-dir /etc/puppet/modules/ puppetlabs/puppetdb



    mkdir -p /etc/scape/
    apt-get install -y git
    git clone @URL /etc/scape/modules

    echo "*/10 * * * * /usr/bin/git --git-dir=/etc/scape/modules/.git --work-tree=/etc/scape/modules/  pull" >> /etc/crontab

    puppet apply /etc/puppet_scape_master.pp

    sleep 1
    /etc/init.d/puppet restart




    """

    def __init__(self, **kwargs):
        FormattedCloudInitShScript.__init__(self, self.script, kwargs)


class CloudInit(object):
    def __init__(self, handlers=[]):
        self.handler = []
        if handlers:
            self.handler.extend(handlers)

    def add_handler(self, handler):
        self.handler.append(handler)

    def _generate(self):
        message = MIMEMultipart()
        for hndlr in self.handler:
            message.attach(hndlr.to_mime())

        return message.as_string()

    def generate(self, compress=True):
        if not compress:
            return self._generate()

        strfd = StringIO.StringIO()
        with gzip.GzipFile(fileobj=strfd, mode="w", compresslevel=9) as gzfd:
            gzfd.write(self._generate())
        strfd.seek(0)

        return strfd.read()

    def __str__(self):
        return self.generate(compress=False)

