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
import libcloud.security

class BaseController(object):
    def __init__(self, config):
        self.configObj = config
        self.config = None
        self.global_config = None
        self._initialized = False

    def init(self):
        if not self._initialized:
            self.global_config = self.configObj.config

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


    def _get_keypair_config_container(self):
        """This should go to the "cluster" module
        """
        config = self.configObj.config
        if 'keypairs' in config:
            return config.get('keypairs')
        else:
            config["keypairs"] = {}
            return config.get('keypairs')

    def list_keypairs(self, **args):
        """This should go to the "cluster" module
        """
        name = args.get("name", None)
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
        """This should go to the "cluster" module
        """
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
