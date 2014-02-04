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

import logging
import urlparse
import time
import os
import codecs

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

import libcloud.security


class BaseController(object):

    def disable_ssl_check(self):
        # ToDo: Find a way to workaround in a sane way the warning
        # and not by disabling it
        import warnings

        warnings.filterwarnings("ignore", module="libcloud.httplib_ssl")
        libcloud.security.VERIFY_SSL_CERT = False

    def get_config_registry(self):
        if 'config' not in self.global_config:
            self.global_config['config'] = {}
        return self.global_config.get('config')


class ClusterController(BaseController):
    def __init__(self, config, cloud_controller):
        super(BaseController, self).__init__()
        self.configObj = config
        self.config = None
        self.global_config = None
        self._initialized = False
        self.cloud_controller = cloud_controller
        if config.loaded:
            self.init()

    def init(self): # Used for lazzy init
        if not self._initialized:
            if 'clusters' not in self.configObj.config:
                self.configObj.config["clusters"] = {}
            self.config = self.configObj.config.get("clusters")
            self.global_config = self.configObj.config
            self._initialized = True

    def create(self, name):
        log = logging.getLogger("cluster.create")
        log.debug('Trying to create cluster named "%s"', name)
        if name in self.config:
            log.error("Cluster %s is already defined", name)
            return False
        self.config[name] = {}
        cluster_config = self.config[name]

        node = self.cloud_controller.create_node()

    def delete(self, name):
        # ToDo: Complete the implementation
        log = logging.getLogger("cluster.delete")
        if name in self.config:
            del self.config[name]
            return True
        log.warn("No cluster with name '%s' to delete", name)
        return  False


