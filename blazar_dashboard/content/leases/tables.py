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
import logging
from datetime import datetime
from datetime import timezone
from functools import partial

from blazar_dashboard import api
from blazar_dashboard import conf
from django.template import defaultfilters as django_filters
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy
from horizon import tables
from horizon.utils import filters

LOG = logging.getLogger(__name__)


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


class CreateVirtualLease(CreateLease):
    url = "horizon:project:virtual_leases:create"


class UpdateLease(tables.LinkAction):
    name = "update"
    verbose_name = _("Update Lease")
    url = "horizon:project:leases:update"
    classes = ("btn-create", "ajax-modal")

    def allowed(self, request, lease):
        if datetime.strptime(lease.end_date, '%Y-%m-%dT%H:%M:%S.%f').\
                replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
            return True
        return False


class ViewHostReservationCalendar(tables.LinkAction):
    name = "calendar"
    verbose_name = _("Host Calendar")
    url = "calendar/host/"
    classes = ("btn-default", )
    icon = "calendar"


class ViewNetworkReservationCalendar(tables.LinkAction):
    name = "network_calendar"
    verbose_name = _("Network Calendar")
    url = "calendar/network/"
    classes = ("btn-default", )
    icon = "calendar"


class ViewDeviceReservationCalendar(tables.LinkAction):
    name = "device_calendar"
    verbose_name = _("Device Calendar")
    url = "calendar/device/"
    classes = ("btn-default", )
    icon = "calendar"


class ViewFlavorReservationCalendar(tables.LinkAction):
    name = "flavor_calendar"
    verbose_name = _("Flavor Calendar")
    url = "calendar/flavor/"
    classes = ("btn-default", )
    icon = "calendar"


class DeleteLease(tables.DeleteAction):
    name = "delete"
    data_type_singular = _("Lease")
    data_type_plural = _("Leases")
    classes = ('btn-danger', 'btn-terminate')

    @staticmethod
    def action_present(count):
        return ngettext_lazy(
            u"Delete Lease",
            u"Delete Leases",
            count
        )

    @staticmethod
    def action_past(count):
        return ngettext_lazy(
            u"Deleted Lease",
            u"Deleted Leases",
            count
        )

    def delete(self, request, lease_id):
        api.client.lease_delete(request, lease_id)


class LeaseFilterAction(tables.FilterAction):
    name = "filter_leases"
    filter_type = "server"
    filter_choices = (
        ('status', _("Status ="), True),
        ('lease_name', _("Lease Name ="), True),
        ('lease_id', _("Lease ID ="), True)
    )


class LeasesTable(tables.DataTable):
    name = tables.Column("name", verbose_name=_("Lease name"),
                         link="horizon:project:leases:detail",)
    user_id = tables.Column("user_id", verbose_name=_("Created by"))
    start_date = tables.Column("start_date", verbose_name=_("Start date"),
                               filters=(filters.parse_isotime,))
    end_date = tables.Column("end_date", verbose_name=_("End date"),
                             filters=(filters.parse_isotime,),)
    status = tables.Column("status", verbose_name=_("Status"),)
    degraded = tables.Column("degraded", verbose_name=_("Degraded"),
                             filters=(django_filters.yesno,
                                      django_filters.capfirst),)

    class Meta(object):
        name = "leases"
        verbose_name = _("Leases")
        pagination_param = "marker"
        table_actions = [CreateLease, DeleteLease, LeaseFilterAction, ]
        if conf.floatingip_reservation.get('enabled'):
            # TODO: put in floating IP calendar support
            pass
        if conf.network_reservation.get('enabled'):
            table_actions.insert(0, ViewNetworkReservationCalendar)
        if conf.host_reservation.get('enabled'):
            table_actions.insert(0, ViewHostReservationCalendar)
        if conf.device_reservation.get('enabled'):
            table_actions.insert(0, ViewDeviceReservationCalendar)

        row_actions = (UpdateLease, DeleteLease, )


class VirtualLeasesTable(LeasesTable):
    name = tables.Column("name", verbose_name=_("Lease name"),
                         link="horizon:project:virtual_leases:detail",)

    class Meta(object):
        name = "virtual_leases"
        verbose_name = _("Virtual Leases")
        pagination_param = "marker"
        table_actions = [CreateVirtualLease, DeleteLease, LeaseFilterAction, ]
        if conf.network_reservation.get('enabled'):
            table_actions.insert(0, ViewNetworkReservationCalendar)
        if conf.device_reservation.get('enabled'):
            table_actions.insert(0, ViewDeviceReservationCalendar)
        if conf.flavor_reservation.get('enabled'):
            table_actions.insert(0, ViewFlavorReservationCalendar)

        row_actions = (UpdateLease, DeleteLease, )
