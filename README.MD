# SCAPE Cloud Toolkit


## IMPORTANT

Please open a ticket for any kind of bug or issue you find. The issue tracker is at [Bitbucket](https://bitbucket.org/scapeuvt/scape-cloud-toolkit/issues?status=new&status=open)

## Installation

In case you have an eucalyptus instance that does use "Private Only Addressing" you need to use a patched version
of libcloud from https://github.com/mneagul/libcloud

1. Create a new virtual env for the project:
  `virtualenv --no-site-packages ~/scape`
2. Clone the code from bitbucket/github: `git clone https://bitbucket.org/scapeuvt/scape-cloud-toolkit.git`
3. Change to the *scape-cloud-toolkit* directory
4. Register the code to the *virtualenv* defined before: `~/scape/bin/python setup.py develop`
5. At this point you can use this tool by calling: `~/scape/bin/sct-cli`



## Configuration


Before proceding with the **SCAPE Cloud Toolkit** you have to setup you credentials. This can be accomplished in two ways: automatic or manual.

### Automatically
1. Load the *eucarc* file: `. ~/euca/eucarc` (change depending on the location of eucarc)
2. Call the auto configuration command: `~/scape/bin/sct-cli -vvvvv cloud-config euca --autoconfig`

### Manual
See: `~/scape/bin/sct-cli -vvvvv cloud-config euca -h`




## Example


### Configure EUCA Credentials

`~/scape/bin/sct-cli -vvvvv cloud-config euca --autodetect`

### Create security Group

Create the security group that will be used in the next steps:

`~/scape/bin/sct-cli -vvvvv euca -S create-security-group --name=Test1`

Add some rules to it:

`~/scape/bin/sct-cli -vvvvv euca -S authorize-security-group --name=Test1 --from-port=22 --to-port=65000 --protocol=tcp`



### Set some global options
In this step we define some configuration defaults that will be used unless we specify them explicitly.

Define the default size of a image that will be used in a cluster:

`~/scape/bin/sct-cli -vvvvv cloud-config registry cluster.default_size=m1.medium`

Define the default image that will be used in a cluster:

`~/scape/bin/sct-cli -vvvvv cloud-config registry cluster.default_image=emi-50733A74A`

Define the default security group:

`~/scape/bin/sct-cli -vvvvv cloud-config registry cluster.default_security_group=Test1`

### Create the cluster

Create a new cluster named *SCAPE1*

`~/scape/bin/sct-cli -vvvvv cluster -S create --name=SCAPE1`

### Get an console to the manager

This allow you to establish automatically a conection to the management node:

`~/scape/bin/sct-cli -vvvvv cluster -S console --name=SCAPE1`

 

