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

import os
import sys
import yaml
import logging
from os.path import expanduser, join

CONFIG_FILE = join( expanduser( "~" ), ".sct_config" )

EUCA_VAR_MAPS = {
    'ec2_url': 'EC2_URL',
    's3_url': 'S3_URL',
    'euare_url': 'EUARE_URL',
    'token_url': 'TOKEN_URL',
    'aws_auto_scaling_url': 'AWS_AUTO_SCALING_URL',
    'aws_cloudwatch_url': 'AWS_CLOUDWATCH_URL',
    'eustore_url': 'EUSTORE_URL',
    'ec2_account_number': 'EC2_ACCOUNT_NUMBER',
    'ec2_access_key': 'EC2_ACCESS_KEY',
    'ec2_secret_key': 'EC2_SECRET_KEY',
    'aws_access_key': 'AWS_ACCESS_KEY',
    'aws_secret_key': 'AWS_SECRET_KEY',
    'ec2_user_id': 'EC2_USER_ID'

}
EUCA_BLOB_VAR_MAPS = {
    'ec2_private_key': 'EC2_PRIVATE_KEY',
    'ec2_cert': 'EC2_CERT',
    'eucalyptus_cert': 'EUCALYPTUS_CERT',
    'aws_credential_file': 'AWS_CREDENTIAL_FILE'
}


def argparse_euca_helper (parse):
    import argparse

    for key in EUCA_VAR_MAPS:
        parse.add_argument( "--%s" % key, type=str, default=None )
    for key in EUCA_BLOB_VAR_MAPS:
        parse.add_argument( "--%s" % key, type=argparse.FileType( "r" ) )


class ConfigFile( object ):
    log = logging.getLogger("ConfigFile")
    def __init__ (self):
        self.config = {}
        self.loaded = False

    def load_config (self, config_file):

        if self.loaded:
            return
        if not os.path.exists( config_file ):
            self.config = {}
            return # ToDo: We should not check the file.

        with open( config_file, "r+b" ) as config_fd:
            config_fd.seek( 0 )
            config = yaml.load( config_fd )
            if config is None:
                config = {}
            self.config = config
            self.loaded = True

        expected_cfg_dir_location = "%s.d" % config_file
        cfg_dir = config.get( "config_directory", expected_cfg_dir_location )
        if expected_cfg_dir_location != cfg_dir: # Validate location
            cfg_dir = expected_cfg_dir_location
            config["config_directory"] = expected_cfg_dir_location
        if not os.path.exists( cfg_dir ):
            os.makedirs( cfg_dir )

        euca_config = config.get( "euca", {} )
        if "eucalyptus_cert" in euca_config: # We have an eucalyptus key
            euca_cert = euca_config["eucalyptus_cert"]
            euca_cert_path = os.path.abspath( os.path.join( cfg_dir, "euca_cert.txt" ) )
            with open( euca_cert_path, "w" ) as f:
                f.write( euca_cert )
            euca_config["eucalyptus_cert_file_path"] = euca_cert_path


    def store_config (self, config_file):
        with open( config_file, "w" ) as config_fd:
            yaml.dump( self.config, config_fd, default_flow_style=False, default_style='|' )


    def _autodetect_euca_settings (self):
        if 'euca' not in self.config:
            self.config['euca'] = {}
        config = self.config['euca']
        for prop, env in EUCA_VAR_MAPS.items( ):
            value = os.environ.get( env, None )
            config[prop] = value

        for prop, env in EUCA_BLOB_VAR_MAPS.items( ):
            value = os.environ.get( env, None )
            if not os.path.exists( value ):
                continue
            with open( value, "rb" ) as f:
                value = f.read( )
            config[prop] = value


    def handle_config_euca (self, args):
        if args.autodetect:
            self._autodetect_euca_settings( )
        if 'euca' not in self.config:
            self.config['euca'] = {}
        config = self.config['euca']
        for key in EUCA_VAR_MAPS:
            value = getattr( args, key, None )
            if value is None: continue
            config[key] = value
        for key in EUCA_BLOB_VAR_MAPS:
            value = getattr( args, key, None )
            if value is None: continue
            with open( value, "rb" ) as f:
                value = f.read( )
            config[key] = value

    def handle_config_info(self, args):
        yaml.dump(self.config, sys.stdout, default_flow_style=False, default_style='|')

    def handle_config_registry (self, args):
        config_registry = {}
        if 'config' in self.config:
            config_registry = self.config['config']
        else:
            self.log.debug("Creating missing config registry")
            self.config['config'] = config_registry
        for cfg_entry in args.configs:
            key, value = cfg_entry.split("=")
            if key in config_registry:
                old_value = config_registry[key]
                self.log.info("Updating key %s (%s) with %s", key, old_value, value)
            config_registry[key] = value



    def get_config_handler (self, section):
        hndlr_name = "handle_config_%s" % section
        hndlr = getattr( self, hndlr_name, None )

        if hndlr is None:
            raise NotImplementedError( "Undefined config handler for section: %s", section )
        def _handler_wrapper (args):
            self.load_config( args.config_file )
            hndlr( args )
            self.store_config( args.config_file )
        return _handler_wrapper
