class { 'puppetdb':
  listen_address => "$ec2_local_ipv4"
}
class {'puppetdb::master::config': }
/*class {'dashboard':
  dashboard_ensure => 'present',
  dashboard_user => 'puppet-dbuser',
  dashboard_group => 'puppet-dbgroup',
  dashboard_password => 'changeme',
  dashboard_db => 'dashboard_prod',
  dashboard_charset => 'utf8',
  dashboard_site => $ec2_public_hostname,
  dashboard_port => '8087',
  mysql_root_pw => 'changemetoo',
  passenger => true,
}*/
