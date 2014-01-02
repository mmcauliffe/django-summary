# Create your views here.
from decimal import Decimal
from collections import OrderedDict
import csv
from datetime import date

from django.http import HttpResponse
from django.db import models
from django.shortcuts import get_object_or_404
from django.views.generic.base import TemplateResponseMixin, ContextMixin, View
from django.core.exceptions import ImproperlyConfigured
#from chartit import PivotDataPool, PivotChart, DataPool, Chart
from django.utils.safestring import mark_safe
from django.db import connections


from summary.classes import Summary
from summary.helper import get_all_related_objects, get_related_class, find_nearby_field, find_fields_by_type




class MultipleQuerysetMixin(ContextMixin):
    querysets = None
    grouping_model = None
    pk_url_kwarg = 'pk'
    context_object_name = None
    related_name_restriction = None

    def _build_grouping_string(self,obj_class,distance):
        related,m2m = get_all_related_objects(obj_class)
        relevant = filter(lambda x: get_related_class(x) == self.grouping_model,
                            [x for x in related+m2m])
        group_string = '%s'
        if len(relevant) == 1:
            group_string = relevant[0].field.name
        elif len(relevant) > 1 and self.related_name_restriction is not None:
            group_string = [x.field.name
                            for x in relevant
                            if self.related_name_restriction in x.field.name][0]
        elif distance == 2:
            possible_routes = []
            for r in related+m2m:
                rel,m = get_all_related_objects(get_related_class(r))
                relevant = filter(lambda x: get_related_class(x) == self.grouping_model,
                            [x for x in rel+m])
                for p in relevant:
                    possible_routes.append('%s__%s' % (r.field.name,p.field.name))
            if len(possible_routes) > 1:
                group_string = [x for x in possible_routes
                            if self.related_name_restriction in x][0]
            elif len(possible_routes) == 1:
                group_string = possible_routes[0]
            else:
                raise ImproperlyConfigured('No relevant related models for grouping model.')
        else:
            raise ImproperlyConfigured('No relevant related models for grouping model.')

        return group_string


    def get_querysets(self,distance = 1):
        """
        Get the list of items for this view. This must be an iterable, and may
        be a queryset (in which qs-specific behavior will be enabled).
        """
        pk = self.kwargs.get(self.pk_url_kwarg, None)
        if self.querysets is not None:
            if self.grouping_model is not None and pk is not None:
                gm = get_object_or_404(self.grouping_model,pk = pk)
                self.querysets = [q.filter(**{self._build_grouping_string(q.model,distance):pk}) for q in self.querysets]
        else:
            raise ImproperlyConfigured('No query sets specified.')
        return self.querysets


    def get_context_object_name(self, object_list):
        """
        Get the name of the item to be used in the context.
        """
        if self.context_object_name:
            return self.context_object_name
        elif hasattr(object_list, 'model'):
            return '%s_summary' % object_list.model._meta.object_name.lower()
        else:
            return None

    def get_context_data(self, **kwargs):
        """
        Get the context for this view.
        """
        summary = kwargs.pop('summary')
        context_object_name = self.get_context_object_name(summary)
        context = {
                'sum_info': summary
            }
        if context_object_name is not None:
            context[context_object_name] = summary
        context.update(kwargs)
        return super(MultipleQuerysetMixin, self).get_context_data(**context)

