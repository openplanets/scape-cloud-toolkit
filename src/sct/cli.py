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

import argparse
import os
import sys
from logging.config import dictConfig

import yaml
import pkg_resources

from sct.config import CONFIG_FILE, argparse_euca_helper
from sct.config import ConfigFile
from sct.cloud import CloudController


class ControllerWrapper(object):
    def __init__(self, klass, klassInst=None):
        self.klass = klass
        self.klassInst = klassInst
        self.config = None

    def __getattr__(self, item):
        class __ConfigWrapper__(object):
            def __init__(self, outer_instance, outer_item):
                self.outer_instance = outer_instance
                self.outer_item = outer_item

            def __getattr__(self, item):
                if not hasattr(self.outer_instance.klassInst, self.outer_item):
                    raise NameError("Name %s is not defined in %s" % (item, self.outer_item))
                outer_obj = getattr(self.outer_instance.klassInst, self.outer_item)

                def __cfg_wrapper(cfg):
                    inner_cc = ControllerWrapper(outer_obj.__class__, outer_obj)

                    def __args_wrapper(args):
                        cfg.load_config(args.config_file)
                        self.outer_instance.klassInst.init()
                        passed_args = self._filter_args(args)
                        if args.disable_ssl_check:
                            outer_obj.disable_ssl_check()
                        print getattr(outer_obj, item)(**passed_args)
                        cfg.store_config(args.config_file)

                    return __args_wrapper

                return __cfg_wrapper

            def _filter_args(self, args):
                passed_args = {}
                for arg in dir(args):
                    if arg.startswith("_") or callable(getattr(args, arg)):
                        continue
                    if arg in ["config_file", "verbose", "logging_config", "disable_ssl_check"]:
                        continue
                    passed_args[arg] = getattr(args, arg)
                return passed_args

            def __call__(self, cfg):
                outer_instance = self.outer_instance
                if outer_instance.klassInst is None:
                    outer_instance.klassInst = outer_instance.klass(cfg)

                if not hasattr(outer_instance.klassInst, item):
                    raise NameError("Name %s is not defined" % item)

                inner_attrib = getattr(outer_instance.klassInst, item)

                def __func_wrapper(args):
                    passed_args = self._filter_args(args)

                    cfg.load_config(args.config_file)
                    outer_instance.klassInst.init()
                    if args.disable_ssl_check:
                        outer_instance.klassInst.disable_ssl_check()
                    result = inner_attrib(**passed_args)
                    cfg.store_config(args.config_file)
                    yaml.dump(result, sys.stdout, default_flow_style=False)

                return __func_wrapper

        return __ConfigWrapper__(self, item)


cc = ControllerWrapper(CloudController)


