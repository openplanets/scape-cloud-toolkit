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
import pkg_resources
import uuid
import time
from sct.controller import BaseController
from sct.cloudinit import CloudInit, CloudConfig, DefaultPuppetCloudConfig, DefaultJavaCloudCloudConfig
from sct.cloudinit import PuppetMasterCloudConfig, PuppetMasterInitCloudBashScript, CloudConfigStoreFile
from sct.skapur import SkapurClient
from sct.templates import get_template
from sct.templates.base import generate_node_content


SKAPUR_PORT = 8088

class ClusterController(BaseController):
    def __init__(self, config, cloud_controller):
        BaseController.__init__(self, config)
        self.cloud_controller = cloud_controller
        self._initialized = False
        if config.loaded:
            self.init()

    def init(self): # Used for lazzy init
        if not self._initialized:
            if 'clusters' not in self.configObj.config:
                self.configObj.config["clusters"] = {}
            self.clusters_config = self.configObj.config.get("clusters")
            BaseController.init(self)

            self._initialized = True


    def create(self, name, image, size, security_group, module_repository_url, module_repository_branch,
               module_repository_tag):
        log = logging.getLogger("cluster.create")

        config_registry = self.get_config_registry()
        if name in self.clusters_config:
            log.error("Cluster %s is already defined", name)
            return False
        self.clusters_config[name] = {}
        cluster_config = self.clusters_config[name]
        cluster_config["nodes"] = {}
        cluster_nodes_config = cluster_config["nodes"]

        requested_size = size or config_registry.get('cluster.default_size', None)
        requested_image = image or config_registry.get('cluster.default_image', None)
        requested_security_group = security_group or config_registry.get('cluster.default_security_group', None)
        requested_module_repository_url = module_repository_url or config_registry.get(
            "cluster.default_module_repository_url")
        requested_module_repository_branch = module_repository_branch or config_registry.get(
            "cluster.default_module_repository_branch")
        requested_module_repository_tag = module_repository_tag or config_registry.get(
            "cluster.default_module_repository_tag")

        if requested_size is None:
            log.error("Size not specified and not defined in config (cluster.default_size)")
            return False

        if requested_image is None:
            log.error("Image not specified and not defined in config (cluster.default_image)")
            return False

        if requested_security_group is None:
            log.error("Security group not specified and not defined in config (cluster.default_security_group)")
            return False

        if requested_module_repository_url is None:
            log.warn(
                "Puppet module repository is not specified and not defined in config (cluster.default_module_repository_url)")
            log.info("Using repository https://bitbucket.org/scapeuvt/puppet-modules.git")
            requested_module_repository_url = "https://bitbucket.org/scapeuvt/puppet-modules.git"

        if requested_module_repository_branch is None:
            log.warn(
                "No module repository branch specified in call or config (cluster.default_module_repository_branch). Using `master`")
            requested_module_repository_branch = "master"

        if 'main_keypair' not in cluster_config:
            cluster_config['main_keypair'] = "%s_MainKeypair" % name
        keypair_name = cluster_config['main_keypair']

        found_keypairs = self.cloud_controller.list_keypairs(name=keypair_name)
        if found_keypairs:
            keypair_name = found_keypairs[0].name  # NoOp
        else:
            result = self.cloud_controller.create_keypair(name=keypair_name)
            if not result:
                log.error("Failed to create keypair %s for cluster %s", keypair_name, name)
                return False

        management_node_name = "%s_Manager" % name
        hmac_secret = uuid.uuid4().get_hex()
        cloudInit = CloudInit()
        configuration = {
            'apt_update': True, # Runs `apt-get update` on first run
            'apt_upgrade': False, #  Runs `apt-get upgrade
            'manage_etc_hosts': True,
            #'byobu_by_default': "system"
        }
        cloudInit.add_handler(CloudConfig(configuration))
        cloudInit.add_handler(
            CloudConfigStoreFile(pkg_resources.resource_string(__name__, "resources/puppet/bootstrap_master.pp"),
                                 "/etc/puppet_scape_master.pp"))
        cloudInit.add_handler(CloudConfigStoreFile(pkg_resources.resource_string(__name__, "resources/puppet/puppet.conf"),
                                                   "/etc/puppet/puppet.conf"))
        #cloudInit.add_handler(DefaultPuppetCloudConfig())
        cloudInit.add_handler(PuppetMasterCloudConfig())
        cloudInit.add_handler(
            PuppetMasterInitCloudBashScript(URL=requested_module_repository_url, HMACSECREET=hmac_secret))

        #cloudInit.add_handler(DefaultJavaCloudCloudConfig()) # Install java from webupd8
        userdata = str(cloudInit)
        userdata_compressed = cloudInit.generate(compress=True)
        log.debug("User data size: raw / compressed = %d/%d", len(userdata), len(userdata_compressed))

        node = self.cloud_controller.create_node(name=management_node_name, size=requested_size, image=requested_image,
                                                 security_group=requested_security_group, auto_allocate_address=True,
                                                 keypair_name=keypair_name, userdata=userdata_compressed)

        if not node:
            log.error("Error creating management node.")
            return False

        cluster_nodes_config["management_node"] = {'name': management_node_name,
                                                   'instance_id': node["instance_id"],
                                                   'ip': node["ip"],
                                                   'private_ips': node["private_ips"],
                                                   'hmac_secret': hmac_secret
        }
        return True

    def get_template_nodes(self, cluster_config, template_name):
        """
        Return all nodes implementing a template
        """
        nodes = cluster_config.get("nodes", {})
        result = []
        for node_name, node_entry in nodes.items():
            node_template = node_entry.get("template", None)
            if node_template is None:
                continue
            if node_template == template_name:
                result.append((node_name, node_entry))
        return result


    def add_node(self, template_name, cluster_name):
        log = logging.getLogger("cluster.add_node")
        config_registry = self.get_config_registry()
        cluster_config = self.clusters_config.get(cluster_name)
        if cluster_config is None:
            log.error("No such cluster: %s", cluster_name)
            return False
        template = get_template(template_name)

        #ToDo: We should use cluster wide config first and after that global config
        requested_size = config_registry.get('cluster.default_size', None)
        requested_image = config_registry.get('cluster.default_image', None)
        requested_security_group = config_registry.get('cluster.default_security_group', None)

        if requested_size is None:
            log.error("Node size is unknown")
            return False

        if requested_security_group is None:
            log.error("Security Group is unknown")
            return False

        if requested_image is None:
            log.error("Requested image is unknown")
            return False

        if 'main_keypair' not in cluster_config:
            log.error("Invalid cluster. Keypair not defined.")
            return False
        keypair_name = cluster_config['main_keypair']

        nodes = self.get_template_nodes(cluster_config, template_name)
        template_nodes_count = len(nodes)
        if template["max-node-count"] is None:
            template["max-node-count"] = 10000
        if template_nodes_count >= template['max-node-count']:
            log.error("Can not create node as it would exceed the maximum allowed nodes (%d) for template %s",
                      template['max-node-count'], template_name)
            return False

        mgmt_node_config = cluster_config.setdefault('nodes', {}).get('management_node', None)
        if mgmt_node_config is None:
            log.error("Invalid cluster. Management node is missing. Aborting")
            return False
        mgmt_node_privip = mgmt_node_config['private_ips']
        mgmt_node_ip = mgmt_node_config['ip']
        mgmt_node_hmac_secret = mgmt_node_config["hmac_secret"]
        if not mgmt_node_privip:
            log.error("Management does not seem to have any private IP's. Aborting!")
            return False
        puppet_server = mgmt_node_privip[0]
        log.info("Configuring node to use puppet server: %s", puppet_server)
        cloudInitHandler = template['cloudinit'](cluster_config=cluster_config, puppet_server=puppet_server)
        cloudInit = CloudInit([cloudInitHandler, ])

        user_data = cloudInit.generate(compress=False)
        user_data_compress = cloudInit.generate(compress=True)
        node_names = [i[0] for i in nodes]
        if template_nodes_count == 0:
            node_index = 1
        else:
            for idx in range(1, template_nodes_count + 2):
                desired_node_name = "%s_%s_%s" % (cluster_name, cloudInitHandler.shortName, idx)
                if desired_node_name in node_names:
                    continue
                node_index = idx
                break

        desired_node_name = "%s_%s_%s" % (cluster_name, cloudInitHandler.shortName, node_index)
        log.debug("Desired node name: %s", desired_node_name)
        log.debug("User data size: raw / compressed = %d/%d", len(user_data), len(user_data_compress))
        log.debug("Attempting to start node.")

        cloud_controller = self.cloud_controller
        node = cloud_controller.create_node(name=desired_node_name, size=requested_size, image=requested_image,
                                            security_group=requested_security_group, auto_allocate_address=True,
                                            keypair_name=keypair_name, userdata=user_data)
        if not node:
            log.error("Failed to create node.")
            return False

        private_name = node["private_dns"]

        cluster_config_nodes = cluster_config['nodes']
        cluster_config_nodes[desired_node_name] = {
            'name': desired_node_name,
            'instance_id': node["instance_id"],
            'ip': node["ip"],
            'private_ips': node["private_ips"],
            'private_dns': node["private_dns"],
            'template': template_name
        }

        skapur_url = "http://%s:%d" % (mgmt_node_ip, SKAPUR_PORT)
        skapurClient = SkapurClient(secret=mgmt_node_hmac_secret, url=skapur_url)
        start_time = time.time()
        skapur_timeout = 120

        if not skapurClient.isalive():
            log.info("Management is not yet UP. Waiting %d seconds" % skapur_timeout)
        current_duration = 0
        while not skapurClient.isalive():
            time.sleep(1)
            current_time = time.time()
            current_duration = current_time - start_time
            if current_duration > skapur_timeout:
                log.error("Failed to connect to management node in %d seconds", current_duration)
                self.delete(desired_node_name)
                return False
        log.info("Connected to management server (%d seconds)", current_duration)
        puppet_node_custom = ""
        puppet_node_config = generate_node_content(private_name, cloudInitHandler.get_puppet_node_specification(private_name))
        print puppet_node_config
        puppet_node_file_name="%s.pp" % desired_node_name
        skapurClient.store(puppet_node_file_name, puppet_node_config)

        return True
