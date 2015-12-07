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
module: kubernetes_service
short_description: Create, Delete or Modify a Kubernetes Service
version_added: "2.0"
author: "Andrew Butcher <abutcher@redhat.com>"
description:
   - Create, Delete or Modify a Kubernetes Service
options:
   name:
     description:
        - Name that will be given to the service (metadata.name)
     required: true
     default: None
   selector:
     description:
        - A dictionary representing a key, value pair.
     required: false
     default: {}
  ports:
     description:
        - A list of ports specifying protocol, port and targetPort.
     required: false
     default: []
requirements:
   TODO
'''

EXAMPLES = '''

kubernetes_service:
  name: nginx
  selector:
    name: nginx
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080

'''

def main():
    argument_spec = kubernetes_argument_spec(
        name                            = dict(required=True),
        state                           = dict(default='present', choices=['absent', 'present']),
        selector                        = dict(default={}),
        ports                           = dict(default=[])
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
    selector = module.params['selector']
    ports = module.params['ports']

    service = kube_client.get_service(name)

    changed = False

    if state == 'present':
        if service is not None:
            module.exit_json(changed=changed, name=name)
        else:
            kube_client.create_service(name=name, selector=selector, ports=ports)
            changed = True
            module.exit_json(changed=changed, name=name)
    elif state == 'absent':
        if service is not None:
            kube_client.delete_service(name)
            changed = True
            module.exit_json(changed=changed, name=name)
        else:
            module.exit_json(changed=changed, name=name)

# this is magic, see lib/ansible/module_common.py
from ansible.module_utils.basic import *
from ansible.module_utils.urls import *
from ansible.module_utils.kubernetes import *
if __name__ == '__main__':
    main()
