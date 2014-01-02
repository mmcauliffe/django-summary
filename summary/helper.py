
from django.db import models


def get_all_related_objects(obj):
    opts = obj._meta
    related = [f.related for f in opts.fields if isinstance(f,models.ForeignKey)]
    m2m = [f.related for f in opts._many_to_many()]
    return related,m2m

def get_related_class(rel_obj):
    return rel_obj.parent_model

def find_nearby_field(obj,field_name):
    opts = obj._meta
    obj_field_names = [f.name for f in opts.fields]
    if field_name in obj_field_names:
        return field_name
    m2m = opts._many_to_many()
    for m in m2m:
        if field_name in [f.name for f in m.rel.through._meta.fields]:
            return '%s__%s' %(m.rel.related_name.lower(),field_name)
    return None

def find_fields_by_type(obj, field_type):
    opts = obj._meta
    fields = filter(lambda x: isinstance(x,field_type),opts.fields)
    return fields
