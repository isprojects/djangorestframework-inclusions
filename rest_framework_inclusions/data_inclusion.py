import copy
import itertools
import logging
from collections import OrderedDict, defaultdict
from typing import List, Union

from django.db import models
from django.utils.module_loading import import_string

from rest_framework.relations import ManyRelatedField, RelatedField
from rest_framework.serializers import BaseSerializer, Field, SerializerMetaclass

logger = logging.getLogger(__name__)


class InclusionDefinition:
    def __init__(
        self,
        field: Field,
        serializer_class: SerializerMetaclass,
        data_path: Union[str, List[str]],
        inclusion_path: str = None,
    ):

        self.field = field
        self.serializer_class = serializer_class
        self.data_paths = data_path if isinstance(data_path, list) else [data_path]
        self.inclusion_path = inclusion_path

    def __repr__(self):
        return "%s(field=%r, serializer_class=%r, data_paths=%r, inclusion_path=%r)" % (
            self.__class__.__name__,
            self.field,
            self.serializer_class,
            self.data_paths,
            self.inclusion_path,
        )

    @property
    def _many(self) -> bool:
        return isinstance(self.field, ManyRelatedField)

    @property
    def queryset(self) -> models.QuerySet:
        if self._many:
            qs = self.field.child_relation.queryset
        else:
            qs = self.field.queryset
        # can happen if the field is set to read_only, see
        # rest_framework.relations.RelatedField.__init__
        if qs is None:
            model = self.serializer_class.Meta.model
            qs = model._default_manager.all()
        return qs

    @property
    def model_key(self) -> str:
        return self.queryset.model._meta.label

    @property
    def roots(self) -> List[str]:
        return [path.split(".")[0] for path in self.data_paths]

    def is_mergeable_with(self, other: "InclusionDefinition") -> bool:
        """
        Determine if an inclusion definition is mergeable with another one.

        Definitions are considered mergeable if:
        1. the ``inclusion_path`` is None
        2. both definitions have equivalent querysets (possibly relax this to the same model?)
        3. both definitions output to the same serializer_class
        """
        # 1. no inclusion_paths may be set
        if self.inclusion_path is not None or other.inclusion_path is not None:
            return False

        # 2. Both definitions need equivalent querysets.
        # NOTE: == is id(...) based anyway. This works out because the (automatic)
        # queryset determination for the field falls back to the _default_manager
        # .all() queryset (or it's explicitly defined), which is the same object
        # in memory. This is probably the most fragile part of this check.
        if self.queryset is not other.queryset:
            return False

        # 3. Must output to the same serializer
        if self.serializer_class is not other.serializer_class:
            return False

        return True


class Inclusion:
    """
    Abstract away the logic of merging, fetching and serializing included data.

    Each inclusion object knows which queryset, serializer class and PKs of
    related objects relate to itself. Using this information, it can output
    serialized data.

    Inclusion objects can be merged by the ``app_label.ModelName`` key.
    """

    def __init__(self, definition: InclusionDefinition):
        self.definition = definition
        self.serializer_class = definition.serializer_class

        self.resolved = False
        self.pks = set()

    def __repr__(self):
        return "<%s definition=%r resolved=%r>" % (
            self.__class__.__name__,
            self.definition,
            self.resolved,
        )

    @classmethod
    def merge(cls, *inclusions) -> list:
        """
        Merges inclusions based on model they encapsulate.

        Note that when inclusions are merged into a single inclusion, the
        serializer class and field from the first one are used, assuming all
        inclusions have the same serializer class and queryset.

        :returns: list of Inclusion objects, guaranteed to be unique in terms
          of model they represent.
        """
        inclusions_per_model = defaultdict(list)
        for inclusion in inclusions:
            inclusions_per_model[inclusion.definition.model_key].append(inclusion)

        inclusions = []
        for model_key, _inclusions in inclusions_per_model.items():
            # can't combine resolved and non-resolved inclusions
            resolved_inclusions = [incl for incl in _inclusions if incl.resolved]
            if resolved_inclusions:
                inclusion = cls(resolved_inclusions[0].definition)
                pks = set()
                for _inclusion in resolved_inclusions:
                    pks.update(_inclusion.pks)
                inclusion.resolve(pks)
                inclusions.append(inclusion)

            unresolved_inclusions = [incl for incl in _inclusions if not incl.resolved]

            if not unresolved_inclusions:
                continue

            # group by inclusion_path itself
            unresolved_inclusions = sorted(
                unresolved_inclusions, key=lambda incl: incl.definition.inclusion_path
            )
            for key, group in itertools.groupby(
                unresolved_inclusions, key=lambda incl: incl.definition.inclusion_path
            ):
                logger.debug("Inclusion for %s", key)
                group = list(group)
                inclusion = cls(group[0].definition)
                for _inclusion in group:
                    assert (
                        not _inclusion.pks
                    ), "Unresolved inclusions is not expected to have data"
                inclusions.append(inclusion)

        return inclusions

    def add_objects(self, pks: Union[list, set, int]):
        """
        Add primary keys to the inclusion.

        :param pks: either an iterable or a single integer representing the PK/
          list of PKs of a/mulitple related objects.
        """
        if isinstance(pks, int):
            pks = [pks]

        self.pks.update(pks)

    def resolve(self, pks: Union[list, set]) -> None:
        self.add_objects(pks)
        self.resolved = True

    @property
    def data(self) -> list:
        """
        Return the serialized data for the related objects.

        Initializes the configured serializer class with the objects based
        on ``self.pks``, and outputs the serializer data. The resulting
        objects are sorted on PK.
        """
        instances = self.definition.queryset.filter(pk__in=self.pks)
        serializer = self.definition.serializer_class(instance=instances, many=True)
        return serializer.data


