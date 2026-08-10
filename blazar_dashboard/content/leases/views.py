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
import pytz
import datetime
from concurrent.futures import ThreadPoolExecutor


from blazar_dashboard import api
from blazar_dashboard import conf
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

LOG = logging.getLogger(__name__)

class IndexView(tables.PagedTableMixin, tables.DataTableView):
    table_class = project_tables.LeasesTable
    template_name = 'project/leases/index.html'

    def get_data_kwargs(self):
        # User applied filters
        filters = self.get_filters()
        return {
            'all_tenants': False,
            "marker": self.request.GET.get(
                self.table_class._meta.pagination_param, None),
            "limit": conf.api_limit,
            **filters,
       }

    def get_data(self):
        try:
            leases = api.client.lease_list(
                self.request,
                **self.get_data_kwargs(),
            )
            limit = self.get_data_kwargs()['limit']
            self._has_more_data = len(leases) == limit
        except Exception:
            leases = []
            self._has_more_data = False
            msg = _('Unable to retrieve lease information.')
            exceptions.handle(self.request, msg)
        return leases


def add_timezone_context(request, context):
    """Supply the offset the calendar charts shift their timestamps by."""
    tz = pytz.timezone(
        request.session.get('django_timezone',
                            request.COOKIES.get('django_timezone', 'UTC')))
    context['timezone'] = tz
    context['offset'] = int(
        (datetime.datetime.now(tz).utcoffset().total_seconds() / 60) * -1)
    context['settings_href'] = reverse('horizon:settings:user:index')
    return context


class CalendarView(views.APIView):
    template_name = 'project/leases/calendar.html'

    titles = {
        "host": _("Host Calendar"),
        "network": _("Network Calendar"),
        "device": _("Device Calendar"),
        "flavor": _("Flavor Calendar"),
    }

    def get_data(self, request, context, *args, **kwargs):
        add_timezone_context(self.request, context)
        context["calendar_title"] = self.titles[context["resource_type"]]
        return context


class FlavorCalendarView(views.APIView):
    template_name = "project/leases/calendar_flavor.html"

    def get_data(self, request, context, *args, **kwargs):
        add_timezone_context(self.request, context)
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
    extra_capabilities_function_map = {
        "computehost": api.client.computehost_extra_capabilities,
        "network": api.client.network_extra_capabilities,
        "device": api.client.device_extra_capabilities
    }
    # Properties from the object to also fetch
    object_properties_map = {
        "device": ["name"],
        "network": ["segment_id"],
    }
    object_list_function_map = {
        "device": api.client.device_list,
        "network": api.client.network_list,
    }

    extra_capabilities = None
    with ThreadPoolExecutor(max_workers=2) as executor:
        extra_capabilities_future = None
        if resource_type in extra_capabilities_function_map:
            extra_capabilities_future = executor.submit(extra_capabilities_function_map[resource_type], request)

        objects = None
        if resource_type in object_list_function_map:
            objects_future = executor.submit(object_list_function_map[resource_type], request)
            objects = objects_future.result()

        if extra_capabilities_future:
            extra_capabilities = extra_capabilities_future.result()
            if objects:
                for prop in object_properties_map[resource_type]:
                    values = set()
                    for obj in objects:
                        values.add(obj.get(prop))
                    extra_capabilities[prop] = list(values)
    data = {
        'extra_capabilities': extra_capabilities}
    return JsonResponse(data)


def flavors(request):
    return JsonResponse({'flavors': api.client.flavors(request)})


class DetailView(tabs.TabView):
    tab_group_class = project_tabs.LeaseDetailTabs
    template_name = 'project/leases/detail.html'


class CreateView(workflows.WorkflowView):
    workflow_class = project_workflows.CreateLease

    def get_initial(self):
        initial = super(CreateView, self).get_initial()
        node_name = self.request.GET.get('node_name')
        if node_name:
            initial['with_computehost'] = True
            initial['min_hosts'] = 1
            initial['max_hosts'] = 1
            initial['computehost_resource_properties'] = f'node_name == {node_name}'
        return initial


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
