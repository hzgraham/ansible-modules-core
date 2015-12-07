#!/usr/bin/python
# coding: utf-8 -*-

# Copyright (c) 2015 Red Hat, Inc
#
# This module is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.


DOCUMENTATION = '''
---
module: kubernetes_pod
short_description: Create, Delete or Modify a Kubernetes Pod
version_added: "2.0"
author: "Jason DeTiberus <jdetiber@redhat.com>"
description:
   - Create, Delete or Modify a Kubernetes Pod
options:
   name:
     description:
        - Name that will be given to the pod (metadata.name)
     required: true
     default: None
   containers:
     description:
        - List of containers specifying name, image and other options.
     required: false
     default: []
requirements:
   TODO
'''

EXAMPLES = '''

kubernetes_pod:
  name: nginx
  containers:
  - name: nginx
    image: nginx
    ports:
    - containerPort: 8080

'''

def main():
    argument_spec = kubernetes_argument_spec(
        name                            = dict(required=True),
        state                           = dict(default='present', choices=['absent', 'present']),
        containers                      = dict(default=[]),
        labels                          = dict(default=[]),
    )
    module_kwargs = kubernetes_module_kwargs(
        mutually_exclusive=[],
        required_together=[],
        required_one_of=[]
    )
    module = AnsibleModule(argument_spec, **module_kwargs)

    kube_client = KubernetesClient(module)

    state = module.params['state']
    name = module.params['name']
    containers = module.params['containers']
    labels = module.params['labels']

    pod = kube_client.get_pod(name)

    changed = False

    if state == 'present':
        if pod is not None:
            module.exit_json(changed=changed, name=name, containers=containers, labels=labels)
        else:
            kube_client.create_pod(name=name, containers=containers, labels=labels)
            changed = True
            module.exit_json(changed=changed, name=name, containers=containers, labels=labels)
    elif state == 'absent':
        if pod is not None:
            result = kube_client.delete_pod(name)
            changed = True
            module.exit_json(changed=changed, name=name, result=result)
        else:
            module.exit_json(changed=changed, name=name)

# this is magic, see lib/ansible/module_common.py
from ansible.module_utils.basic import *
from ansible.module_utils.urls import *
from ansible.module_utils.kubernetes import *
if __name__ == '__main__':
    main()
