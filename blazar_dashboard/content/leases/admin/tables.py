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

import pytz

from blazar_dashboard import api
from blazar_dashboard import conf
from django.template import defaultfilters as django_filters
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy
from functools import partial
from horizon import tables
from horizon.utils import filters
from blazar_dashboard.content.leases import tables as project_tables

LOG = logging.getLogger(__name__)

class AdminLeaseFilterAction(project_tables.LeaseFilterAction):
    filter_choices = project_tables.LeaseFilterAction.filter_choices + (
        ('project', _("Project Name ="), True),
        ('project_id', _("Project ID ="), True),
    )

class AdminLeasesTable(project_tables.LeasesTable):
    class Meta(object):
        table_actions = [project_tables.DeleteLease, AdminLeaseFilterAction, ]
