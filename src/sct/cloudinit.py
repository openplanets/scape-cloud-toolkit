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

import pkg_resources

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import yaml
import base64


class BaseHandler(object):
    def to_mime(self):
        raise NotImplementedError()


class CloudConfig(BaseHandler):
    """
    Sadly Ubuntu 12.04 does not support CloudInit mergers...
    ToDo: find a way to work around
    """

    def __init__(self, configuration):
        self.configuration = configuration

    def to_mime(self):
        buffer = StringIO.StringIO()
        yaml.dump(self.configuration, buffer, default_flow_style=False)
        message = MIMEText(buffer.getvalue(), "cloud-config", "utf8")
        return message


class CloudUserScriptFile(BaseHandler):
    def __init__(self):
        raise NotImplementedError()


class CloudUserScript(BaseHandler):
    def __init__(self, content):
        self.content = content

    def to_mime(self):
        message = MIMEText(self.content, "x-shellscript", "utf8")
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


class PuppetMasterInitCloudBashScript(CloudSHScript):
    script = """
    . /etc/profile
    echo 'START=yes\nDAEMON_OPTS=""\n' > /etc/default/puppet
    sed -i 's|127.0.0.1|127.0.0.1 puppet|g' /etc/hosts
    /etc/init.d/puppet start

    echo "*" > /etc/puppet/autosign.conf
    /etc/init.d/puppetmaster restart

    puppet module install puppetlabs/puppetdb

    #puppet apply /etc/puppet_scape_master.pp

    """

    def __init__(self):
        CloudSHScript.__init__(self, self.script)


class CloudInit(object):
    def __init__(self):
        self.handler = []

    def add_handler(self, handler):
        self.handler.append(handler)

    def generate(self):
        message = MIMEMultipart()
        for hndlr in self.handler:
            message.attach(hndlr.to_mime())

        return message.as_string()

    def __str__(self):
        return self.generate()

