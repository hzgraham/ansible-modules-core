#!/usr/bin/python
# Copyright 2013 Google Inc.
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: gce
version_added: "1.4"
short_description: create or terminate GCE instances
description:
     - Creates or terminates Google Compute Engine (GCE) instances.  See
       U(https://cloud.google.com/products/compute-engine) for an overview.
       Full install/configuration instructions for the gce* modules can
       be found in the comments of ansible/test/gce_tests.py.
options:
  image:
    description:
       - image string to use for the instance
    required: false
    default: "debian-7"
    aliases: []
  instance_names:
    description:
      - a comma-separated list of instance names to create or destroy
    required: false
    default: null
    aliases: []
  machine_type:
    description:
      - machine type to use for the instance, use 'n1-standard-1' by default
    required: false
    default: "n1-standard-1"
    aliases: []
  metadata:
    description:
      - a hash/dictionary of custom data for the instance; '{"key":"value",...}'
    required: false
    default: null
    aliases: []
  service_account_email:
    version_added: 1.5.1
    description:
      - service account email
    required: false
    default: null
    aliases: []
  pem_file:
    version_added: 1.5.1
    description:
      - path to the pem file associated with the service account email
    required: false
    default: null
    aliases: []
  project_id:
    version_added: 1.5.1
    description:
      - your GCE project ID
    required: false
    default: null
    aliases: []
  name:
    description:
      - identifier when working with a single instance
    required: false
    aliases: []
  network:
    description:
      - name of the network, 'default' will be used if not specified
    required: false
    default: "default"
    aliases: []
  persistent_boot_disk:
    description:
      - if set, create the instance with a persistent boot disk
    required: false
    default: "false"
    aliases: []
  disks:
    description:
      - a list of persistent disks to attach to the instance; a string value gives the name of the disk; alternatively, a dictionary value can define 'name' and 'mode' ('READ_ONLY' or 'READ_WRITE'). The first entry will be the boot disk (which must be READ_WRITE).
    required: false
    default: null
    aliases: []
    version_added: "1.7"
  state:
    description:
      - desired state of the resource
    required: false
    default: "present"
    choices: ["active", "present", "absent", "deleted"]
    aliases: []
  tags:
    description:
      - a comma-separated list of tags to associate with the instance
    required: false
    default: null
    aliases: []
  zone:
    description:
      - the GCE zone to use
    required: true
    default: "us-central1-a"
    aliases: []
  ip_forward:
    version_added: "1.9"
    description:
      - set to true if the instance can forward ip packets (useful for gateways)
    required: false
    default: "false"
    aliases: []
  external_ip:
    version_added: "1.9"
    description:
      - type of external ip, ephemeral by default
    required: false
    default: "ephemeral"
    aliases: []
  disk_auto_delete:
    version_added: "1.9"
    description:
      - if set boot disk will be removed after instance destruction
    required: false
    default: "true"
    aliases: []

requirements: [ "libcloud" ]
notes:
  - Either I(name) or I(instance_names) is required.
author: Eric Johnson <erjohnso@google.com>
'''

EXAMPLES = '''
# Basic provisioning example.  Create a single Debian 7 instance in the
# us-central1-a Zone of n1-standard-1 machine type.
- local_action:
    module: gce
    name: test-instance
    zone: us-central1-a
    machine_type: n1-standard-1
    image: debian-7

# Example using defaults and with metadata to create a single 'foo' instance
- local_action:
    module: gce
    name: foo
    metadata: '{"db":"postgres", "group":"qa", "id":500}'


# Launch instances from a control node, runs some tasks on the new instances,
# and then terminate them
- name: Create a sandbox instance
  hosts: localhost
  vars:
    names: foo,bar
    machine_type: n1-standard-1
    image: debian-6
    zone: us-central1-a
    service_account_email: unique-email@developer.gserviceaccount.com
    pem_file: /path/to/pem_file
    project_id: project-id
  tasks:
    - name: Launch instances
      local_action: gce instance_names={{names}} machine_type={{machine_type}}
                    image={{image}} zone={{zone}} service_account_email={{ service_account_email }}
                    pem_file={{ pem_file }} project_id={{ project_id }}
      register: gce
    - name: Wait for SSH to come up
      local_action: wait_for host={{item.public_ip}} port=22 delay=10
                    timeout=60 state=started
      with_items: {{gce.instance_data}}

- name: Configure instance(s)
  hosts: launched
  sudo: True
  roles:
    - my_awesome_role
    - my_awesome_tasks

- name: Terminate instances
  hosts: localhost
  connection: local
  tasks:
    - name: Terminate instances that were previously launched
      local_action:
        module: gce
        state: 'absent'
        instance_names: {{gce.instance_names}}

'''

import sys

try:
    from libcloud.compute.types import Provider
    from libcloud.compute.providers import get_driver
    from libcloud.common.google import GoogleBaseError, QuotaExceededError, \
            ResourceExistsError, ResourceInUseError, ResourceNotFoundError
    _ = Provider.GCE
except ImportError:
    print("failed=True " + \
        "msg='libcloud with GCE support (0.13.3+) required for this module'")
    sys.exit(1)

try:
    from ast import literal_eval
except ImportError:
    print("failed=True " + \
        "msg='GCE module requires python's 'ast' module, python v2.6+'")
    sys.exit(1)

class GCENodeManager(object):
    def __init__(self, module):
        self.validate_params(module.params)
        self.module = module
        self.gce = gce_connect(module)

    def get_image(self):
        image_name = self.module.params.get('image')
        if image_name is not None:
            return self.gce.ex_get_image(image_name)
        return None

    def get_network(self):
        network_name = self.module.params.get('network')
        if network_name is not None:
            return self.gce.ex_get_network(network_name)
        return None

    def get_size(self):
        size_name = self.module.params.get('machine_type')
        if size_name is not None:
            return self.gce.ex_get_size(size_name)
        return None

    def get_zone(self):
        zone_name = self.module.params.get('zone')
        if zone_name is not None:
            return self.gce.ex_get_zone(zone_name)
        return None

    # Try to convert the user's metadata value into the format expected
    # by GCE.  First try to ensure user has proper quoting of a
    # dictionary-like syntax using 'literal_eval', then convert the python
    # dict into a python list of 'key' / 'value' dicts.  Should end up
    # with:
    # [ {'key': key1, 'value': value1}, {'key': key2, 'value': value2}, ...]
    def cleanup_metadata(self, metadata):
        if metadata:
            try:
                md = literal_eval(str(metadata))
                if not isinstance(md, dict):
                    raise ValueError('metadata must be a dict')
            except ValueError, e:
                self.module.fail_json(msg="bad metadata: %s" % str(e), changed=False)
            except SyntaxError, e:
                self.module.fail_json(msg='bad metadata syntax', changed=False)

            items = []
            for k,v in md.items():
                items.append({"key": k, "value": v})

            metadata = {'items': items}
        return metadata

    def execute(self):
        state = self.module.params.get('state')
        lc_zone = self.get_zone()
        name = self.module.params.get('name')

        instance_names = []
        param_inames = self.module.params.get('instance_names')
        if isinstance(param_inames, list):
            instance_names = param_inames
        elif isinstance(param_inames, str):
            instance_names = [n.strip() for n in param_inames.split(',')]

        if state in ['absent', 'deleted']:
            # TODO: support deleting multiple instances with ex_destroy_multiple_nodes
            # TODO: support deleting multiple instances by tag
            # TODO: support one or more instances by instance ids or other
            if name is not None:
                # We are deleting a single named instance
                return self.delete_instance_by_name(name, lc_zone)
            else:
                # We are deleting multiple named instances specified by
                # instance_names
                return self.delete_instances_by_names(instance_names, lc_zone)
        elif state in ['stopped']:
            # TODO: stop one or more instances  based on the
            # name, instance_names params and current instance states
            self.module.fail_json(msg='stop not implemented yet', changed=False)
        elif state in ['running', 'active', 'present']:
            lc_image = self.get_image()
            lc_network = self.get_network()
            lc_machine_type = self.get_size()

            # These variables all have default values but check just in case
            if None in [ lc_image, lc_network, lc_machine_type, lc_zone ]:
                self.module.fail_json(
                    msg='Missing required create instance variable.',
                    changed=False
                )

            metadata = self.cleanup_metadata(self.module.params.get('metadata'))

            if name is not None:
                count = self.module.params.get('count')
                exact_count = self.module.params.get('exact_count')

                if count is not None:
                    # We are creating count number of instances with basename
                    # name
                    instance_count = self.module.params['count']
                    return self.create_instances_by_count(name, instance_count,
                                                          lc_image,
                                                          lc_machine_type,
                                                          lc_network,
                                                          lc_zone, metadata)

                elif exact_count is not None:
                    exact_count = self.module.params
                    # TODO: verify exact_count vs running instances and
                    # delete/create instances as needed
                    self.module.fail_json(msg='exact_count not implemented yet', changed=False)

                else:
                    # We are creating a single named instance
                    return self.create_instance_by_name(name, lc_image,
                                                        lc_machine_type,
                                                        lc_network, lc_zone,
                                                        metadata)
            else:
                # We are creating multiple named instances specified by
                # instance_names
                return self.create_instances_by_names(instance_names, lc_image,
                                                      lc_machine_type,
                                                      lc_network, lc_zone,
                                                      metadata)

    def validate_params(self, params):
        if 'zone' not in params:
            self.module.fail_json(msg='Must specify a "zone"', changed=False)

    def delete_instance_by_name(self, name, lc_zone):
        changed = False
        inst = None
        try:
            inst = self.gce.ex_get_node(name, lc_zone)
        except ResourceNotFoundError:
            pass
        except Exception, e:
             self.module.fail_json(msg=unexpected_error_msg(e), changed=False)

        if inst:
            self.gce.destroy_node(inst)
            changed = True

        results = {
            'state': self.module.params.get('state'),
            'changed': changed,
            'zone': lc_zone.name,
            'name': name
        }
        return results

    def delete_instances_by_names(self, instance_names, lc_zone):
        changed = False

        deleted_instances = []

        for name in instance_names:
            r = self.delete_instance_by_name(name, lc_zone)
            if r['changed']:
                changed = True
                deleted_instances.append(r['name'])

        results = {
            'state': self.module.params.get('state'),
            'changed': changed,
            'zone': lc_zone.name,
            'instance_names': deleted_instances
        }
        return results

    def stop_instances(self):
        module.fail_json(msg='stop_instances not implemented yet', changed=False)

    def start_instances(self):
        module.fail_json(msg='start_instances not implemented yet', changed=False)

    def create_instance_by_name(self, name, lc_image, lc_machine_type, lc_network,
                                lc_zone, metadata):
        changed = False

        # TODO: Convert old style disk arrays to a valid ex_disks_gce_struct
        #       - array of names
        #       - array of dicts: { 'name': <name>, 'mode': <mode> }

        disks = self.module.params.get('disks')
        boot_disk = self.module.params.get('boot_disk')
        disk_auto_delete = self.module.params.get('disk_auto_delete')
        disk_type = self.module.params.get('disk_type')
        use_existing_disk = self.module.params.get('use_existing_disk')
        tags = self.module.params.get('tags')
        nics = self.module.params.get('nics')
        ip_forward = self.module.params.get('ip_forward')
        external_ip = self.module.params.get('external_ip')
        if external_ip == 'none':
            external_ip = None

        try:
            inst = self.gce.create_node(
                name, lc_machine_type, lc_image, location=lc_zone,
                ex_network=lc_network, ex_tags=tags, ex_metadata=metadata,
                ex_boot_disk=boot_disk, use_existing_disk=use_existing_disk,
                external_ip=external_ip, ex_disk_type=disk_type,
                ex_disk_auto_delete=disk_auto_delete,
                ex_can_ip_forward=ip_forward, ex_disks_gce_struct=disks,
                ex_nic_gce_struct=nics
            )
            changed = True
        except ResourceExistsError:
            inst = self.gce.ex_get_node(name, lc_zone)
        except GoogleBaseError, e:
            self.module.fail_json(
                msg='Unexpected error attempting to create '
                    'instance %s, error: %s' % (name, e.value)
            )

        results = {
            'state': self.module.params.get('state'),
            'changed': changed,
            'zone': lc_zone.name,
            'instance_data': [self.get_instance_info(inst)],
            'name': name
        }
        return results

    def create_instances_by_names(self, instance_names, lc_image,
                                  lc_machine_type, lc_network, lc_zone,
                                  metadata):
        changed = False
        created_data=[]
        created_names=[]
        for name in instance_names:
            r = self.create_instance_by_name(name, lc_image, lc_machine_type,
                                             lc_network, lc_zone, metadata)
            if r['changed']:
                changed = True
            created_data.append(r['instance_data'][0])
            created_names.append(r['name'])

        results = {
            'state': self.module.params.get('state'),
            'changed': changed,
            'zone': lc_zone.name,
            'instance_data': created_data,
            'instance_names': created_names
        }
        return results

    def create_instances_by_count(self, name, instance_count, lc_image,
                                  lc_machine_type, lc_network, lc_zone, metadata):
        # current method returns:
        #     { state: present, changed: changed, zone: zone, instance_data, instance_names: [] }
        #     { state: present, changed: changed, zone: zone, instance_data, name: [] }
        #
        # TODO: implement using ex_create_multiple_nodes
        self.module.fail_json(msg='create_instances_by_count not implemented yet', changed=False, parmas=self.module.params)

    def get_instance_info(self, inst):
        """Retrieves instance information from an instance object and returns it
        as a dictionary.

        """
        metadata = {}
        if 'metadata' in inst.extra and 'items' in inst.extra['metadata']:
            for md in inst.extra['metadata']['items']:
                metadata[md['key']] = md['value']

        try:
            netname = inst.extra['networkInterfaces'][0]['network'].split('/')[-1]
        except:
            netname = None
        if 'disks' in inst.extra:
            disk_names = [disk_info['source'].split('/')[-1]
                          for disk_info
                          in sorted(inst.extra['disks'],
                                    key=lambda disk_info: disk_info['index'])]
        else:
            disk_names = []

        if len(inst.public_ips) == 0:
            public_ip = None
        else:
            public_ip = inst.public_ips[0]


        return({
            'image': inst.image is not None and inst.image.split('/')[-1] or None,
            'disks': disk_names,
            'machine_type': inst.size,
            'metadata': metadata,
            'name': inst.name,
            'network': netname,
            'private_ip': inst.private_ips[0],
            'public_ip': public_ip,
            'status': ('status' in inst.extra) and inst.extra['status'] or None,
            'tags': ('tags' in inst.extra) and inst.extra['tags'] or [],
            'zone': ('zone' in inst.extra) and inst.extra['zone'].name or None,
       })


def main():
    module = AnsibleModule(
        argument_spec = dict(
            image = dict(default='debian-7'),
            instance_names = dict(),
            machine_type = dict(default='n1-standard-1'),
            metadata = dict(),
            name = dict(),
            count = dict(type='int'),
            exact_count = dict(type='int'), # TODO: update docs for this param
            count_tag = dict(), # TODO: update docs for this param
            wait = dict(type='bool', default=False),
            network = dict(default='default'),
            disks = dict(type='list'), # TODO: update docs for this param
            state = dict(choices=['active', 'present', 'running', 'stopped', 'absent', 'deleted'],
                    default='present'), # TODO: update docs for this param
            tags = dict(type='list'),
            zone = dict(default='us-central1-a'),
            service_account_email = dict(),
            pem_file = dict(),
            project_id = dict(),
            ip_forward = dict(type='bool', default=False),
            external_ip = dict(choices=['ephemeral', 'none'],
                    default='ephemeral'),
            boot_disk = dict(), # TODO: update docs for this param
            disk_auto_delete = dict(type='bool', default=True),
            disk_type = dict(choices=['pd-standard', 'pd-ssd'],
                    default='pd-standard'), # TODO: update docs for this param
            use_existing_disk = dict(type='bool', default=True), # TODO: update docs for this param
            nics = dict(type='list') # TODO: update docs for this param
        ),
        mutually_exclusive = [
            ['name', 'instance_names'],
            ['disks', 'disk_auto_delete'],
            ['disks', 'boot_disk'],
            ['disks', 'disk_type'],
            ['disks', 'use_existing_disk'],
            ['exact_count', 'count'],
            ['exact_count', 'instance_names'],
            ['instance_names', 'count'],
            ['nics', 'external_ip'],
            ['nics', 'network']
        ],
        required_together = [['exact_count', 'count_tag']],
        required_one_of = [['name', 'instance_names']],
    )

    node_mgr = GCENodeManager(module)

    module.exit_json(**(node_mgr.execute()))

# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.gce import *

main()
