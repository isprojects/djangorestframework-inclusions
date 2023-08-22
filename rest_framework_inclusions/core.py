from django.db.models import Manager
from django.utils.module_loading import import_string
from rest_framework.fields import SkipField
from rest_framework.relations import (
    HyperlinkedRelatedField,
    ManyRelatedField,
    PKOnlyObject,
    PrimaryKeyRelatedField,
    RelatedField,
)
from rest_framework.serializers import BaseSerializer, ListSerializer


class Error(Exception):
    pass


class InclusionLoader:
    # When doing inclusions, this indicates whether or not the entire path should
    # be used to include nested resources, e.g.: `?include=resource1.resource2` vs `?include=resource2`
    nested_inclusions_use_complete_path = False

    def __init__(self, allowed_paths):
        self.allowed_paths = allowed_paths
        self._seen = set()

    def get_model_key(self, obj, *args, **kwargs):
        return obj._meta.label

    def inclusions_dict(self, serializer):
        entries = self._inclusions((), serializer, serializer.instance)
        result = {}
        for obj, inclusion_serializer in entries:
            model_key = self.get_model_key(obj, inclusion_serializer)
            data = inclusion_serializer(instance=obj, context=serializer.context).data
            result.setdefault(model_key, []).append(data)
        # in-place sort of inclusions
        for value in result.values():
            value.sort(key=sort_key)
        return result

    def _inclusions(self, path, serializer, instance):
        if isinstance(serializer, ListSerializer):
            return self._list_inclusions(path, serializer.child, instance)
        elif isinstance(serializer, BaseSerializer):
            return self._instance_inclusions(path, serializer, instance)
        else:
            raise Error(f"Unknown serializer {repr(serializer)}")

    def _instance_inclusions(self, path, serializer, instance):
        inclusion_serializers = getattr(serializer, "inclusion_serializers", {})
        for name, field in serializer.fields.items():
            for entry in self._field_inclusions(path, field, instance, name, inclusion_serializers):
                yield entry

    def _list_inclusions(self, path, serializer, iterable):
        # be careful to use the existing cache in the queryset by not
        # using all(). This can also be a plain Python list.
        for entry in iterable:
            for entry in self._instance_inclusions(path, serializer, entry):
                yield entry

    def _field_inclusions(self, path, field, instance, name, inclusion_serializers):
        # if this turns out to be None, we don't want to do a thing
        if instance is None:
            return
        new_path = path + (name,)
        if isinstance(field, BaseSerializer):
            for entry in self._sub_serializer_inclusions(new_path, field, instance):
                yield entry
            return
        inclusion_serializer = inclusion_serializers.get(name)
        if inclusion_serializer is None:
            return
        if isinstance(inclusion_serializer, str):
            inclusion_serializer = import_string(inclusion_serializer)
        for obj in self._some_related_field_inclusions(new_path, field, instance, inclusion_serializer):
            yield obj, inclusion_serializer
            # when we do inclusions in inclusions, we base path off our
            # parent object path, not the sub-field
            nested_path = new_path if self.nested_inclusions_use_complete_path else new_path[:-1]
            for entry in self._instance_inclusions(nested_path, inclusion_serializer(instance=object), obj):
                yield entry

    def _sub_serializer_inclusions(self, path, field, instance):
        try:
            sub_instance = field.get_attribute(instance)
        except SkipField:
            return []
        if isinstance(field, ListSerializer):
            if isinstance(sub_instance, Manager):
                iterable = sub_instance.get_queryset()
            else:
                # this is either a true queryset, or a list
                iterable = sub_instance

            return self._list_inclusions(path, field.child, iterable)
        else:
            return self._instance_inclusions(path, field, sub_instance)

    def _some_related_field_inclusions(self, path, field, instance, inclusion_serializer):
        if self.allowed_paths is not None and path not in self.allowed_paths:
            return []
        if isinstance(field, PrimaryKeyRelatedField):
            return self._primary_key_related_field_inclusions(path, field, instance, inclusion_serializer)
        elif isinstance(field, HyperlinkedRelatedField):
            return self._primary_key_related_field_inclusions(path, field, instance, inclusion_serializer)
        elif isinstance(field, ManyRelatedField):
            return self._many_related_field_inclusions(path, field, instance)
        else:
            raise Error(f"Trying to include unknown field type: {repr(field)}")

    def _primary_key_related_field_inclusions(self, path, field, instance, inclusion_serializer):
        # Optimization:
        # get PKOnlyObject generated by DRF. This doesn't cause
        # a database query to be made at all. This avoids loading
        # the same underlying object twice if it's referenced by multiple
        # objects
        obj = field.get_attribute(instance)
        if obj is None or obj.pk is None:
            return
        if isinstance(obj, PKOnlyObject):
            entry = (inclusion_serializer.Meta.model._meta.label, obj.pk)
            if entry in self._seen:
                return
            # Now we have to use the RelatedField superclass here to avoid getting an
            # PKOnlyObject, since we *do* want to serialize the object later on as
            # an inclusion
            obj = super(RelatedField, field).get_attribute(instance)
        if self._has_been_seen(obj):
            return
        yield obj

    def _many_related_field_inclusions(self, path, field, instance):
        # We think an optimization isn't possible, because touching the field
        # to get the ids at all results in a select
        for obj in field.get_attribute(instance):
            if self._has_been_seen(obj):
                continue
            yield obj

    def _has_been_seen(self, obj):
        entry = (obj.__class__._meta.label, obj.pk)
        if entry in self._seen:
            return True
        self._seen.add(entry)
        return False


def sort_key(item):
    """
    Return the sort value for an item in a collection of included resources.

    Intended for nested, related objects that expose the ``id`` or ``pk`` field.

    :raises: ValueError if the PK cannot be determined.
    """
    if "id" in item:
        return item["id"]
    elif "pk" in item:
        return item["pk"]
    elif "url" in item:
        return item["url"]
    raise ValueError(
        "Item %r does not contain a reference to the 'id'. " " Please included it in the serializer." % item
    )
