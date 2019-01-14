# Copyright 2014 Intel Corporation
# All Rights Reserved.
#
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

from datetime import datetime
from functools import partial

from django.template import defaultfilters as django_filters
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy
from horizon import tables
from horizon.utils import filters
import pytz

from blazar_dashboard import api


class CreateLease(tables.LinkAction):
    name = "create"
    verbose_name = _("Create Lease")
    url = "horizon:project:leases:create"
    classes = ("btn-create", "btn-primary", "ajax-modal", )
    icon = "plus"
    ajax = True

    def __init__(self, attrs=None, **kwargs):
        kwargs['preempt'] = True
        super(CreateLease, self).__init__(attrs, **kwargs)


class UpdateLease(tables.LinkAction):
    name = "update"
    verbose_name = _("Update Lease")
    url = "horizon:project:leases:update"
    classes = ("btn-create", "ajax-modal")

    def allowed(self, request, lease):
        if datetime.strptime(lease.end_date, '%Y-%m-%dT%H:%M:%S.%f').\
                replace(tzinfo=pytz.utc) > datetime.now(pytz.utc):
            return True
        return False


class ViewLeaseCalendar(tables.LinkAction):
    ## TODO(nicktimko) move calendar to a panel
    name = "calendar"
    verbose_name = _("Host Calendar")
    url = "horizon:project:leases:calendar"
    classes = ("btn-default", )
    icon = "calendar"


class ViewNetworkReservationCalendar(tables.LinkAction):
    name = "network_calendar"
    verbose_name = _("Network Reservation Calendar")
    url = "horizon:project:leases:network_calendar"
    classes = ("btn-default", )
    icon = "calendar"


class DeleteLease(tables.DeleteAction):
    name = "delete"
    data_type_singular = _("Lease")
    data_type_plural = _("Leases")
    classes = ('btn-danger', 'btn-terminate')

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Lease",
            u"Delete Leases",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted Lease",
            u"Deleted Leases",
            count
        )

    def delete(self, request, lease_id):
        api.client.lease_delete(request, lease_id)


class LeasesTable(tables.DataTable):
    name = tables.Column("name", verbose_name=_("Lease name"),
                         link="horizon:project:leases:detail",)
    start_date = tables.Column("start_date", verbose_name=_("Start date"),
                               filters=(filters.parse_isotime,
                                        partial(django_filters.date,
                                                arg='Y-m-d H:i T')),)
    end_date = tables.Column("end_date", verbose_name=_("End date"),
                             filters=(filters.parse_isotime,
                                      partial(django_filters.date,
                                              arg='Y-m-d H:i T')),)
    status = tables.Column("status", verbose_name=_("Status"),)

    class Meta(object):
        name = "leases"
        verbose_name = _("Leases")
        table_actions = (ViewLeaseCalendar, ViewNetworkReservationCalendar,
                         CreateLease, DeleteLease, )
        row_actions = (UpdateLease, DeleteLease, )
