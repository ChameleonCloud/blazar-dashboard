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
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import RedirectView
from horizon import exceptions
from horizon import messages
from horizon import tables
from horizon import tabs
from horizon import views
from horizon import workflows
from horizon.utils import memoized
from blazar_dashboard.content.leases import views

LOG = logging.getLogger(__name__)

class IndexView(views.IndexView):
    def get_data_kwargs(self):
        kwargs = super().get_data_kwargs()
        kwargs['all_tenants'] = True
        return kwargs

class DetailView(views.DetailView):
    pass

class UpdateView(views.UpdateView):
    pass

class ReallocateView(views.RedirectView):
    pass