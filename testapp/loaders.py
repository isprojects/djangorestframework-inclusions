from rest_framework_inclusions.core import InclusionLoader


class CustomInclusionLoader(InclusionLoader):
    nested_inclusions_use_complete_path = True

    def get_model_key(self, obj, *args, **kwargs):
        return f"prefix:{obj._meta.label}"
