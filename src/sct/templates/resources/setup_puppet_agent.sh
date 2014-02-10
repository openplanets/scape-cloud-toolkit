#!/bin/sh

#
# This script registers 'puppet' in /etc/hosts
#
. /etc/profile

grep "puppet" /etc/hosts || echo "@puppetServer puppet" >> /etc/hosts
