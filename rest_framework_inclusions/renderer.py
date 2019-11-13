import logging
from collections import OrderedDict
from typing import Callable

from rest_framework import renderers, serializers
from rest_framework.utils.serializer_helpers import ReturnDict

from .data_inclusion import (
    determine_inclusion_definitions,
    extract_inclusions,
    hoist_inclusions,
    merge_inclusion_definitions,
)

logger = logging.getLogger(__name__)


def has_inclusion_serializers(serializer: serializers.Serializer) -> bool:
    # Serializer(many=True) wraps the actual serializer class, so we want to grab that
    if hasattr(serializer, "child"):
        serializer = serializer.child

    # the attribute may be defined, but empty, so we do a truthy-check instead of just
    # checking for None
    inclusion_serializers = getattr(serializer, "inclusion_serializers", None)
    if inclusion_serializers:
        return True

    child_serializers = (
        child
        for child in serializer.fields.values()
        if isinstance(child, serializers.BaseSerializer)
    )
    return any(has_inclusion_serializers(child) for child in child_serializers)


def should_skip_inclusions(
    action: Callable, serializer: serializers.Serializer
) -> bool:
    """
    Determine if the inclusion machinery needs to be skipped or not.

    The inclusion renderer is specified on the viewset, which applies it to
    custom actions using serializers as well. If those serializers don't use
    inclusions anywhere (lack of ``inclusion_serializers`` attribute down
    the entire stack), the inclusion machinery can safely be skipped.
    """

    # determine if it's a custom action or not - the decorator sets all of these
    # attributes for custom actions
    action_attrs = ["mapping", "detail", "url_path", "url_name", "kwargs"]
    if not all((hasattr(action, attr) for attr in action_attrs)):
        return False
    return not has_inclusion_serializers(serializer)


class InclusionJSONRenderer(renderers.JSONRenderer):
    """
    Support the ?include querystring parameter in the JSONRenderer.

    Serializers can refer to related objects in two ways (massively simplified):

    * by including the PK in the serializer body
    * or by including a nested object in the serializer body

    Conditional 'expansion' can be triggered on a per-request basis, by
    including the querystring parameter ``?include=some_field``, which causes
    the related objects to appear in the top-level ``'inclusions'`` key.
    Within this object, inclusions are keyed by the model
    ``app_label.ModelName``.

    Note that inclusions must be white-listed on the serializer, e.g.:

    .. code-block:: python

        class ChildSerializer(serializers.ModelSerializer):
            inclusion_serializers = {
                'parent': ParentSerializer,
            }

            class Meta:
                model = Child
                fields = ('id', 'name', 'parent')

    The inclusions can refer to multiple fields, separate them with a comma::

        GET /api/v1/endpoint/?include=field1,field2

    The inclusions can drill down into nested objects using dot-notation, e.g.
    if parent is nested in child, you can do::

        GET /api/v1/endpoint/?include=parent.tags

    This requires the ``inclusion_serializers`` to be set on the Parent
    serializer class.

    Specifying this renderer on a ViewSet will apply the inclusions machinery
    on custom actions ONLY if the serializers used have inclusion machinery
    configured - i.e. down the serializer stack (e.g. serializer with nested
    serializers), somewhere a serializer should be defining the
    ``inclusion_serializers`` attribute.

    Known limitations:

    * nested inclusions only work with a nested serializer:
      if Child.parent is defined as nested serializer, it's fine and you can
      refer to Child.parent.tags, but if parent is just a regular RelatedField,
      the behaviour is undefined, untested and probably doesn't work as
      expected.

    * Inclusions are hoisted from arbitrary depth and grouped per model. If a
      nested object uses the same related model as the root object(s) (e.g.
      Tag relation on both Parent and Child), but the root and nested
      serializers for the related model use different serializers in the
      ``inclusion_serializers`` definition, the behaviour is undefined. You
      will get results back, but it may not be the serializer you expected.

      This is because of the de-duplication happening during hoisting, and the
      first serializer that's encountered is used.

    * Inclusion of related objects does no permissions checking. You need to
      make sure that the serializers themselves only include data that may be
      disclosed.

    * Currently ``RelatedField`` and ``ManyRelatedField`` (based on PKs) are
      supported. Variations such as ``HyperLinkedRelatedField`` are untested
      and unsupported.
    """

    def extract_relations(self, request, serializer, serializer_data) -> OrderedDict:
        """
        Extract the relations from PK fields and add them to the inclusions.
        """
        inclusions = OrderedDict()

        inclusions_requested = request.GET.get("include") if request else None
        to_include = inclusions_requested.split(",") if inclusions_requested else []

        if not getattr(serializer, "many", False):
            serializer_data = [serializer_data]

        # first sweep - inspect the serializer (graph) structure and figure out
        # which inclusions should all be loaded at the end
        inclusion_definitions = determine_inclusion_definitions(serializer)
        inclusion_definitions = merge_inclusion_definitions(inclusion_definitions)

        # second sweep - populate PK data from the root node
        inclusions = extract_inclusions(
            serializer, to_include, serializer_data, inclusion_definitions
        )

        return hoist_inclusions(inclusions)

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Re-organize the response data in top-level ``data`` and ``inclusions`` keys.

        The 'main' data is parked under a top-level ``data`` key in the
        response. Pagination/extra meta information is kept in the root.

        The object ``inclusions`` is added to the top level, and contains lists
        of included, related objects, keyed by ``app_label.ModelName``.

        Works for both detail and list responses.
        """
        renderer_context = renderer_context or {}
        response = renderer_context.get("response")
        # if we have an error, return data as-is
        if response is not None and response.status_code >= 400:
            return super().render(data, accepted_media_type, renderer_context)

        if data and "results" in data:
            serializer_data = data["results"]
        else:
            serializer_data = data

        serializer = getattr(serializer_data, "serializer", None)
        # if there is no serializer (like for a viewset action())
        # we just pass the data through as-is
        if serializer is None:
            return super().render(data, accepted_media_type, renderer_context)

        # if it's a custom action, and the serializer has no inclusions, return the normal response
        view = renderer_context.get("view")
        if view is not None and hasattr(view, "action"):
            if not view.action:
                logger.debug("Skipping inclusions for view that has no action")
                return super().render(data, accepted_media_type, renderer_context)
            action = getattr(view, view.action)
            if should_skip_inclusions(action, serializer):
                logger.debug(
                    "Skipping inclusion machinery for custom action %r", action
                )
                return super().render(data, accepted_media_type, renderer_context)

        request = renderer_context.get("request")
        inclusions = self.extract_relations(request, serializer, serializer_data)

        render_data = OrderedDict()
        # map the meta information, if any
        render_data["data"] = serializer_data
        render_data["inclusions"] = inclusions

        # extract keys like pagination information
        if isinstance(data, dict) and not isinstance(data, ReturnDict):
            for key, value in data.items():
                if key == "results":
                    continue
                render_data[key] = value

        return super().render(render_data, accepted_media_type, renderer_context)