def sort_key(item: OrderedDict) -> int:
    """
    Return the sort value for an item in a collection of included resources.

    Intended for nested, related objects that expose the ``id`` or ``pk`` field.

    :raises: ValueError if the PK cannot be determined.
    """
    if "id" in item:
        return item["id"]
    elif "pk" in item:
        return item["pk"]
    raise ValueError(
        "Item %r does not contain a reference to the 'id'. Please included it in the serializer."
        % item
    )


def is_inclusion_candidate(
    name: str, to_include: list, serializer: BaseSerializer
) -> bool:
    if name not in to_include:  # TODO; make more smark to handle nesting etc.
        return False

    inclusion_serializers = getattr(serializer, "inclusion_serializers", {})
    if name not in inclusion_serializers:
        return False

    return True


def get_inclusion_serializer_class(
    serializer: BaseSerializer, field_name: str
) -> Union[None, SerializerMetaclass]:
    if not hasattr(serializer, "inclusion_serializers"):
        return None

    inclusion_serializer_class = serializer.inclusion_serializers.get(field_name)
    if inclusion_serializer_class is None:
        return None

    if isinstance(inclusion_serializer_class, str):
        inclusion_serializer_class = import_string(inclusion_serializer_class)

    return inclusion_serializer_class


def get_nested(to_include: list) -> dict:
    nested = defaultdict(list)

    for fields in to_include:
        bits = fields.split(".")
        if len(bits) == 1:  # no nesting
            continue
        nested[bits[0]].append(".".join(bits[1:]))

    return nested


def flatten(iterable: list):
    """
    Flatten a list of lists into a list.

    Typically used to flatten a list of lists of serializer data into a list
    of serializer data.
    """
    for item in iterable:
        if not isinstance(item, list):
            item = [item]
        for obj in item:
            yield obj


def determine_inclusion_definitions(
    serializer: BaseSerializer,
    data_path_start=None,
    inclusion_path_start=None,
    references: dict = None,
) -> List[InclusionDefinition]:
    """
    Look at a serializer and determine which data inclusions are encapsulated.

    This method drills down into a serializer and extracts all the implied
    inclusions, keeping track of the data path from root to leaf nodes.
    """
    assert isinstance(serializer, BaseSerializer), "Needs an _instance_ of a serializer"

    # Serializer(many=True) wraps the actual serializer class, so we want to grab
    # that
    if hasattr(serializer, "child"):
        serializer = serializer.child

    inclusion_definitions = []

    for name, field in serializer.fields.items():

        # if it's a regular primitive-ish datatype -> nothing to do
        if not isinstance(field, (RelatedField, ManyRelatedField, BaseSerializer)):
            continue

        data_path = get_data_path(data_path_start, name)
        inclusion_path = get_inclusion_path(inclusion_path_start, name)

        # if we're dealing with a nested serializer, we need to recurse
        # TODO: protect against infite recursion
        if isinstance(field, BaseSerializer):
            inclusion_definitions += get_nested_inclusion_definitions(
                field, data_path, inclusion_path
            )
        else:
            inclusion_definitions += get_related_inclusion_definitions(
                serializer,
                name,
                field,
                data_path,
                inclusion_path,
                references=references,
            )

    return inclusion_definitions


