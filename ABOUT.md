
# Cloud Deployment Toolkit

## What does CDT do ?

Cloud Deployment Toolkit facilitates the deployment of various Scape software components on top of public or private (on-premises) clouds.

CDT achieves this by integrating technologies like:

* [Libcloud](https://libcloud.apache.org/): used for interfacing with the cloud services. Responsible for the creation of virtual machines or containers (depending on the cloud provider). It handles the initial bootstrapping of the virtual machines, installing the required packages and performing the specific configurations that allow the operation of the other CDT components (e.g. Puppet)
* [Puppet](http://puppetlabs.com/): Configuration management system responsible for the effective deployment of Scape components and tools.
* [Consul](http://www.consul.io/): Used for various addressing and configuration scenarios.

Scape developers can create deployment rules (effectively *Puppet recipes*) for their projects and publish them to the CDT Recipe GIT Repository, making them accessible to both CDT users and fellow developers. 

End users can use the CDT UI's for deploying Scape components without having the detailed know-how, promoting this way the adoption of Scape tools.
Based on the user interaction with the UI, CDT automatically creates the required computing resources (virtual machines) using [Libcloud](https://libcloud.apache.org/) and configures the machines based on user expected rules (using Puppet).

## What are the benefits for the end-user ?

* Deploys Scape components in various Clouds;
* Avoids vendor lock-in;
* Streamlines the deployment of Digital Preservation ;Environments by automatising tedious tasks;
* Preserves integrity and avoids incompatibilities;
* Enables easy extension for new packages;

## What is the intended audience?

CDT is aimed mainly for:

* Institutions operating data centres;
* System administrators;
* Digital preservation specialists;
* Users having minimal IT skills willing to deploy production ready Scape components;

## Examples

Although migrating library applications to Cloud environment is not an easy task, many libraries are interested in using Cloud infrastructure services broadly across their businesses, whether it is about a Public, Private or Hybrid Cloud. 

One of the migration expectations is the scalability of digital preservation architectures in Cloud environments. In real-life setups, digital preservation environments require are complex systems comprising multiple software components that need to seamlessly work together. For example, the SCAPE Execution Platform is built on top of Apache Hadoop, usually preservation components are implemented as Taverna workflows and are using a plethora of tools for characterisation, migration of QA tasks. All these need to be consistently deployed on all the nodes of the infrastructure. When these nodes are a mix of physical machines, virtual machine on private cloud and virtual machines provisioned from public clouds, the task of installation and configuration of required software packages on the nodes becomes a complex, tedious and error-prone one.

This is where Cloud Deployment Toolkit comes in! It makes your life easier allowing your to easily deploy and monitor your tools on a hybrid infrastructure.

## Authors

* Marian NEAGUL / UVT marian@info.uvt.ro
* Adrian SPĂTARU / UVT  spataru.florin@info.uvt.ro

## Publications
* Pop D, Petcu D, Neagul M - On Cloud Deployment of Digital Preservation Environments, Proc. of JCDL 2014, London, September 2014

## Credits
     
    This work was partially supported by the SCAPE project. 
    The SCAPE project is co-funded by the European Union under
    FP7ICT-2009.4.1 (Grant Agreement number 270137)


