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
from sct.controller import BaseController
from sct.cloudinit import CloudInit, CloudConfig, DefaultPuppetCloudConfig, DefaultJavaCloudCloudConfig
from sct.cloudinit import PuppetMasterCloudConfig, PuppetMasterInitCloudBashScript, CloudConfigStoreFile


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
        #cloudInit.add_handler(DefaultPuppetCloudConfig())
        cloudInit.add_handler(PuppetMasterCloudConfig())
        cloudInit.add_handler(PuppetMasterInitCloudBashScript(URL=requested_module_repository_url))

        #cloudInit.add_handler(DefaultJavaCloudCloudConfig()) # Install java from webupd8

        print "Current userdata size:", len(str(cloudInit))

        node = self.cloud_controller.create_node(name=management_node_name, size=requested_size, image=requested_image,
                                                 security_group=requested_security_group, auto_allocate_address=True,
                                                 keypair_name=keypair_name, userdata=cloudInit.generate(compress=False))

        if not node:
            log.error("Error creating management node.")
            return False

        cluster_nodes_config["management_node"] = {'name': management_node_name,
                                                   'instance_id': node["instance_id"],
                                                   'ip': node["ip"]
        }
        return True