def merge_inclusion_definitions(
    definitions: List[InclusionDefinition],
) -> List[InclusionDefinition]:
    """
    Merge inclusion definitions based on field/serializer.

    Merging definitions allows you to stay efficient in collecting the PK
    values to populate the data, while still allowing a simpler setup to figure
    out all the definitions for different data paths with the same inclusion.

    A merge is performed when definitions share the same field and
    ``serializer_class``, but have different ``data_path``s (and the
    ``inclusion_path`` is ``None``).
    """
    merged = []

    # keep a copy around to process the definitions. Anything that gets merged,
    # is removed from this, so we can just loop over the original definitions
    # without mutating the objects we're looping over (because that gets funky
    # and weird to debug).
    inputs = copy.copy(definitions)

    for definition in definitions:
        # skip if it was already processed
        if definition not in inputs:
            continue

        # find matching definitions
        matching_defs = [
            _definition
            for _definition in inputs
            if _definition.is_mergeable_with(definition)
            and _definition is not definition  # noqa
        ]

        data_paths = sum(
            (match.data_paths for match in matching_defs), definition.data_paths
        )

        # clean up our inputs
        inputs.remove(definition)
        for _definition in matching_defs:
            inputs.remove(_definition)

        # make the new definition, if not merge data is found, the original
        # definition is re-used
        merged.append(
            InclusionDefinition(
                field=definition.field,
                serializer_class=definition.serializer_class,
                data_path=data_paths,
                inclusion_path=definition.inclusion_path,
            )
        )

    return merged


def get_data_path(data_path_start, name):
    return name if data_path_start is None else f"{data_path_start}.{name}"


def get_inclusion_path(inclusion_path_start, name):
    if not inclusion_path_start:
        return None
    if ":" not in inclusion_path_start:
        return f"{inclusion_path_start}:{name}"
    else:
        return f"{inclusion_path_start}.{name}"


def get_related_inclusion_definitions(
    serializer, name, field, data_path, inclusion_path, references: dict = None
):
    references = references or {}
    # we are now sure we're dealing with a relational field that is not a
    # nested serializer. Inspect the inclusion definitions
    inclusion_serializer_class = get_inclusion_serializer_class(serializer, name)

    # very much possible that a FK is set up without inclusions
    if inclusion_serializer_class is None:
        return []

    referrer = (type(serializer), name)
    if inclusion_serializer_class not in references:
        references[inclusion_serializer_class] = [referrer]
    elif referrer not in references[inclusion_serializer_class]:
        references[inclusion_serializer_class].append(referrer)
    else:
        # referrer is already recorded before - we're detecting a circular reference
        return []

    # set up the definition - this is static and no data touches this
    definition = InclusionDefinition(
        field=field,
        serializer_class=inclusion_serializer_class,
        data_path=data_path,
        inclusion_path=inclusion_path,
    )

    # check if this serializer has its own inclusions
    return [definition] + determine_inclusion_definitions(
        inclusion_serializer_class(),
        data_path_start=data_path,
        inclusion_path_start=definition.model_key,
        references=references,
    )


def get_nested_inclusion_definitions(field, data_path, inclusion_path):
    return determine_inclusion_definitions(
        field, data_path_start=data_path, inclusion_path_start=inclusion_path
    )


def get_pks(serializer_data: Union[list, dict, None], data_path: str) -> list:
    # it's possible that serializer_data is none if there are optional PKs
    if serializer_data is None:
        return []

    pks = []

    if isinstance(serializer_data, list):
        for dct in serializer_data:
            pks += get_pks(dct, data_path)
    else:
        if "." in data_path:
            first_key, remainder = data_path.split(".", 1)
            pks += get_pks(serializer_data[first_key], data_path=remainder)
        else:
            _pks = serializer_data[data_path]
            if not isinstance(_pks, list):
                _pks = [_pks]
            pks += _pks
    return pks


