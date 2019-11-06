import unittest

from rest_framework.test import APITestCase
from testapp.models import A, B, C, Child, D, E, Parent, Tag

from .mixins import InclusionsMixin


class InclusionsLoadInclusionsTests(InclusionsMixin, APITestCase):
    """
    Tests for chained inclusions.

    Serializers used for inclusions may (indirectly) reference other
    serializers to be used for inclusions. Inclusions should be loaded all
    the way down the tree, and as effiently as possible.
    """

    def test_direct_nested_inclusion(self):
        """
        Assert that inclusions from inclusion serializers are loaded.
        """
        a = A.objects.create()
        b = B.objects.create(a=a)
        c = C.objects.create(b=b)

        expected = {
            "data": [{"id": c.id, "b": b.id}],
            "inclusions": {
                "testapp.A": [{"id": a.id}],
                "testapp.B": [{"id": b.id, "a": a.id}],
            },
        }

        self.assertResponseData("c-nested-list", expected, params={"include": "*"})

    def test_indirect_inclusion(self):
        """
        Assert that indirect inclusions from serializers are loaded.
        """
        a = A.objects.create()
        b = B.objects.create(a=a)
        c = C.objects.create(b=b)

        expected = {
            "count": 1,
            "previous": None,
            "next": None,
            "data": [{"id": c.id, "b": {"id": b.id, "a": a.id}}],
            "inclusions": {"testapp.A": [{"id": a.id}]},
        }

        self.assertResponseData("c-list", expected, params={"include": "*"})

    def test_inclusions_same_datamodel_different_levels(self):
        """
        Assert that the same datamodel in different places loads correctly.

        A primary serializer defines an inclusion to a model, and that
        inclusion references the same model but other data. The data must
        be merged together and hoisted correctly.
        """
        tag1 = Tag.objects.create(name="tag1")
        tag2 = Tag.objects.create(name="tag2")
        Tag.objects.create(name="tag3")

        parent = Parent.objects.create(name="parent")
        parent.tags.set([tag1])

        child = Child.objects.create(name="child", parent=parent)
        child.tags.set([tag2])

        expected = {
            "count": 1,
            "previous": None,
            "next": None,
            "data": [{"id": child.id, "parent": child.parent_id, "tags": [tag2.id]}],
            "inclusions": {
                "testapp.Parent": [
                    {
                        "id": parent.id,
                        "name": "parent",
                        "favourite_child": None,
                        "tags": [tag1.pk],
                    }
                ],
                "testapp.Tag": [
                    {"id": tag1.id, "name": "tag1"},
                    {"id": tag2.id, "name": "tag2"},
                ],
            },
        }

        self.assertResponseData("child2-list", expected, params={"include": "*"})

    def test_circular_references(self):
        """
        Assert that circular serializer references resolve.

        A serializer is set up in such a way that the inclusions eventually
        cycle back to itself. These circular references must resolve and
        include all the data.
        """
        parent = Parent.objects.create(name="parent")
        child1 = Child.objects.create(name="child1", parent=parent)
        child2 = Child.objects.create(name="child2", parent=parent)
        parent.favourite_child = child1
        parent.save()

        expected = {
            "data": {"id": child2.id, "parent": parent.id},
            "inclusions": {
                "testapp.Parent": [{"id": parent.id, "favourite_child": child1.pk}],
                "testapp.Child": [{"id": child1.pk, "parent": parent.id}],
            },
        }

        self.assertResponseData(
            "child3-detail", expected, pk=child2.pk, params={"include": "*"}
        )

    @unittest.skip("Not implemented yet")
    def test_inclusion_adds_more_objects(self):
        """
        Assert that fresh data is included

        An inclusion can have inclusions of itself, which should be added. But
        those extra inclusions may also cause extra instances of an earlier
        inclusion to be added. An inclusion cannot be 'finalized' if there's
        still data being added.
        """
        raise NotImplementedError

    def test_same_inclusion_serializer_different_paths(self):
        """
        Assert that re-use of an inclusion serializer doesn't crash.
        """
        tag1 = Tag.objects.create(name="tag 1")
        tag2 = Tag.objects.create(name="tag 2")  # noqa
        tag3 = Tag.objects.create(name="tag 3")
        d = D.objects.create()
        d.tags1.set([tag1])
        d.tags2.set([tag1, tag3])
        e = E.objects.create(d=d)

        expected = {
            "count": 1,
            "previous": None,
            "next": None,
            "data": [{"id": e.id, "d": d.id}],
            "inclusions": {
                "testapp.D": [
                    {"id": d.id, "tags1": [tag1.id], "tags2": [tag1.id, tag3.id]}
                ],
                "testapp.Tag": [
                    {"id": tag1.id, "name": "tag 1"},
                    {"id": tag3.id, "name": "tag 3"},
                ],
            },
        }

        self.assertResponseData("e-list", expected, params={"include": "*"})
