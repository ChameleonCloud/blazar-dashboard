#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from unittest import mock

from django.urls import reverse

from blazar_dashboard import api
from blazar_dashboard import conf
from blazar_dashboard.content.leases import workflows as project_workflows
from blazar_dashboard.test import helpers as test

import logging
LOG = logging.getLogger(__name__)

INDEX_TEMPLATE = 'project/leases/index.html'
INDEX_URL = reverse('horizon:project:leases:index')
DETAIL_TEMPLATE = 'project/leases/detail.html'
DETAIL_URL_BASE = 'horizon:project:leases:detail'
CREATE_URL = reverse('horizon:project:leases:create')
CREATE_TEMPLATE = 'project/leases/create.html'
UPDATE_URL_BASE = 'horizon:project:leases:update'
UPDATE_TEMPLATE = 'project/leases/update.html'
FLAVORS_URL = reverse('horizon:project:leases:flavors')
FLAVOR_CALENDAR_URL = reverse('horizon:project:leases:flavor_calendar')
FLAVOR_CALENDAR_DATA_URL = reverse('horizon:project:leases:calendar_data',
                                   args=['flavor'])
HOST_CALENDAR_DATA_URL = reverse('horizon:project:leases:calendar_data',
                                 args=['host'])
VIRTUAL_INDEX_URL = reverse('horizon:project:virtual_leases:index')
VIRTUAL_CREATE_URL = reverse('horizon:project:virtual_leases:create')


