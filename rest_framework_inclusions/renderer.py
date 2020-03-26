import logging
from collections import OrderedDict
from typing import Callable

from rest_framework import renderers, serializers
from rest_framework.utils.serializer_helpers import ReturnDict

from .core import InclusionLoader

logger = logging.getLogger(__name__)


class InclusionJSONRenderer(renderers.JSONRenderer):
    def _render_inclusions(self, data, renderer_context):
        renderer_context = renderer_context or {}
        response = renderer_context.get("response")
        # if we have an error, return data as-is
        if response is not None and response.status_code >= 400:
            return None

        if data and "results" in data:
            serializer_data = data["results"]
        else:
            serializer_data = data

        serializer = getattr(serializer_data, "serializer", None)
        # if there is no serializer (like for a viewset action())
        # we just pass the data through as-is
        if serializer is None:
            return None

        # if it's a custom action, and the serializer has no inclusions,
        # return the normal response
        view = renderer_context.get("view")
        if view is not None and hasattr(view, "action"):
            if not view.action:
                logger.debug("Skipping inclusions for view that has no action")
                return None
            action = getattr(view, view.action)
            if should_skip_inclusions(action, serializer):
                logger.debug(
                    "Skipping inclusion machinery for custom action %r", action
                )
                return None

        request = renderer_context.get("request")

        inclusions = InclusionLoader(get_allowed_paths(request)).inclusions_dict(
            serializer
        )

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

        return render_data

    def render(self, data, accepted_media_type=None, renderer_context=None):
        render_data = self._render_inclusions(data, renderer_context)
        if not render_data:
            return super().render(data, accepted_media_type, renderer_context)
        return super().render(render_data, accepted_media_type, renderer_context)


def get_allowed_paths(request):
    include = request.GET.get("include") if request else None
    if include is None:
        # nothing is allowed
        return set()
    if include == "*":
        # everything is allowed
        return None
    return [tuple(entry.split(".")) for entry in include.split(",")]


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
