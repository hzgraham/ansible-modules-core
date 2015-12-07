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
module: kubernetes_namespace
short_description: Create, Delete or Modify a Kubernetes Namespace
version_added: "2.0"
author: "Jason DeTiberus <jdetiber@redhat.com>"
description:
   - Create, Delete or Modify a Kubernetes Namespace
options:
   namespace:
     description:
        - Name that will be given to the namespace (metadata.name)
     required: false
     default: default
requirements:
   TODO
'''

EXAMPLES = '''

kubernetes_namespace:
  name: test
'''

def main():
    argument_spec = kubernetes_argument_spec(
        namespace = dict(required=True),
        state     = dict(default='present', choices=['absent', 'present'])
    )
    module_kwargs = kubernetes_module_kwargs(
        mutually_exclusive=[],
        required_together=[],
        required_one_of=[]
    )
    module = AnsibleModule(argument_spec, **module_kwargs)

    kube_client = KubernetesClient(module)

    state = module.params['state']

    namespace = kube_client.get_namespace()

    changed = False

    if state == 'present':
        if namespace is not None:
            module.exit_json(changed=changed)
        else:
            result = kube_client.create_namespace()
            changed = True
            module.exit_json(changed=changed, result=result)
    elif state == 'absent':
        if namespace is not None:
            result = kube_client.delete_namespace()
            changed = True
            module.exit_json(changed=changed, result=result)
        else:
            module.exit_json(changed=changed)

# this is magic, see lib/ansible/module_common.py
from ansible.module_utils.basic import *
from ansible.module_utils.urls import *
from ansible.module_utils.kubernetes import *
if __name__ == '__main__':
    main()
