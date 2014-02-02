# -*- coding: utf-8 -*-
'''
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
'''

import sys
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

import yaml
import libcloud.security

import urlparse


class CloudController( object ):
    def __init__ (self, config):
        self.configObj = config
        self._initialized = False
        if config.loaded:
            self.init( )


    def init (self):
        if not self._initialized:
            config = self.configObj.config['euca']
            if 'eucalyptus_cert_file_path' in config:
                libcloud.security.CA_CERTS_PATH.append( config["eucalyptus_cert_file_path"] )
            self.driver = get_driver( Provider.EUCALYPTUS )
            ec2_url = config['ec2_url']
            url = urlparse.urlparse( ec2_url )
            self.conn = self.driver( config['ec2_access_key'],
                                     config['ec2_secret_key'],
                                     host=url.hostname,
                                     port=url.port )
            self._initialized = True

    def disable_ssl_check (self):
        # ToDo: Find a way to workaround in a sane way the warning
        # and not by disabling it
        import warnings

        warnings.filterwarnings( "ignore", module="libcloud.httplib_ssl" )
        libcloud.security.VERIFY_SSL_CERT = False

    def add_node (self, args):
        pass

    def list_nodes (self, args):
        conn = self.conn
        euca_nodes = conn.list_nodes( )
        nodes = []
        for euca_node in euca_nodes:
            node = {'id': euca_node.uuid,
                    'name': euca_node.name,
                    'image-id': euca_node.extra.get( 'image_id', None ),
                    'instance-id': euca_node.extra.get( 'instance_id', None ),
                    'instance-type': euca_node.extra.get( 'instance_type', None ),
                    'instance-status': euca_node.extra.get( 'status', None ),
                    'public-networking': {
                        'public-ips': list( set( getattr( euca_node, 'public_ips', () ) ) ),
                        'public-dns': euca_node.extra.get( 'dns_name', None ),
                    },
                    'private-networking': {
                        'private-ips': list( set( getattr( euca_node, 'private_ips', () ) ) ),
                        'private-dns': euca_node.extra.get( 'private_dns', None ),
                    }
            }
            nodes.append( node )
            #print euca_node
            #print euca_node.extra

        yaml.dump( nodes, sys.stdout, default_flow_style=False )