class BaseSummaryView(MultipleQuerysetMixin, View):
    """
    A base view for displaying a summaries of grouping objects related to other objects.
    """
    field_mapping = None
    filters = None
    distance = 1
    date_resolution = 'none'

    def get(self, request, *args, **kwargs):
        self.date_resolution = request.GET.get('time_period','none')
        if not self.distance:
            self.distance = 1
        qs = self.get_querysets(distance = self.distance)
        if self.filters:
            for f in self.filters:
                qs = f.apply_filter(request,qs)

        summary = self.get_summary(qs)
        context = self.get_context_data(summary=summary,filters = self.filters)
        csv_check = request.GET.get('csv',0)
        key = request.GET.get('key',None)
        if csv_check and key is not None:
            try:
                summary = summary[key]
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename="%s.csv"' % key
                writer = csv.writer(response, delimiter='\t',quotechar = '')
                for line in summary.as_csv():
                    writer.writerow(line)
                return response
            except KeyError:
                pass
        return self.render_to_response(context)

    def get_summary(self,querysets):
        summaries = []
        for key,value in self.field_mapping.items():
            by,field,function = value
            summary = OrderedDict()
            if by == 'queryset':
                for q in querysets:
                    f = find_nearby_field(q.model,field)
                    if f is None: #Is not relevant field for this queryset
                        continue
                    g = q.model._meta.verbose_name_plural
                    if self.date_resolution != 'none':
                        summary[g] = OrderedDict()
                        date_fields = find_fields_by_type(q.model, models.fields.DateField)
                        q = q.extra(select={
                            self.date_resolution: connections[q.model.objects.db].ops.date_trunc_sql(self.date_resolution,'"'+date_fields[0].name+'"')})
                        qs = q.order_by(self.date_resolution).values(self.date_resolution).annotate(Agg = function(f))
                        for x in qs:
                            summary[g][x[self.date_resolution]] = x['Agg']
                    else:
                        summary[g] = q.aggregate(Agg = function(f))['Agg']
                        if summary[g] is None:
                            summary[g] = Decimal('0.00')
            elif by == '':
                for q in querysets:
                    f = find_nearby_field(q.model, field)
                    if f is None: #Is not relevant field for this queryset
                        continue
                    if self.date_resolution != 'none':
                        date_fields = find_fields_by_type(q.model, models.fields.DateField)

                        q = q.extra(select={
                            self.date_resolution: connections[q.model.objects.db].ops.date_trunc_sql(self.date_resolution,'"'+date_fields[0].name+'"')})
                        qs = q.order_by(self.date_resolution).values(self.date_resolution).annotate(Agg = function(field))

                        for x in qs:
                            summary[x[self.date_resolution]] = x['Agg']
                    else:
                        qs = q.aggregate(All = function(field))
                        summary = qs
            elif isinstance(by,str):
                for q in querysets:
                    opts = q.model._meta
                    g = None
                    if by in [f.name for f in opts.fields]:
                        g = opts.get_field(by)
                    if g is None and by not in q.query.extra.keys():
                        continue
                    if isinstance(g,models.fields.DateField):
                        if self.date_resolution != 'none':
                            q = q.extra(select={
                            self.date_resolution: connections[q.model.objects.db].ops.date_trunc_sql(self.date_resolution,'"'+by+'"')})
                            by = self.date_resolution
                        else:
                            summary = q.aggregate(All = function(field))
                            continue
                    qs = q.order_by(by).values(by).annotate(Agg = function(field))
                    for x in qs:
                        if g is None or not g.choices:
                            t = x[by]
                            summary[t] = x['Agg']
                        else:
                            for c in g.choices:
                                if c[0] == x[by]:
                                    summary[c[1]] = x['Agg']
                                    break
                            else:
                                summary[str(x[by])] = x['Agg']
            elif issubclass(by,models.Model):
                for q in querysets:
                    related,m2m = get_all_related_objects(q.model)
                    relevant = list(filter(lambda x: get_related_class(x) == by,
                            [x for x in related+m2m]))
                    if not len(relevant):
                        continue
                    for r in relevant:
                        #key = r.field.verbose_name
                        g = r.field.name
                        f = find_nearby_field(q.model,field)
                        if f is None: #Is not relevant field for this queryset
                            continue
                        qs = q.order_by(g).values(g).annotate(Agg = function(f))
                        for x in qs:

                            if x[g] is not None:
                                summary[str(by.objects.get(pk=x[g]))] = x['Agg']
            if summary:
                summary = Summary(summary,key,self.date_resolution)
                summaries.append(summary)
        return summaries



class MultipleQuerysetTemplateResponseMixin(TemplateResponseMixin):
    """
    Mixin for responding with a template and list of objects.
    """
    template_name_suffix = '_list'

    def get_template_names(self):
        """
        Return a list of template names to be used for the request. Must return
        a list. May not be called if render_to_response is overridden.
        """
        try:
            names = super(MultipleQuerysetTemplateResponseMixin, self).get_template_names()
        except ImproperlyConfigured:
            # If template_name isn't specified, it's not a problem --
            # we just start with an empty list.
            names = []

        # If the list is a queryset, we'll invent a template name based on the
        # app and model name. This name gets put at the end of the template
        # name list so that user-supplied names override the automatically-
        # generated ones.
        names.append("summary/summary.html" )

        return names

class SummaryView(MultipleQuerysetTemplateResponseMixin, BaseSummaryView):
    """
    Render some list of objects, set by `self.model` or `self.queryset`.
    `self.queryset` can actually be any iterable of items, not just a queryset.
    """


