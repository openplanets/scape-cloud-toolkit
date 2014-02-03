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

import logging
import urlparse

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

import libcloud.security


class CloudController( object ):
    log = logging.getLogger( "CloudController" )

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

    def create_node (self, **args):
        log = logging.getLogger( "create_node" )
        requested_node_size = args["size"]
        requested_node_image = args["image"]
        requested_node_name = args["name"]

        log.debug( "Looking up sizes" )
        node_sizes = [size for size in self.conn.list_sizes( ) if size.id == requested_node_size]
        log.debug( "Looking up images" )
        node_images = [image for image in self.conn.list_images( ) if image.id == requested_node_image]
        log.debug( "Looking up existing nodes" )
        matching_nodes = [node for node in self.conn.list_nodes( ) if node.name == requested_node_name]

        if matching_nodes:
            log.critical( "Request node name (%s) is in use", requested_node_name )
            return False

        if not node_sizes:
            log.critical( "Requested size (%s) was not found", requested_node_image )
            return False

        if not node_images:
            log.critical( "Requested size (%s) was not found", requested_node_size )
            return False

        node_size = node_sizes[0]
        node_image = node_images[0]

        log.info( "Creating node %s (image=%s, size=%s)", requested_node_name, requested_node_image,
                  requested_node_size )
        self.conn.create_node( name=requested_node_name, image=node_image, size=node_size, ex_addressingtype="private" )
        return True

    def list_nodes (self, **kwargs):
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

        return nodes

    def list_images (self, **kwargs):
        log = logging.getLogger( "list_images" )
        images = self.conn.list_images( )
        available_images = {}
        for image in images:
            extra_info = image.extra
            if 'state' not in extra_info:
                continue
            if extra_info["state"] != "available":
                continue
            if image.id in available_images:
                log.warn( "Got same image twice: %s", image.id )
            image_entry = {}
            available_images[image.id] = image_entry
            image_entry["uuid"] = image.uuid
            image_entry["name"] = image.name

        return available_images

    def list_sizes (self, **kwargs):
        log = logging.getLogger( "list_sizes" )
        sizes = self.conn.list_sizes( )
        available_sizes = {}
        for size in sizes:
            if size.id in available_sizes:
                log.warn( "Got same size twice: %s", size.id )
                continue
            size_entry = {}
            available_sizes[size.id] = size_entry

            size_entry['name'] = size.name
            size_entry['ram'] = size.ram
            size_entry['disk'] = size.disk

        return available_sizes

    def list_security_groups (self, **kwargs):
        log = logging.getLogger( "list_security_groups" )
        log.debug( "Listing security groups" )
        groups = self.conn.ex_list_security_groups( )
        return groups

    def create_security_group (self, **kwargs):
        log = logging.getLogger( "create_security_group" )
        sg_name = kwargs["name"]
        sg_description = kwargs["description"]

        if sg_description is None:
            sg_description = "SCAPE Cloud Toolkit autogenerated"
        log.debug( "Attempting to create security group %s", sg_name )
        if sg_name in self.conn.ex_list_security_groups( ):
            log.error( "Security Group %s is already defined!", sg_name )
            return False
        self.conn.ex_create_security_group( sg_name, sg_description )
        return True

    def delete_security_group (self, **kwargs):
        log = logging.getLogger( "delete_security_group" )
        sg_name = kwargs["name"]
        log.debug( "Attempting to delete security group %s", sg_name )
        if not sg_name in self.conn.ex_list_security_groups( ):
            log.error( "Security group %s is not defined", sg_name )
            return False
        self.conn.ex_delete_security_group_by_name( sg_name )
        log.info( "Security Group Deleted" )
        return True

    def authorize_security_group (self, **kwargs):
        log = logging.getLogger( "delete_security_group" )
        log.debug( "Attempting to authorize an IP" )

        sg_name = kwargs["name"]
        sg_from_port = kwargs["from_port"]
        sg_to_port = kwargs["to_port"]
        sg_protocol = kwargs["protocol"]
        sg_cidr_ip = kwargs["cidr_ip"]

        if sg_name not in self.conn.ex_list_security_groups( ):
            log.error( "Security group %s is not defined. Defining", sg_name )
            self.conn.ex_create_security_group( sg_name, "SCAPE Cloud Toolkit autogenerated" )

        if sg_to_port is None:
            sg_to_port = sg_from_port

        self.conn.ex_authorize_security_group( sg_name, sg_from_port, sg_to_port, sg_cidr_ip, sg_protocol )
        log.info( "%s traffic from port %d-%d to %s authorized", sg_protocol, sg_from_port, sg_to_port, sg_cidr_ip )
        return True

    def list_addresses (self, **kwargs):
        log = logging.getLogger( "list_addresses" )
        log.debug( "Listing addresses" )

        result = self.conn.ex_describe_all_addresses( kwargs.get( "associated", None ) )
        addresses = {}
        for addr in result:
            addresses[addr.ip] = {
                'domain': addr.domain,
                'instance_id': addr.instance_id
            }
        return addresses

    def list_available_addresses (self, **kwargs):
        log = logging.getLogger( "list_available_addresses" )
        available_addresses = {}
        addresses = self.list_addresses( )
        for addr in addresses:
            entry = addresses[addr]
            if entry.get( "instance_id", None ) is None:
                available_addresses[addr] = addresses[addr]
        return available_addresses

    def associate_address (self, **kwargs):
        pass