class CloudController(BaseController):
    log = logging.getLogger("CloudController")

    def __init__(self, config):
        super(BaseController, self).__init__()
        self.configObj = config
        self._initialized = False
        self.cluster = ClusterController(config, self)
        self.conn = None
        if config.loaded:
            self.init()
            self.cluster.init()

    def init(self):
        if not self._initialized:
            config = self.configObj.config['euca']
            if 'eucalyptus_cert_file_path' in config:
                libcloud.security.CA_CERTS_PATH.append(config["eucalyptus_cert_file_path"])
            self.driver = get_driver(Provider.EUCALYPTUS)
            ec2_url = config['ec2_url']
            url = urlparse.urlparse(ec2_url)
            self.conn = self.driver(config['ec2_access_key'],
                                    config['ec2_secret_key'],
                                    host=url.hostname,
                                    port=url.port)
            self._initialized = True
            self.cluster.init()

    def create_node(self, name=None, size=None, image=None, userdata=None, userdata_file=None,
                    network_setup_timeout=200, auto_allocate_address=False, security_group=None):
        log = logging.getLogger("create_node")
        requested_node_size = size
        requested_node_image = image
        requested_node_name = name
        requested_autoallocate_address = auto_allocate_address
        requested_security_group = security_group

        if size is None:
            raise ValueError("Argument `size` needs to be provided")
        if image is None:
            raise ValueError("Argument `image` needs to be provided")
        if name is None:
            raise ValueError("Argument `name` needs to be provided")
        if security_group is None:
            raise ValueError("Argument `security_group` needs to be provided")

        log.debug("Looking up security groups")
        sec_groups = self.list_security_groups()
        if requested_security_group not in sec_groups:
            log.error("Requested security group is not available")
            return False

        log.debug("Looking up sizes")
        node_sizes = [size for size in self.conn.list_sizes() if size.id == requested_node_size]
        log.debug("Looking up images")
        node_images = [image for image in self.conn.list_images() if image.id == requested_node_image]
        log.debug("Looking up existing nodes")
        matching_nodes = [node for node in self.conn.list_nodes() if node.name == requested_node_name]

        if matching_nodes:
            log.critical("Request node name (%s) is in use", requested_node_name)
            return False

        if not node_sizes:
            log.critical("Requested size (%s) was not found", requested_node_image)
            return False

        if not node_images:
            log.critical("Requested size (%s) was not found", requested_node_size)
            return False

        node_size = node_sizes[0]
        node_image = node_images[0]

        requested_userdata = None
        if userdata is not None:
            requested_userdata = userdata
        if userdata_file is not None:
            if not os.path.exists(userdata_file):
                log.error("Missing required user-data file: %s", userdata_file)
                return False
            with codecs.open(userdata_file, encoding="utf8") as userdata_fd:
                requested_userdata = userdata_fd.read()

        if requested_userdata is None:
            log.warn("No userdata provided!")

        log.info("Creating node %s (image=%s, size=%s)", requested_node_name, requested_node_image,
                 requested_node_size)

        self.conn.create_node(name=requested_node_name, image=node_image, size=node_size,
                              ex_addressingtype="private", ex_security_groups=[requested_security_group, ],
                              ex_userdata=requested_userdata)

        start_time = time.time()
        log.debug("Waiting for the setup of the private network. Maximum duration = %f seconds",
                  network_setup_timeout)
        node = None
        while True:
            duration = time.time() - start_time
            if duration > network_setup_timeout: # Wait for network setup
                # ToDo: At this stage the node will remain in "limbo"
                log.critical("The Cloud failed to setup the addresses in expected time")
                return False
            nodes = [node for node in self.conn.list_nodes() if node.name == requested_node_name]
            if not nodes:
                log.error("Failed to create node %s", requested_node_name)
                return False
            node = nodes[0]
            priv_ips = node.private_ips
            if not priv_ips:
                time.sleep(1)
                continue
            if priv_ips:
                if priv_ips[0] == "0.0.0.0": ### hack
                    time.sleep(1)
                    continue
            log.debug("Private network was setup after %d seconds", duration)
            break

        if not node:
            log.error("Failed to create node %s", requested_node_name)
            return False

        response = {'id': node.id, 'instance_id': node.extra['instance_id']}
        if requested_autoallocate_address:
            addr = self.associate_address(instance_id=node.extra['instance_id'])
            response["ip"] = addr

        return response


    def list_nodes(self, **kwargs):
        conn = self.conn
        euca_nodes = conn.list_nodes()
        nodes = []
        for euca_node in euca_nodes:
            node = {'id': euca_node.uuid,
                    'name': euca_node.name,
                    'image-id': euca_node.extra.get('image_id', None),
                    'instance-id': euca_node.extra.get('instance_id', None),
                    'instance-type': euca_node.extra.get('instance_type', None),
                    'instance-status': euca_node.extra.get('status', None),
                    'public-networking': {
                        'public-ips': list(set(getattr(euca_node, 'public_ips', ()))),
                        'public-dns': euca_node.extra.get('dns_name', None),
                    },
                    'private-networking': {
                        'private-ips': list(set(getattr(euca_node, 'private_ips', ()))),
                        'private-dns': euca_node.extra.get('private_dns', None),
                    }
            }
            nodes.append(node)

        return nodes

    def list_images(self, **kwargs):
        log = logging.getLogger("list_images")
        images = self.conn.list_images()
        available_images = {}
        for image in images:
            extra_info = image.extra
            if 'state' not in extra_info:
                continue
            if extra_info["state"] != "available":
                continue
            if image.id in available_images:
                log.warn("Got same image twice: %s", image.id)
            image_entry = {}
            available_images[image.id] = image_entry
            image_entry["uuid"] = image.uuid
            image_entry["name"] = image.name

        return available_images

    def list_sizes(self, **kwargs):
        log = logging.getLogger("list_sizes")
        sizes = self.conn.list_sizes()
        available_sizes = {}
        for size in sizes:
            if size.id in available_sizes:
                log.warn("Got same size twice: %s", size.id)
                continue
            size_entry = {}
            available_sizes[size.id] = size_entry

            size_entry['name'] = size.name
            size_entry['ram'] = size.ram
            size_entry['disk'] = size.disk

        return available_sizes

    def list_security_groups(self, **kwargs):
        log = logging.getLogger("list_security_groups")
        log.debug("Listing security groups")
        groups = self.conn.ex_list_security_groups()
        return groups

    def create_security_group(self, **kwargs):
        log = logging.getLogger("create_security_group")
        sg_name = kwargs["name"]
        sg_description = kwargs["description"]

        if sg_description is None:
            sg_description = "SCAPE Cloud Toolkit autogenerated"
        log.debug("Attempting to create security group %s", sg_name)
        if sg_name in self.conn.ex_list_security_groups():
            log.error("Security Group %s is already defined!", sg_name)
            return False
        self.conn.ex_create_security_group(sg_name, sg_description)
        return True

    def delete_security_group(self, **kwargs):
        log = logging.getLogger("delete_security_group")
        sg_name = kwargs["name"]
        log.debug("Attempting to delete security group %s", sg_name)
        if not sg_name in self.conn.ex_list_security_groups():
            log.error("Security group %s is not defined", sg_name)
            return False
        self.conn.ex_delete_security_group_by_name(sg_name)
        log.info("Security Group Deleted")
        return True

    def authorize_security_group(self, **kwargs):
        log = logging.getLogger("delete_security_group")
        log.debug("Attempting to authorize an IP")

        sg_name = kwargs["name"]
        sg_from_port = kwargs["from_port"]
        sg_to_port = kwargs["to_port"]
        sg_protocol = kwargs["protocol"]
        sg_cidr_ip = kwargs["cidr_ip"]

        if sg_name not in self.conn.ex_list_security_groups():
            log.error("Security group %s is not defined. Defining", sg_name)
            self.conn.ex_create_security_group(sg_name, "SCAPE Cloud Toolkit autogenerated")

        if sg_to_port is None:
            sg_to_port = sg_from_port

        self.conn.ex_authorize_security_group(sg_name, sg_from_port, sg_to_port, sg_cidr_ip, sg_protocol)
        log.info("%s traffic from port %d-%d to %s authorized", sg_protocol, sg_from_port, sg_to_port, sg_cidr_ip)
        return True

    def list_addresses(self, **kwargs):
        log = logging.getLogger("list_addresses")
        log.debug("Listing addresses")

        result = self.conn.ex_describe_all_addresses(kwargs.get("associated", None))
        addresses = {}
        for addr in result:
            addresses[addr.ip] = addr
        return addresses

    def list_available_addresses(self, **kwargs):
        #log = logging.getLogger( "list_available_addresses" )
        available_addresses = {}
        addresses = self.list_addresses()
        for addr in addresses:
            entry = addresses[addr]
            if entry.instance_id is None:
                available_addresses[addr] = addresses[addr]
        return available_addresses


    def allocate_address(self, **kwargs):
        log = logging.getLogger("allocate_address")

        response = self.conn.ex_allocate_address()

        if response:
            log.debug("Allocating new address %s", response.ip)
            return response
        else:
            log.warn("Failed to allocate new address.")
            return False

    def get_address(self, **kwargs):
        log = logging.getLogger("get_address")
        address = None
        available_addreses = self.list_available_addresses()
        if available_addreses:
            address_id = available_addreses.keys().pop()
            log.debug("Found already existing address: %s", available_addreses[address_id].ip)
            address = available_addreses[address_id]
            return address
        else:
            log.debug("No addresses available. Trying to obtain a new one")
            address = self.allocate_address()
            return address


    def get_libcloud_nodes(self, node_id):
        nodes = self.conn.list_nodes()
        selected_nodes = [node for node in nodes if node.id == node_id or node.extra["instance_id"] == node_id]
        return selected_nodes

    def associate_address(self, **kwargs):
        log = logging.getLogger("associate_address")
        instance_id = kwargs["instance_id"]
        requested_address = kwargs.get("address", None)

        nodes = self.get_libcloud_nodes(instance_id)
        if nodes:
            node = nodes.pop()
        else:
            log.error("Could not find node %s by instance-id or id", instance_id)
            return False

        if requested_address is None:
            requested_address = self.get_address()

        self.conn.ex_associate_address_with_node(node, requested_address)
        return requested_address.ip

    def _get_keypair_config_container(self):
        config = self.configObj.config
        if 'keypairs' in config:
            return config.get('keypairs')
        else:
            config["keypairs"] = {}
            return config.get('keypairs')

    def list_keypairs(self, **args):
        name = args["name"]
        all_keypairs = self.conn.list_key_pairs()
        keypairs = []
        for keypair in all_keypairs:
            if name is None:
                keypairs.append(keypair)
            elif keypair.name == name:
                keypairs.append(keypair)
            else:
                continue
        return keypairs


    def create_keypair(self, **kwargs):
        log = logging.getLogger("create_keypair")
        name = kwargs.get("name")
        config = self._get_keypair_config_container()
        keypairs = self.list_keypairs(name=name)
        if keypairs:
            log.critical("Keypair %s already exists", name)
            return False
        keypair = self.conn.create_key_pair(name)

        config[name] = {
            'private_key': keypair.private_key,
            'public_key': keypair.public_key
        }

        return True
