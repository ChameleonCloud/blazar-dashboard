import datetime
import json

from django.forms.widgets import Widget
from django.template import loader
from django.utils.safestring import mark_safe


EQUALITIES = {
    'eq': '==',
    'lt': '<',
    'le': '<=',
    'gt': '>',
    'ge': '>=',
    'ne': '!=',
}


class CapabilityWidget(Widget):
    template_name = 'project/leases/_widget_{resource_type}_capabilities.html'

    def __init__(self, *args, **kwargs):
        self.resource_type = kwargs.pop('resource_type')
        self.switchable_class = kwargs.pop('switchable_class')
        super(CapabilityWidget, self).__init__(*args, **kwargs)

    def get_context(self, name, value, attrs=None):
        # Convert JSON back to plain text for display
        display_value = value or ''
        if display_value and display_value.startswith('['):
            try:
                data = json.loads(display_value)
                criteria_list = []

                if isinstance(data, list) and len(data) > 0:
                    if data[0] == 'and':
                        for item in data[1:]:
                            if isinstance(item, list) and len(item) == 3:
                                op, prop, val = item
                                if isinstance(prop, str) and prop.startswith('$'):
                                    prop = prop[1:]
                                criteria_list.append('{} {} {}'.format(prop, op, val))
                    else:
                        if len(data) == 3:
                            op, prop, val = data
                            if isinstance(prop, str) and prop.startswith('$'):
                                prop = prop[1:]
                            criteria_list.append('{} {} {}'.format(prop, op, val))

                display_value = ', '.join(criteria_list)
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

        return {'widget': {
            'name': name,
            'value': display_value,
            'switchable_class': self.switchable_class
        }}

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        template_path = self.template_name.format(resource_type=self.resource_type)
        return mark_safe(loader.get_template(template_path).render(context))

    def value_from_datadict(self, data, files, name):
        text_value = data.get('criteria-' + name, '')

        if not text_value or text_value.strip() == '':
            return ''

        operators = ['==', '!=', '<=', '>=', '<', '>']
        formatted_criteria = []

        for item in text_value.split(','):
            item = item.strip()
            if not item:
                continue

            found_op = None
            for op in operators:
                if op in item:
                    found_op = op
                    break

            if found_op:
                parts = item.split(found_op, 1)
                if len(parts) == 2:
                    prop_name = parts[0].strip()
                    prop_value = parts[1].strip()
                    if prop_name and prop_value:
                        formatted_criteria.append([found_op, '$' + prop_name, prop_value])

        if len(formatted_criteria) < 1:
            resource_properties = ''
        elif len(formatted_criteria) == 1:
            resource_properties = json.dumps(formatted_criteria[0], separators=(',', ':'))
        else:
            resource_properties = json.dumps(['and'] + formatted_criteria, separators=(',', ':'))

        return resource_properties


class TimespanWidget(Widget):
    """
    Produces 4 text boxes for days/hours/minutes/seconds. Converts data into
     - an empty string (net time is zero),
     - a string of the form "<integer>s", or
     - "invalid" if a non-numeric value is entered into one of the boxes.
    """
    template_name = 'project/leases/_widget_timespan.html'

    def get_context(self, name, value, attrs=None):
        return {'widget': {
            'name': name,
            'value': value,
        }}

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        template = loader.get_template(self.template_name).render(context)
        return mark_safe(template)

    def value_from_datadict(self, data, files, name):
        parts = {p: 0 for p in ['days', 'hours', 'minutes']}
        for part in parts:
            try:
                parts[part] = data['timespan-{}-{}'.format(name, part)]
            except LookupError:
                parts[part] = 0
                continue  # missing assume 0

            if not parts[part]:
                # might be empty string
                parts[part] = 0
                continue

            try:
                parts[part] = float(parts[part])
            except ValueError:
                return 'invalid'

        timespan = datetime.timedelta(**parts)
        total_seconds = timespan.total_seconds()
        if abs(total_seconds) < 1:
            # if zero or sub-second time, ignore
            return ''
        return '{:.0f}s'.format(total_seconds)