def main():
    parser = argparse.ArgumentParser(
        description="SCAPE Cloud Toolkit",
        epilog="(c) Universitatea de Vest din Timisoara"
    )

    cfg = ConfigFile()
    parser.add_argument("--config-file",
                        type=str,
                        default=CONFIG_FILE,
                        help="Specify the config file")
    parser.add_argument('--verbose', '-v', action='count', default=None,
                        help="The verbosity level. More v's means more logging")
    parser.add_argument('--logging-config', type=str, default=None, help="Alternate logging config file. (YAML)")
    subparsers = parser.add_subparsers(title='Subcommands',
                                       description='valid subcommands',
                                       help='')
    cloud_config_parser = subparsers.add_parser('cloud-config')
    cloud_info_parser = subparsers.add_parser('cloud-info', help="Set Cloud Configuration Params")
    cloud_info_parser.set_defaults(func=cfg.get_config_handler("info"))
    euca_parser = subparsers.add_parser('euca')
    cluster_parser = subparsers.add_parser("cluster")

    ############## Cloud Config #################
    cloud_config_subparsers = cloud_config_parser.add_subparsers(title="Subcomands",
                                                                 description="Valid subcomands",
                                                                 help="Valid subconfiguration commands")
    euca_config_parser = cloud_config_subparsers.add_parser('euca')
    registry_config_parser = cloud_config_subparsers.add_parser('registry')

    euca_config_parser.add_argument("--autodetect",
                                    action="store_true",
                                    help="Autodetect eucalyptus settings")
    argparse_euca_helper(euca_config_parser)
    euca_config_parser.set_defaults(func=cfg.get_config_handler('euca'))

    registry_config_parser.add_argument("configs", metavar="entry", type=str, nargs='+', default=[],
                                        help="Configuration Entry (key=value)")
    registry_config_parser.set_defaults(func=cfg.get_config_handler("registry"))

    ############# Euca Commands ##################
    euca_parser.add_argument("--disable-ssl-check", "-S", action="store_true", default=False)
    euca_subparsers = euca_parser.add_subparsers(title="Subcommands", description="Valid EUCA Commands")

    euca_list_nodes_parser = euca_subparsers.add_parser("list-nodes", help="List registered nodes")
    euca_list_nodes_parser.set_defaults(func=cc.list_nodes(cfg))

    euca_list_images_parser = euca_subparsers.add_parser("list-images")
    euca_list_images_parser.set_defaults(func=cc.list_images(cfg))

    euca_list_sizes_parser = euca_subparsers.add_parser("list-sizes")
    euca_list_sizes_parser.set_defaults(func=cc.list_sizes(cfg))

    euca_create_node_parser = euca_subparsers.add_parser("create-node")
    euca_create_node_parser.add_argument("--image", type=str, required=True, help="Image used for creating the node")
    euca_create_node_parser.add_argument("--size", type=str, required=True, help="Size used for the created image")
    euca_create_node_parser.add_argument("--name", type=str, required=True, help="Name for the new node")
    euca_create_node_parser.add_argument("--network-setup-timeout", type=int, required=False, default=120,
                                         help="Number of seconds to wait for the Cloud to setup the private network.")
    euca_create_node_parser.add_argument("--security-group", type=str, required=True, help="Name for the new node")
    euca_create_node_parser.add_argument("--keypair-name", type=str, required=False,
                                         help="The name of the keypair to use")
    euca_create_node_parser.add_argument("--auto-allocate-address", action="store_true", required=False, default=False,
                                         help="Auto allocate address")
    euca_create_node_parser_exclusive = euca_create_node_parser.add_mutually_exclusive_group()
    euca_create_node_parser_exclusive.add_argument("--userdata", type=str, default=None,
                                                   help="Userdata to provide to the machine")
    euca_create_node_parser_exclusive.add_argument("--userdata-file", type=str, default=None,
                                                   help="Path to the file hosting userdata")
    euca_create_node_parser.set_defaults(func=cc.create_node(cfg))

    euca_terminate_node_parser = euca_subparsers.add_parser("terminate-node")
    euca_terminate_node_parser.add_argument("--instance-id", type=str, required=True,
                                            help="The node that should be terminated")
    euca_terminate_node_parser.set_defaults(func=cc.terminate_node(cfg))

    euca_create_security_group = euca_subparsers.add_parser("create-security-group")
    euca_create_security_group.add_argument("--name", type=str, required=True, help="Name of the security group")
    euca_create_security_group.add_argument("--description", type=str, required=False,
                                            help="Description of the security group")
    euca_create_security_group.set_defaults(func=cc.create_security_group(cfg))

    euca_delete_security_group = euca_subparsers.add_parser("delete-security-group")
    euca_delete_security_group.add_argument("--name", type=str, required=True, help="Name of the security group")
    euca_delete_security_group.set_defaults(func=cc.delete_security_group(cfg))

    euca_list_security_groups = euca_subparsers.add_parser("list-security-groups")
    euca_list_security_groups.set_defaults(func=cc.list_security_groups(cfg))

    euca_authorize_security_groups = euca_subparsers.add_parser("authorize-security-group")
    euca_authorize_security_groups.add_argument("--name", type=str, required=True, help="Name of the security group")
    euca_authorize_security_groups.add_argument("--from-port", type=int, required=True,
                                                help="Starting port of the rule")
    euca_authorize_security_groups.add_argument("--to-port", type=int, required=False, help="End port of the rule")
    euca_authorize_security_groups.add_argument("--cidr-ip", type=str, required=False, default="0.0.0.0/0",
                                                help="Allow traffic for this IP address. Default 0.0.0.0/0")
    euca_authorize_security_groups.add_argument("--protocol", type=str, choices=("tcp", "udp", "icmp"), default="tcp",
                                                help="Applicable protocol")
    euca_authorize_security_groups.set_defaults(func=cc.authorize_security_group(cfg))

    euca_list_addresses = euca_subparsers.add_parser("list-addresses")
    euca_list_addresses.add_argument("--associated", action="store_true", default=False,
                                     help="Show only associated addresses")
    euca_list_addresses.set_defaults(func=cc.list_addresses(cfg))

    euca_list_addresses = euca_subparsers.add_parser("list-available-addresses")
    euca_list_addresses.set_defaults(func=cc.list_available_addresses(cfg))

    euca_allocate_address = euca_subparsers.add_parser("allocate-address")
    euca_allocate_address.set_defaults(func=cc.allocate_address(cfg))

    euca_associate_address = euca_subparsers.add_parser("associate-address")
    euca_associate_address.add_argument("--instance-id", type=str, required=True,
                                        help="The node to associate the address to")
    euca_associate_address.add_argument("--address", type=str, required=False,
                                        help="The address that should be allocated.")
    euca_associate_address.set_defaults(func=cc.associate_address(cfg))

    euca_create_keypair = euca_subparsers.add_parser("create-keypair")
    euca_create_keypair.add_argument("--name", type=str, required=True, help="The name of the keypair")
    euca_create_keypair.set_defaults(func=cc.create_keypair(cfg))

    euca_list_keypairs = euca_subparsers.add_parser("list-keypairs")
    euca_list_keypairs.add_argument("--name", type=str, required=False, default=None, help="The name of the keypair")
    euca_list_keypairs.set_defaults(func=cc.list_keypairs(cfg))

    euca_console_subparsers = euca_subparsers.add_parser("console")
    euca_console_subparsers.add_argument("--node-id", type=str, required=True, default=None,
                                         help="The instance id of the node")
    euca_console_subparsers.add_argument("--keypair-name", type=str, required=True, default=None,
                                         help="The name of the keypair to use")
    euca_console_subparsers.set_defaults(func=cc.console(cfg))

    ########### Cluster
    cluster_parser.add_argument("--disable-ssl-check", "-S", action="store_true", default=False)
    cluster_subparsers = cluster_parser.add_subparsers(title="Subcommands", description="Valid Cluster Commands")
    create_cluster_parser = cluster_subparsers.add_parser("create")
    create_cluster_parser.add_argument("--name", type=str, required=True, help="The name of the new cluster")
    create_cluster_parser.add_argument("--size", type=str, required=False, help="Size used for the management image")
    create_cluster_parser.add_argument("--image", type=str, required=False, help="Image used for the management image")
    create_cluster_parser.add_argument("--security-group", type=str, required=False,
                                       help="Security group used for the management image")
    create_cluster_parser.set_defaults(func=cc.cluster.create(cfg))
    delete_cluster_parser = cluster_subparsers.add_parser("delete")
    delete_cluster_parser.add_argument("--name", type=str, required=True, help="The name of the cluster to be deleted")
    delete_cluster_parser.set_defaults(func=cc.cluster.delete(cfg))
    console_cluster_parser = cluster_subparsers.add_parser("console")
    console_cluster_parser.add_argument("--node", type=str, required=False, help="The node to open the connection to")
    console_cluster_parser.add_argument("--name", type=str, required=True, help="The name of the cluster")
    console_cluster_parser.set_defaults(func=cc.cluster.console(cfg))


    ###### Handle
    args = parser.parse_args()

    # Setup logging
    import yaml

    if args.logging_config is None:
        logging_config_stream = pkg_resources.resource_stream(__name__, "logging.yaml")
        with logging_config_stream:
            loggingDict = yaml.load(logging_config_stream)
        if loggingDict is None:
            raise RuntimeError("Failed to find valid logging config file at expected location")
        if 'version' not in loggingDict:
            loggingDict['version'] = 1

        if args.verbose is not None:
            if args.verbose > 4:
                log_level = 10
            else:
                log_level = 50 - args.verbose * 10
            loggingDict["handlers"]["console"]["level"] = log_level
    else:
        if not os.path.exists(args.logging_config):
            print >> sys.stderr, "Could not find alternate logging file at: %s" % args.logging_config
            sys.exit(1)
        with open(args.logging_config) as f:
            loggingDict = yaml.load(f)

    dictConfig(loggingDict)
    if hasattr(args, 'func'):
        args.func(args)