def extract_inclusions(
    serializer: BaseSerializer,
    to_include: List[str],
    serializer_data: list,
    inclusion_definitions: list,
) -> List[Inclusion]:
    """
    Analyze the serializer and extract the related objects.

    The serializer fields are introspected and tested against the
    ``to_include`` list. If inclusions are needed, the related pks are
    extracted from ``serializer_data``.

    :param serializer: the (nested) serializer instance to introspect.
    :param to_include: a list of dotted paths drilling down into the
      serializer fields
    :param serializer_data: a list of 'instances' - the result of serializer.data

    :return: a list of Inclusion objects. Note that multiple Inclusion objects
      for the same model may be returned. You need to call Inclusion.merge(...)
      on these.
    """
    if not to_include:
        return []

    inclusions = []

    # figure out nested inclusions
    nested = get_nested(to_include)

    # Serializer(many=True) wraps the actual serializer class, so we want to grab
    # that
    if hasattr(serializer, "child"):
        serializer = serializer.child

    if to_include == ["*"]:
        _fields = list(serializer.fields.keys())
        to_include = _fields
        nested = {field: ["*"] for field in _fields}

    requested_roots = set(
        [include for include in to_include if "." not in include]
    ).union(set(nested))

    # first sweep - create the initial inclusions that can be resolved now,
    # because it does not depend on inclusions being resolved
    for definition in inclusion_definitions:
        relevant_roots = set(definition.roots).intersection(requested_roots)

        # this inclusion does not provide any requested roots, and it's also
        # not required for nested inclusions -> skip it alltogether
        if not relevant_roots and not definition.inclusion_path:
            continue

        inclusion = Inclusion(definition=definition)
        inclusions.append(inclusion)

        # inclusion path implies it needs to be resolved later after the first
        # sweep is completed
        if definition.inclusion_path:
            continue

        # collect the pks for the requested inclusions
        pks = []
        for root, data_path in zip(definition.roots, definition.data_paths):
            # this root path is not requested at all, so skip it
            if root not in relevant_roots:
                continue
            pks += get_pks(serializer_data, data_path)

        inclusion.resolve(pks)

    # merge them together
    inclusions = Inclusion.merge(*inclusions)

    resolved = {
        inclusion.definition.model_key: inclusion.data
        for inclusion in inclusions
        if inclusion.resolved
    }

    i = 0
    while not all(incl.resolved for incl in inclusions):
        i += 1
        assert (
            i < 200
        ), "Probably a bug in inclusions, this loop shouldn't run indefitinely"
        for inclusion in inclusions:
            if inclusion.resolved:
                continue

            model_key, data_path = inclusion.definition.inclusion_path.split(":")
            if model_key not in resolved:
                # it's possible this originates in a path from the root down
                # to something that isn't even needed to be included. in that case,
                # resolve on the empty dataset
                relevant_roots = set(inclusion.definition.roots).intersection(
                    requested_roots
                )
                if not relevant_roots:
                    inclusion.resolve([])
                continue

            pks = get_pks(resolved[model_key], data_path)
            inclusion.resolve(pks)

            # store for further resolutions
            resolved.setdefault(inclusion.definition.model_key, [])
            resolved[inclusion.definition.model_key] += inclusion.data

    return inclusions


def get_nested_inclusions(serializer: BaseSerializer, lookup: str) -> List[Inclusion]:
    """
    Given an inclusion serializer, figure out which deferred inclusions apply.

    Descent into all serializers to figure out all the possible inclusions.
    These inclusions are deferred which implies they fetch their data based on
    the earlier inclusions that resolve.

    An inclusion happens because a PK is referenced somewhere. This is
    transformed into serialized output, which may reveal more PKs of other
    included objects. These PKs are then merged and used to serialize the next
    batch of inclusions.
    """
    assert not hasattr(serializer, "child"), "Only Serializer(many=False) is supported"

    inclusions = []

    for name, field in serializer.fields.items():

        # an inclusion serializer is defined
        inclusion_serializer_class = get_inclusion_serializer_class(serializer, name)
        if inclusion_serializer_class is not None:
            inclusions.append(
                Inclusion(
                    field=field,
                    serializer_class=inclusion_serializer_class,
                    deferred=True,
                    lookup=f"{lookup}.{name}",
                )
            )

        elif isinstance(field, BaseSerializer):
            if hasattr(field, "child"):
                field = field.child

            inclusions += get_nested_inclusions(field, lookup=f"{lookup}.{name}")

    return inclusions


def hoist_inclusions(inclusions: List[Inclusion]) -> dict:
    """
    Merge all the extracted inclusions by model.

    Takes all the inclusion objects, and merges them by model key, returning
    the serializer data for each type of object.
    """
    merged = Inclusion.merge(*inclusions)
    hoisted = {
        inclusion.definition.model_key: sorted(inclusion.data, key=sort_key)
        for inclusion in merged
    }
    return hoisted
