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

import argparse
from sct.config import CONFIG_FILE, argparse_euca_helper
from sct.config import ConfigFile
from sct.cloud import CloudController


class ControllerWrapper( object ):
    def __init__ (self, klass):
        self.klass = klass
        self.klassInst = None

    def __getattr__ (self, item):
        def _config_wrapper (cfg):
            if self.klassInst is None:
                self.klassInst = self.klass( cfg )

            if not hasattr( self.klassInst, item ):
                raise NameError( "Name %s is not defined" % item )
            func = getattr( self.klassInst, item )

            def __wrapper (args):
                cfg.load_config( args.config_file )
                self.klassInst.init( )
                if args.disable_ssl_check:
                    self.klassInst.disable_ssl_check( )
                func( args )
                cfg.store_config( args.config_file )

            return __wrapper

        return _config_wrapper


cc = ControllerWrapper( CloudController )
#print cc.list_nodes

def main ():
    parser = argparse.ArgumentParser(
        description="SCAPE Cloud Toolkit",
        epilog="(c) Universitatea de Vest din Timisoara"
    )

    cfg = ConfigFile( )
    parser.add_argument( "--config-file",
                         type=str,
                         default=CONFIG_FILE,
                         help="Specify the config file" )
    subparsers = parser.add_subparsers( title='Subcommands',
                                        description='valid subcommands',
                                        help='' )
    cloud_config_parser = subparsers.add_parser( 'cloud-config' )
    cloud_info_parser = subparsers.add_parser( 'cloud-info', help="Set Cloud Configuration Params" )
    euca_parser = subparsers.add_parser( 'euca' )

    ############## Cloud Config #################
    cloud_config_subparsers = cloud_config_parser.add_subparsers( title="Subcomands",
                                                                  description="Valid subcomands",
                                                                  help="Valid subconfiguration commands" )
    euca_config_parser = cloud_config_subparsers.add_parser( 'euca' )
    euca_config_parser.add_argument( "--autodetect",
                                     action="store_true",
                                     help="Autodetect eucalyptus settings" )
    argparse_euca_helper( euca_config_parser )
    euca_config_parser.set_defaults( func=cfg.get_config_handler( 'euca' ) )

    ############# Euca Commands ##################
    euca_parser.add_argument( "--disable-ssl-check", "-S", action="store_true", default=False )
    euca_subparsers = euca_parser.add_subparsers( title="Subcommands" )
    euca_list_nodes_parser = euca_subparsers.add_parser( "list-nodes" )
    euca_list_nodes_parser.set_defaults( func=cc.list_nodes( cfg ) )
    euca_create_node_parser = euca_subparsers.add_parser( "add-node" )
    euca_create_node_parser.set_defaults( func=cc.add_node( cfg ) )
    euca_test_parser = euca_subparsers.add_parser( "test" )



    ###### Handle
    args = parser.parse_args( )
    if hasattr( args, 'func' ):
        args.func( args )
