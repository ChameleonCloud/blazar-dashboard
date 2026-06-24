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


from blazar_dashboard import api
from blazar_dashboard.api import client
from blazar_dashboard.content.leases import tables as project_tables
from blazar_dashboard.content.leases import tabs as project_tabs
from blazar_dashboard.content.leases import workflows as project_workflows
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import RedirectView
from horizon import exceptions
from horizon import messages
from horizon import tables
from horizon import tabs
from horizon import views
from horizon import workflows
from horizon.utils import memoized
from django.conf import settings

LOG = logging.getLogger(__name__)

class IndexView(tables.DataTableView):
    table_class = project_tables.LeasesTable
    template_name = 'project/leases/index.html'

    def filter_leases(self, leases):
        """Override in subclasses to filter leases."""
        if settings.CHAMELEON_ENABLE_VMS:
            physical_leases = []
            for lease in leases:
                # filter by leases that have flavor instance, or no physical host reservations
                no_flavor = True
                has_physical = False
                for x in lease["reservations"]:
                    if x["resource_type"] == "physical:host":
                        has_physical = True
                    if x["resource_type"] == "flavor:instance":
                        no_flavor = False
                if has_physical or no_flavor:
                    physical_leases.append(lease)
            return physical_leases
        return leases

    def get_data(self):
        try:
            leases = api.client.lease_list(self.request)
            leases = self.filter_leases(leases)
        except Exception:
            leases = []
            msg = _('Unable to retrieve lease information.')
            exceptions.handle(self.request, msg)
        return leases


class VirtualLeasesIndexView(IndexView):
    table_class = project_tables.VirtualLeasesTable

    def filter_leases(self, leases):
        """Filter leases by virtual reservation type."""
        flavor_leases = []
        for lease in leases:
            # filter by leases that have flavor instance, or no physical host reservations
            no_physical = True
            has_flavor = False
            for x in lease["reservations"]:
                if x["resource_type"] == "physical:host":
                    no_physical = False
                if x["resource_type"] == "flavor:instance":
                    has_flavor = True
            if has_flavor or no_physical:
                flavor_leases.append(lease)
        return flavor_leases


class CalendarView(views.APIView):
    template_name = 'project/leases/calendar.html'

    titles = {
        "host": _("Host Calendar"),
        "network": _("Network Calendar"),
        "device": _("Device Calendar"),
        "flavor": _("Flavor Calendar"),
    }

    def get_data(self, request, context, *args, **kwargs):
        context["calendar_title"] = self.titles[context["resource_type"]]
        return context


class FlavorCalendarView(views.APIView):
    template_name = "project/leases/calendar_flavor.html"

    def get_data(self, request, context, *args, **kwargs):
        context["calendar_title"] = _("Flavor Calendar")
        return context


def calendar_data_view(request, resource_type):
    api_mapping = {
        "host": api.client.reservation_calendar,
        "network": api.client.network_reservation_calendar,
        "device": api.client.device_reservation_calendar,
        "flavor": api.client.flavor_reservation_calendar,
    }
    data = {}
    resources, reservations = api_mapping[resource_type](request)
    data['resources'] = resources
    data['reservations'] = reservations
    data["project_id"] = request.user.project_id
    return JsonResponse(data)


def extra_capabilities(request, resource_type):
    extra_capabilities = None
    if resource_type == 'computehost':
        extra_capabilities = api.client.computehost_extra_capabilities(
            request)
    elif resource_type == 'network':
        extra_capabilities = api.client.network_extra_capabilities(
            request)
    elif resource_type == 'device':
        extra_capabilities = api.client.device_extra_capabilities(
            request)
    data = {
        'extra_capabilities': extra_capabilities}
    return JsonResponse(data)


def flavors(request):
    return JsonResponse({'flavors': api.client.flavors(request)})


class DetailView(tabs.TabView):
    tab_group_class = project_tabs.LeaseDetailTabs
    template_name = 'project/leases/detail.html'

class VirtualDetailView(DetailView):
    tab_group_class = project_tabs.LeaseDetailTabs
    # template_name = 'project/virtual_leases/detail.html'

class CreateView(workflows.WorkflowView):
    workflow_class = project_workflows.CreateLease

class VirtualCreateView(CreateView):
    workflow_class = project_workflows.VirtualCreateLease

class UpdateView(workflows.WorkflowView):
    workflow_class = project_workflows.UpdateLease

    def get_initial(self):
        initial = super(UpdateView, self).get_initial()
        initial['lease'] = self.get_object()

        return initial

    @memoized.memoized_method
    def get_object(self):
        lease_id = self.kwargs['lease_id']
        try:
            lease = api.client.lease_get(self.request, lease_id)
        except Exception:
            msg = _("Unable to retrieve lease.")
            redirect = reverse('horizon:project:leases:index')
            exceptions.handle(self.request, msg, redirect=redirect)
        return lease

class ReallocateView(RedirectView):

    def post(self, request, *args, **kwargs):
        """
        Handles requests made by buttons
        """
        host_reallocate = request.POST.get("host_reallocate")
        fail_page = reverse("horizon:project:leases:index")
        if not host_reallocate:
            LOG.error(f"Received malformed POST: {request.POST}")
            return redirect(fail_page)
        try:
            host_id, lease_id = host_reallocate.split(maxsplit=1)
            next_url = reverse("horizon:project:leases:detail", args=[lease_id])
        except Exception:
            exceptions.handle(
                request, _("Missing node ID or Lease ID"), redirect=fail_page
            )
            return redirect(fail_page)

        try:
            client.host_reallocate(request, host_id, lease_id)
        except Exception:
            exceptions.handle(
                request, _("Could not reallocate host."), redirect=next_url
            )
            return redirect(next_url)

        messages.success(request, f"Reallocated host {host_id}. "
                                  f"Updates may not appear in lease "
                                  f"for a few more seconds.")

        return redirect(next_url)


