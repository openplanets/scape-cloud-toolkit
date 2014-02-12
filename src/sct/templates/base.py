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
from email.mime.multipart import MIMEMultipart
from sct.cloudinit import BaseHandler, FormattedCloudInitShScript, CloudConfig

import pkg_resources


class TemplateHandler(object):
    def __init__(self, cluster_config=None, **kwargs):
        self.cluster_config = cluster_config


class BaseTemplate(TemplateHandler, BaseHandler):
    def __init__(self, parts=[], *args, **kwargs):
        BaseHandler.__init__(self)
        TemplateHandler.__init__(self, *args, **kwargs)
        self._cloud_init_parts = []
        self.cloud_config = CloudConfig()
        self.add_part(self.cloud_config)

        if parts:
            self._cloud_init_parts.extend(parts)

    def getCloudInit(self):
        return self.to_mime()

    def add_part(self, part):
        self._cloud_init_parts.append(part)

    def to_mime(self):
        message = MIMEMultipart()
        for part in self._cloud_init_parts:
            message.attach(part.to_mime())
        return message


class PuppetClientNode(BaseTemplate):
    setup_script = pkg_resources.resource_string(__name__, "resources/setup_puppet_agent.sh")
    puppet_node = "default_node"
    def __init__(self, puppet_server, *args, **kwargs):
        BaseTemplate.__init__(self, *args, **kwargs)

        # Register the puppet master hostname

        self.add_part(FormattedCloudInitShScript(self.setup_script, {'puppetServer': puppet_server}))

        # Add the puppet repository's

        self.cloud_config.add_apt_source(
            {'source': 'deb http://apt.puppetlabs.com precise main',
             'keyid': '4BD6EC30',
             'filename': 'puppet-labs-main.list'
            }
        )
        self.cloud_config.add_apt_source(
            {'source': 'deb http://apt.puppetlabs.com precise dependencies',
             'keyid': '4BD6EC30',
             'filename': 'puppet-labs-deps.list'
            }
        )

        # Install puppet
        self.cloud_config.add_package("puppet")

        # Set global options
        self.cloud_config.set_option('manage_etc_hosts', True) # CloudInit should manage hosts
        self.cloud_config.set_option('apt_update', True) # Update the package list
        self.cloud_config.set_option('apt_upgrade',
                                     False) # Disable the Package upgrade. ToDo: This should be on by default

    def get_puppet_node_specification(self, dns_name):
        """This should return a tuple containing:
        (parent_node, content)

        -parent_node: the node that should be extended by the node specification
        -content: the content of the node specification. It can be none
        """
        parent_node = self.puppet_node
        return (parent_node, None)



def generate_node_content(node_name, node_spec):
    parent_node, node_content = node_spec
    spec = "node %s " % node_name
    if parent_node:
        spec = "%s inherits %s" % (spec, parent_node)
    if node_content is None:
        node_content = ""
    spec = "%s {  \n  %s \n}\n" % (spec, node_content)
    return spec


class DefaultNodeTemplate(PuppetClientNode):
    def __init__(self, *args, **kwargs):
        PuppetClientNode.__init__(self, *args, **kwargs)




