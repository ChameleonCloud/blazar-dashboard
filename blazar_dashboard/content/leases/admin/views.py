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


from blazar_dashboard.content.leases.admin import tables as admin_tables
from blazar_dashboard.content.leases import views
from django.utils.translation import gettext_lazy as _

LOG = logging.getLogger(__name__)

class IndexView(views.IndexView):
    table_class = admin_tables.AdminLeasesTable

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