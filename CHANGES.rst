1.2.0 (unreleased)
------------------

- Make `djangorestframework-inclusions` compatible with both Python 3.9 and 3.11 and both Django 3.2 and 4.2


1.1.0 (2020-03-26)
------------------

The old approach would generate a new database query for each inclusion made.
This meant that Django mechanisms such as select_related and prefetch_related
to optimize queryset performance had no effect, and it became harder to debug
the performance hotspots of applications.

This approach reuses the Django ORM itself to fetch objects: it just accesses
the underlying attributes. If an object is already fetched before, it is
therefore be reused and no new query will be issued.

There is one (small) limitation to the new approach: in the case of many
serializers, if your return an iterable of results (instead of a list), the
system gets an empty list as the iterable is already exhausted earlier. This is
easy to fix by using list() before passing this to this library.

While all existing tests still pass, it's possible that the mechanism to
include specific field (as opposed to include=) has changed its behavior in the
face of inclusions within inclusions.
