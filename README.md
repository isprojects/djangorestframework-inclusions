# DRF-inclusions

A django-restframework renderer to side-load related resources.

[![Build status][build-status]][travis]
[![Coverage status][coverage]][codecov]
![Python versions][python-versions]
![Django versions][django-versions]
[![PyPI][pypi-version]][pypi]


[build-status]: https://travis-ci.org/isprojects/rest-framework-inclusions.svg?branch=develop
[travis]: https://travis-ci.org/isprojects/rest-framework-inclusions
[coverage]: https://codecov.io/gh/isprojects/rest-framework-inclusions/branch/develop/graph/badge.svg
[codecov]: https://codecov.io/gh/isprojects/rest-framework-inclusions
[python-versions]: https://img.shields.io/pypi/pyversions/djangorestframework-inclusions.svg
[django-versions]: https://img.shields.io/pypi/djversions/djangorestframework-inclusions.svg
[pypi-version]: https://img.shields.io/pypi/v/djangorestframework-inclusions.svg
[pypi]: https://pypi.org/project/djangorestframework-inclusions/


One drawback of RESTful APIs is that you have to make _many_ calls to fetch all
the related resources. DRF-inclusions provides a custom renderer allowing you
to sideload those in a single, original request.

DRF-inclusions allows you to specify which serializers to use for included
resources, and via the query string the client can specify which resources
should be included.

Features:

* arbitrary depth
* option to include _all_ related resources
* de-duplication when the same object is found in multiple parent/related
  objects
* an effort is made to retrieve related objects in as little DB queries as possible

## Installation

```bash
pip install djangorestframework-inclusions
```

## Usage

```python
from rest_framework_inclusions.renderer import InclusionJSONRenderer


class MySerializer(...):
    inclusion_serializers = {"some_field": OtherSerializer}


class MyViewSet(...):
    ...
    renderer_classes = (InclusionJSONRenderer,)
```

See the `tests` and `testapp` for advanced usage examples.