class LeasesTests(test.TestCase):
    @mock.patch.object(api.client, 'lease_list')
    def test_index(self, lease_list):
        leases = self.leases.list()
        lease_list.return_value = leases

        res = self.client.get(INDEX_URL)

        lease_list.assert_called_once_with(
            test.IsHttpRequest(), all_tenants=False, marker=None, limit=20)
        self.assertTemplateUsed(res, INDEX_TEMPLATE)
        self.assertNoMessages(res)
        self.assertContains(res, 'lease-2')
        self.assertContains(res, 'lease-1')

    @mock.patch.object(api.client, 'lease_list')
    def test_index_no_leases(self, lease_list):
        leases = []
        lease_list.return_value = leases

        res = self.client.get(INDEX_URL)

        lease_list.assert_called_once_with(
            test.IsHttpRequest(), all_tenants=False, marker=None, limit=20)
        self.assertTemplateUsed(res, INDEX_TEMPLATE)
        self.assertNoMessages(res)
        self.assertContains(res, 'No items to display')

    @mock.patch.object(api.client, 'lease_list')
    def test_index_error(self, lease_list):
        lease_list.side_effect = self.exceptions.blazar

        res = self.client.get(INDEX_URL)

        lease_list.assert_called_once_with(
            test.IsHttpRequest(), all_tenants=False, marker=None, limit=20)
        self.assertTemplateUsed(res, INDEX_TEMPLATE)
        self.assertMessageCount(res, error=1)

    @mock.patch.object(api.client, 'nodes_in_lease')
    @mock.patch.object(api.client, 'lease_get')
    def test_lease_detail(self, lease_get, nodes_in_lease):
        lease = self.leases.get(name='lease-1')
        lease_get.return_value = lease
        nodes_in_lease.return_value = []

        res = self.client.get(reverse(DETAIL_URL_BASE, args=[lease['id']]))

        lease_get.assert_called_once_with(test.IsHttpRequest(), lease['id'])
        self.assertTemplateUsed(res, DETAIL_TEMPLATE)
        self.assertContains(res, 'lease-1')

    @mock.patch.object(api.client, 'lease_get')
    def test_lease_detail_error(self, lease_get):
        lease_get.side_effect = self.exceptions.blazar

        res = self.client.get(reverse(DETAIL_URL_BASE, args=['invalid']))

        lease_get.assert_called_once_with(test.IsHttpRequest(), 'invalid')
        self.assertTemplateNotUsed(res, DETAIL_TEMPLATE)
        self.assertMessageCount(error=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @mock.patch.object(api.client, 'compute_host_available')
    @mock.patch.object(api.client, 'lease_list')
    @mock.patch.object(api.client, 'lease_create')
    def test_create_lease_host_reservation(self, lease_create, lease_list,
                                           compute_host_available):
        new_lease = self.leases.get(name='lease-1')
        lease_list.return_value = []
        compute_host_available.return_value = 5
        lease_create.return_value = new_lease
        form_data = {
            'name': 'lease-1',
            'start_date': '2030-06-27',
            'start_time': '18:00',
            'end_date': '2030-06-30',
            'end_time': '18:00',
            'with_computehost': True,
            'min_hosts': 1,
            'max_hosts': 1,
            'criteria-computehost_resource_properties': 'vcpus >= 2',
        }

        res = self.client.post(CREATE_URL, form_data)

        lease_create.assert_called_once_with(
            test.IsHttpRequest(),
            'lease-1',
            '2030-06-27 18:00',
            '2030-06-30 18:00',
            [
                {
                    'min': 1,
                    'max': 1,
                    'hypervisor_properties': '',
                    'resource_properties': '[">=","$vcpus","2"]',
                    'resource_type': 'physical:host',
                }
            ],
            [])
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=2)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @mock.patch.object(api.client, 'compute_host_available')
    @mock.patch.object(api.client, 'lease_list')
    @mock.patch.object(api.client, 'lease_create')
    def test_create_lease_client_error(self, lease_create, lease_list,
                                       compute_host_available):
        lease_list.return_value = []
        compute_host_available.return_value = 5
        lease_create.side_effect = self.exceptions.blazar
        form_data = {
            'name': 'lease-1',
            'start_date': '2030-06-27',
            'start_time': '18:00',
            'end_date': '2030-06-30',
            'end_time': '18:00',
            'with_computehost': True,
            'min_hosts': 1,
            'max_hosts': 1,
        }

        res = self.client.post(CREATE_URL, form_data)

        lease_create.assert_called_once_with(
            test.IsHttpRequest(),
            'lease-1',
            '2030-06-27 18:00',
            '2030-06-30 18:00',
            [
                {
                    'min': 1,
                    'max': 1,
                    'hypervisor_properties': '',
                    'resource_properties': '',
                    'resource_type': 'physical:host',
                }
            ],
            [])
        self.assertMessageCount(error=2)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @mock.patch.object(api.client, 'lease_get')
    @mock.patch.object(api.client, 'lease_update')
    def test_update_lease_name_and_date(self, lease_update, lease_get):
        lease = self.leases.get(name='lease-1')
        form_data = {
            'lease_name': 'newname',
            'timespan-prolong_for-hours': '1',
        }
        lease_get.return_value = lease

        res = self.client.post(reverse(UPDATE_URL_BASE, args=[lease['id']]),
                               form_data)

        lease_get.assert_called_once_with(test.IsHttpRequest(), lease['id'])
        lease_update.assert_called_once_with(test.IsHttpRequest(),
                                             lease_id=lease['id'],
                                             name='newname',
                                             prolong_for='60m')
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=2)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @mock.patch.object(api.client, 'lease_get')
    @mock.patch.object(api.client, 'lease_update')
    def test_update_lease_reservations(self, lease_update, lease_get):
        lease = self.leases.get(name='lease-1')
        form_data = {
            'lease_id': lease['id'],
            'reservations': '[{"id": "087bc740-6d2d-410b-9d47-c7b2b55a9d36",'
                            ' "max": 3}]'
        }
        lease_get.return_value = lease

        res = self.client.post(reverse(UPDATE_URL_BASE, args=[lease['id']]),
                               form_data)

        lease_get.assert_called_once_with(test.IsHttpRequest(), lease['id'])
        lease_update.assert_called_once_with(
            test.IsHttpRequest(),
            lease_id=lease['id'],
            reservations=[{
                "id": "087bc740-6d2d-410b-9d47-c7b2b55a9d36",
                "max": 3}])
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=2)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @mock.patch.object(api.client, 'lease_get')
    @mock.patch.object(api.client, 'lease_update')
    def test_update_lease_error(self, lease_update, lease_get):
        lease = self.leases.get(name='lease-1')
        form_data = {
            'lease_name': 'newname',
            'timespan-prolong_for-hours': '1',
        }
        lease_get.return_value = lease
        lease_update.side_effect = self.exceptions.blazar

        res = self.client.post(reverse(UPDATE_URL_BASE, args=[lease['id']]),
                               form_data)

        lease_get.assert_called_once_with(test.IsHttpRequest(), lease['id'])
        lease_update.assert_called_once_with(test.IsHttpRequest(),
                                             lease_id=lease['id'],
                                             name='newname',
                                             prolong_for='60m')
        self.assertMessageCount(error=2)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @mock.patch.object(api.client, 'lease_list')
    @mock.patch.object(api.client, 'lease_delete')
    def test_delete_lease(self, lease_delete, lease_list):
        leases = self.leases.list()
        lease = self.leases.get(name='lease-1')
        action = 'leases__delete__%s' % lease['id']
        form_data = {'action': action}
        lease_list.return_value = leases

        res = self.client.post(INDEX_URL, form_data)

        lease_list.assert_called_once_with(
            test.IsHttpRequest(), all_tenants=False, marker=None, limit=20)
        lease_delete.assert_called_once_with(test.IsHttpRequest(), lease['id'])
        self.assertMessageCount(success=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @mock.patch.object(api.client, 'lease_list')
    @mock.patch.object(api.client, 'lease_delete')
    def test_delete_lease_error(self, lease_delete, lease_list):
        leases = self.leases.list()
        lease = self.leases.get(name='lease-1')
        action = 'leases__delete__%s' % lease['id']
        form_data = {'action': action}
        lease_list.return_value = leases
        lease_delete.side_effect = self.exceptions.blazar

        res = self.client.post(INDEX_URL, form_data)

        lease_list.assert_called_once_with(
            test.IsHttpRequest(), all_tenants=False, marker=None, limit=20)
        lease_delete.assert_called_once_with(test.IsHttpRequest(), lease['id'])
        self.assertMessageCount(error=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    # conf binds the OPENSTACK_BLAZAR_* settings at import time, so
    # override_settings does not reach it; patch the module attribute.
    @mock.patch.object(conf, "flavor_reservation", {"enabled": False})
    def test_flavor_step_not_shown_when_disabled(self):
        workflow = project_workflows.VirtualCreateLease(request=self.request)

        self.assertNotIn(
            project_workflows.SetFlavors,
            [type(step) for step in workflow.steps],
        )

    def test_flavor_step_shown_when_enabled(self):
        workflow = project_workflows.VirtualCreateLease(request=self.request)

        self.assertIn(
            project_workflows.SetFlavors,
            [type(step) for step in workflow.steps],
        )

    def test_flavor_step_not_on_baremetal_workflow(self):
        workflow = project_workflows.CreateLease(request=self.request)

        step_classes = [type(step) for step in workflow.steps]
        self.assertNotIn(project_workflows.SetFlavors, step_classes)
        self.assertIn(project_workflows.SetHosts, step_classes)

    @mock.patch.object(conf, "flavor_reservation", {"enabled": True})
    @mock.patch.object(api.client, "flavors")
    def test_flavors_json(self, flavors):
        flavors.return_value = [
            {"id": "f1", "name": "m1.small", "extra_specs": {}}
        ]

        res = self.client.get(FLAVORS_URL)

        flavors.assert_called_once_with(test.IsHttpRequest())
        self.assertEqual(
            {"flavors": [{"id": "f1", "name": "m1.small", "extra_specs": {}}]},
            res.json(),
        )

    def test_create_lease_flavor_step_renders(self):
        res = self.client.get(VIRTUAL_CREATE_URL)

        self.assertContains(res, 'name="flavor_id"')

    @mock.patch.object(api.client, "lease_list")
    @mock.patch.object(api.client, "lease_create")
    def test_create_lease_flavor_reservation(self, lease_create, lease_list):
        lease_list.return_value = []
        lease_create.return_value = self.leases.get(name="lease-1")
        form_data = {
            "name": "lease-1",
            "start_date": "2030-06-27",
            "start_time": "18:00",
            "end_date": "2030-06-30",
            "end_time": "18:00",
            "with_flavor": True,
            "flavor_amount": 2,
            "flavor_id": "flavor-uuid",
        }

        res = self.client.post(VIRTUAL_CREATE_URL, form_data)

        lease_create.assert_called_once_with(
            test.IsHttpRequest(),
            "lease-1",
            "2030-06-27 18:00",
            "2030-06-30 18:00",
            [
                {
                    "resource_type": "flavor:instance",
                    "flavor_id": "flavor-uuid",
                    "amount": 2,
                    "affinity": "None",
                }
            ],
            [],
        )
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=2)
        self.assertRedirectsNoFollow(res, VIRTUAL_INDEX_URL)

    @mock.patch.object(api.client, "lease_list")
    @mock.patch.object(api.client, "lease_create")
    def test_create_lease_flavor_reservation_no_flavor_selected(
        self, lease_create, lease_list
    ):
        lease_list.return_value = []
        form_data = {
            "name": "lease-1",
            "start_date": "2030-06-27",
            "start_time": "18:00",
            "end_date": "2030-06-30",
            "end_time": "18:00",
            "with_flavor": True,
            "flavor_amount": 2,
        }

        res = self.client.post(VIRTUAL_CREATE_URL, form_data)

        lease_create.assert_not_called()
        self.assertContains(res, "No flavor is reserved!")

    @mock.patch.object(api.client, "lease_list")
    @mock.patch.object(api.client, "lease_create")
    def test_create_lease_flavor_reservation_no_amount(
        self, lease_create, lease_list
    ):
        lease_list.return_value = []
        form_data = {
            "name": "lease-1",
            "start_date": "2030-06-27",
            "start_time": "18:00",
            "end_date": "2030-06-30",
            "end_time": "18:00",
            "with_flavor": True,
            "flavor_id": "flavor-uuid",
        }

        res = self.client.post(VIRTUAL_CREATE_URL, form_data)

        lease_create.assert_not_called()
        self.assertContains(
            res, "Number of instances is required to reserve a flavor."
        )

    @mock.patch.object(conf, "flavor_reservation", {"enabled": True})
    def test_flavor_calendar_supplies_timezone_offset(self):
        res = self.client.get(FLAVOR_CALENDAR_URL)

        self.assertContains(res, 'id="cookie_offset"')

    # The suite now enables flavor reservation by default, so this one has to
    # ask for the disabled state explicitly.
    @mock.patch.object(conf, "flavor_reservation", {"enabled": False})
    def test_flavor_endpoints_absent_when_disabled(self):
        for url in (FLAVORS_URL, FLAVOR_CALENDAR_URL,
                    FLAVOR_CALENDAR_DATA_URL):
            self.assertEqual(404, self.client.get(url).status_code, url)

    @mock.patch.object(api.client, "reservation_calendar")
    def test_host_calendar_data_unaffected_when_flavor_disabled(
        self, reservation_calendar
    ):
        reservation_calendar.return_value = ([], [])

        res = self.client.get(HOST_CALENDAR_DATA_URL)

        self.assertEqual(200, res.status_code)

    def _lease_reserving(self, name, *resource_types):
        lease = dict(self.leases.get(name='lease-1').to_dict())
        lease['id'] = name
        lease['name'] = name
        lease['reservations'] = [{'resource_type': rt} for rt in resource_types]
        return api.client.Lease(lease)

    @mock.patch.object(api.client, 'lease_list')
    def test_index_excludes_flavor_only_leases(self, lease_list):
        lease_list.return_value = [
            self._lease_reserving('host-lease', 'physical:host'),
            self._lease_reserving('flavor-lease', 'flavor:instance'),
            self._lease_reserving('both-lease',
                                  'physical:host', 'flavor:instance'),
        ]

        res = self.client.get(INDEX_URL)

        self.assertContains(res, 'host-lease')
        self.assertContains(res, 'both-lease')
        self.assertNotContains(res, 'flavor-lease')

    @mock.patch.object(api.client, 'lease_list')
    def test_virtual_index_excludes_host_only_leases(self, lease_list):
        lease_list.return_value = [
            self._lease_reserving('host-lease', 'physical:host'),
            self._lease_reserving('flavor-lease', 'flavor:instance'),
            self._lease_reserving('both-lease',
                                  'physical:host', 'flavor:instance'),
        ]

        res = self.client.get(VIRTUAL_INDEX_URL)

        self.assertContains(res, 'flavor-lease')
        self.assertContains(res, 'both-lease')
        self.assertNotContains(res, 'host-lease')

    @mock.patch.object(conf, 'flavor_reservation', {'enabled': False})
    @mock.patch.object(api.client, 'lease_list')
    def test_index_unfiltered_when_disabled(self, lease_list):
        lease_list.return_value = [
            self._lease_reserving('host-lease', 'physical:host'),
            self._lease_reserving('flavor-lease', 'flavor:instance'),
        ]

        res = self.client.get(INDEX_URL)

        self.assertContains(res, 'host-lease')
        self.assertContains(res, 'flavor-lease')
