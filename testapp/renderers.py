from rest_framework_inclusions.renderer import InclusionJSONRenderer

from .loaders import CustomInclusionLoader


class CustomInclusionJSONRenderer(InclusionJSONRenderer):
    loader_class = CustomInclusionLoader
    response_data_key = "custom_data"
    response_inclusions_key = "custom_inclusions"
