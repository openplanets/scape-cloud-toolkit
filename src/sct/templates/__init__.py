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



from sct.templates.hadoop import HadoopServer, HadoopWorker

TEMPLATES = {
    'hadoop-server': {
        'max-node-count': 1,
        'cloudinit': HadoopServer
    },
    'hadoop-worker': {
        'max-node-count': None,
        'cloudinit': HadoopWorker
    }
}

def get_available_templates():
    return TEMPLATES.keys()

def get_template(name):
    if name not in TEMPLATES:
        raise NameError("No such template %s" % name)
    else:
        return TEMPLATES.get(name)



