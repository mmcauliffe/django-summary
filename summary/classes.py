from collections import OrderedDict
from decimal import Decimal
from django.utils.safestring import mark_safe
from datetime import date
import json

def render_value(value,resolution):
    if isinstance(value,date):
        if resolution == 'month':
            return value.strftime("%b %Y")
        elif resolution == 'week':
            return value.strftime("%d %b %Y")
        else:
            return value.strftime("%Y")
    return value

def json_dict_to_list(dictionary):
    key_value_template = "['%s',%s],"
    string = '[%s]' % '\n'.join([key_value_template % (k,v) for k,v in dictionary.items()])
    return string

class Summary(object):
    data = None
    dimensions = [0]
    date_resolution = 'none'
    title = ''

    def __init__(self,summary,title,date_resolution):
        self.date_resolution = date_resolution
        self.title = title
        self.id = title.replace(" ",'').replace('(','').replace(')','')
        if isinstance(summary.itervalues().next(),OrderedDict):
            self.dimensions = [0,0]
        data = OrderedDict()
        for k,v in summary.items():
            if len(self.dimensions) == 1:
                data[k] = v
            else:
                for k2,v2 in v.items():
                    data[(k,k2)] = v2
        if len(self.dimensions) == 2:
            kones = set([])
            ktwos = set([])
            for x in data:
                kones.update([x[0]])
                ktwos.update([x[1]])
            self.dimensions = [sorted(kones),sorted(ktwos)]
            for o in kones:
                for t in ktwos:
                    if (o,t) not in data:
                        data[(o,t)] = Decimal('0.00')
        self.data = data

    def data_to_table(self):
        if len(self.dimensions) == 1:
            head = [self.title,'Total']
            body = []
            for k,v in self.data.items():
                body.append([render_value(k,self.date_resolution),'{:,}'.format(v)])
        else:
            head = self.dimensions[0]
            body = []
            for x in self.dimensions[1]:
                row = [render_value(x,self.date_resolution)]
                row += ['{:,}'.format(self.data[(y,x)]) for y in self.dimensions[0]]
                body.append(row)

        return head,body

    def as_csv(self):
        head,body = self.data_to_table()
        rows = [head] + body
        return rows

    def as_table(self):
        table = '<table class="summary"><thead>%(head)s</thead><tbody>%(body)s</tbody></table>'
        row = '<tr>%s</tr>'
        head_cell = '<th>%s</th>'
        body_cell = '<td>%s</td>'
        headdata,bodydata = self.data_to_table()
        body_temp = ''.join([head_cell]+[body_cell]*(len(headdata)-1))

        head = row % ''.join([ head_cell % x for x in headdata])
        body = []
        for r in bodydata:
            body_row = body_temp % tuple(r)
            body.append(row % (body_row))
        body = ''.join(body)
        return mark_safe(table % {'head':head,'body':body})

    def as_chart(self):
        options = {
                    'section_name': self.title,
                    'time_resolution': self.date_resolution
                    }
        data = {}
        if len(self.dimensions) == 2:
            for x in self.dimensions[0]:
                data[x] = [ [k[1],v] for k,v in self.data.items() if k[0] == x]
        else:
            data[''] = self.data
        options['data'] = data
        if len(self.dimensions) == 2 or isinstance(self.data.iterkeys().next(),date):
            options['chart_type'] = 'line'
            options['xaxis_type'] = 'datetime'
            options['yaxis_title'] = ''
        else:
            options['chart_type'] = 'pie'
        c = HighChartsRenderer(options)
        t = c.render()
        return t


class HighChartsRenderer(object):
    tooltip_template = """"""
    function_template = """"""
    data_template = """"""

    def __init__(self,options_dict):
        self.section_name = options_dict.get('section_name',"container")
        self.chart_type = options_dict.get('chart_type','pie')
        self.title = options_dict.get('title','')
        self.data = options_dict.get('data',{})
        self.xaxis_type = options_dict.get('xaxis_type',None)
        self.yaxis_type = options_dict.get('yaxis_type',None)
        self.time_resolution = options_dict.get('time_resolution',None)

        self.function_template = """$(function () {
        $('#%s').highcharts({%%s});
    });""" % self.section_name

    def render(self):
        t = self._build_chart()
        t = self._build_title()
        t = self._build_tooltip()
        t = self._build_x_axis()
        t = self._build_y_axis()
        t = self._build_data()
        to_render = [self._build_chart(), self._build_title(),
                                 self._build_tooltip(),self._build_x_axis(),
                                 self._build_y_axis(),self._build_data()]

        r = mark_safe(self.function_template % ',\n'.join([x for x in to_render if x is not None]))
        return r

    def _build_tooltip(self):
        tooltip_template = """tooltip: {
                formatter: function() {
                    %s
                }
            }"""
        if self.chart_type == 'pie':
            return tooltip_template % "return '<b>'+ this.point.name +'</b>: '+ this.point.y + ' (' + Highcharts.numberFormat(this.percentage, 1) +' %)';"
        else:
            return tooltip_template % "return '<b>'+ this.series.name +'</b><br/>'+ Highcharts.dateFormat('%e. %b', this.x) +': '+ this.y;"

    def _build_x_axis(self):
        if self.chart_type == 'pie':
            return None
        xaxis_template = """
        xAxis: {
                type: '%s'%s
            }"""
        if self.xaxis_type == 'datetime':
            formatter = ",\ndateTimeLabelFormats: { %s}"
            if self.time_resolution == 'month':
                formatter = formatter % "month: '%b %y'"
            elif self.time_resolution == 'year':
                formatter = formatter % "year: '%y'"
            else:
                formatter = ''
            return xaxis_template % (self.xaxis_type,formatter)
        return None

    def _build_y_axis(self):
        xaxis_template = """
        yAxis: {
                type: '%s'%s
            }"""
        return None

    def _build_data(self):
        series_template = """series: [%s]"""
        #Fix to use json.dumps?
        data_template = """{
                name: '%s',
                data: %s,
            }"""
        if self.xaxis_type == 'datetime':
            data_string_template = """[Date.UTC(%d, %d, %d), %s]"""
            d_strings = []
            for k,d in self.data.items():
                if isinstance(d, list):
                    t = [ (x.year,x.month-1,x.day,v) for x,v in d if x is not None]
                else:
                    t = [ (x.year,x.month-1,x.day,d[x]) for x in d.keys() if x is not None]
                data_strings = [data_string_template % x for x in t]
                d_strings.append(data_template % (k,'[%s]' %
                                    ',\n'.join([x for x in data_strings])))
            return series_template % ',\n'.join([x for x in d_strings])

        else:
            d = self.data
            t = [data_template % (k,json_dict_to_list(v)) for k,v in self.data.items()]
            #p
            t = series_template % ',\n'.join(t)
            return t


    def _build_title(self):
        title_template = """title:{text: '%s'}"""
        return title_template % self.title

    def _build_chart(self):
        chart_template = """chart: {
                type: '%s',
                plotBackgroundColor: null,
                plotBorderWidth: null,
                plotShadow: false
            }"""
        return chart_template % self.chart_type
