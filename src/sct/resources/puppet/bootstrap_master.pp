class { 'puppetdb':
  listen_address => "$ec2_local_ipv4"
}

class {'puppetdb::master::config': }


