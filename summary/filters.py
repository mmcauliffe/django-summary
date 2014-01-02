import datetime
from django.utils import timezone
from django import forms
from django.db import models
from django.db.models import Sum
from summary.helper import get_all_related_objects

class DateRangeForm(forms.Form):
    since = forms.DateField(required=False)
    until = forms.DateField(required=False)

class EmptyForm(forms.Form):
    include_empty = forms.BooleanField(required=False)

class DisplayForm(forms.Form):
    display = forms.ChoiceField(choices=[('S','Summary'),('C','Chart')],required=False)

class TimeResolutionForm(forms.Form):
    time_period = forms.ChoiceField(choices=[('none','None'),('year','Year'),('month','Month'),('week','Week')],required=False)

class BaseFilter(object):
    title = None
    template_name = 'summary/filter.html'

class EmptyFilter(BaseFilter):
    title = 'Lack of default private rate'

    def __init__(self,based_on=None):
        self.based_on = based_on
        super(EmptyFilter, self).__init__()

    def apply_filter(self,request,querysets):
        form = EmptyForm(request.GET)
        for k,v in request.GET.items():
            if k not in ['include_empty']:
                form.fields[k] = forms.CharField(widget=forms.HiddenInput(), initial=v,required=False)
        self.form = form
        return self.filter_querysets(querysets)

    def filter_querysets(self,querysets):
        if not self.form.is_valid() or not self.form.cleaned_data['include_empty']:
            return querysets
        new_querysets = []
        for q in querysets:
            qs = q.exclude(**self.based_on)
            new_querysets.append(qs)

        return new_querysets

class DisplayFilter(BaseFilter):
    title = 'Display'

    def apply_filter(self,request,querysets):
        form = DisplayForm(request.GET)
        for k,v in request.GET.items():
            if k not in ['display']:
                form.fields[k] = forms.CharField(widget=forms.HiddenInput(), initial=v,required=False)
        self.form = form
        return querysets


class TimeResolutionFilter(BaseFilter):
    title = 'Time Resolution'

    def apply_filter(self,request,querysets):
        form = TimeResolutionForm(request.GET)
        for k,v in request.GET.items():
            if k not in ['time_period']:
                form.fields[k] = forms.CharField(widget=forms.HiddenInput(), initial=v,required=False)
        self.form = form
        return querysets

class DateRangeSummaryFilter(BaseFilter):
    """
    Filter based on dates
    """
    title = 'Date'


    def __init__(self,fields_excluded=None):
        self.fields_excluded = fields_excluded
        super(DateRangeSummaryFilter, self).__init__()

    def apply_filter(self,request,querysets):
        form = DateRangeForm(request.GET)
        for k,v in request.GET.items():
            if k not in ['since','until']:
                form.fields[k] = forms.CharField(widget=forms.HiddenInput(), initial=v,required=False)
        self.form = form
        return self.filter_querysets(querysets)

    def filter_querysets(self,querysets):
        if not self.form.is_valid():
            return querysets
        new_querysets = []
        for q in querysets:
            kwargs = {}
            fields = q.model()._meta.fields
            date_fields = filter(lambda x: isinstance(x,models.DateField),fields)
            if not date_fields:
                continue
            for df in date_fields:
                if self.fields_excluded and df.name in self.fields_excluded:
                    continue
                if self.form.cleaned_data['since']:
                    kwargs['%s__gte' % df.name] = self.form.cleaned_data['since']
                if self.form.cleaned_data['until']:
                    kwargs['%s__lte' % df.name] = self.form.cleaned_data['until']
            new_querysets.append(q.filter(**kwargs))

        return new_querysets
