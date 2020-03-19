from django.urls import reverse

from rest_framework.test import APITestCase
from testapp.models import (
    A,
    B,
    C,
    Child,
    ChildProps,
    Container,
    Entry,
    MainObject,
    Parent,
    Tag,
)

from .mixins import InclusionsMixin


class ReferenceTests(InclusionsMixin, APITestCase):

    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.tag1 = Tag.objects.create(name="you")
        cls.tag2 = Tag.objects.create(name="are")
        cls.tag3 = Tag.objects.create(name="it")

        cls.parent1 = Parent.objects.create(name="Papa Johns")
        cls.parent1.tags.set([cls.tag1, cls.tag2])

        cls.parent2 = Parent.objects.create(name="Papa Roach")
        cls.parent2.tags.set([cls.tag2])

        cls.child1 = Child.objects.create(parent=cls.parent1, name="Children of Bodom")
        cls.child2 = Child.objects.create(parent=cls.parent1, name="Children of Men")

        cls.child1.tags.set([cls.tag3])

        cls.parent1.favourite_child = cls.child2
        cls.parent1.save()

        cls.childprops = ChildProps.objects.create(child=cls.child2)

        cls.container1 = Container.objects.create(name="container 1")
        cls.container1.save()

        cls.entryA = Entry.objects.create(name="A", container=cls.container1)
        cls.entryA.tags.set([cls.tag1])
        cls.entryA.save()

        cls.entryB = Entry.objects.create(name="B", container=cls.container1)
        cls.entryB.tags.set([cls.tag3])
        cls.entryB.save()

    def test_tag_list(self):  # without pagination
        expected = {
            "data": [
                {"id": self.tag1.id, "name": "you"},
                {"id": self.tag2.id, "name": "are"},
                {"id": self.tag3.id, "name": "it"},
            ],
            "inclusions": {},
        }
        self.assertResponseData("tag-list", expected)

    def test_tag_detail(self):
        expected = {"data": {"id": self.tag1.id, "name": "you"}, "inclusions": {}}
        self.assertResponseData("tag-detail", expected, pk=self.tag1.pk)

    def test_custom_action_no_inclusion_serializer(self):
        """
        Assert that custom actions with inclusion renderer don't trigger
        inclusion machinery.
        """
        expected = [
            {"id": self.tag1.id, "name": "you"},
            {"id": self.tag2.id, "name": "are"},
            {"id": self.tag3.id, "name": "it"},
        ]
        self.assertResponseData("tag-custom-action", expected)

    def test_custom_action_inclusion_serializer(self):
        """
        Assert that the inclusion machinery does kick in if inclusion
        serializers are involved.
        """
        entry_c = C.objects.create()

        expected = {"data": {"id": entry_c.id, "b": None}, "inclusions": {}}

        self.assertResponseData("c-custom-action", expected, pk=entry_c.pk)

    def test_parent_list(self):  # with pagination
        expected = {
            "count": 2,
            "previous": None,
            "next": None,
            "data": [
                {
                    "id": self.parent1.id,
                    "name": "Papa Johns",
                    "tags": [self.tag1.id, self.tag2.id],
                    "favourite_child": self.child2.pk,
                },
                {
                    "id": self.parent2.id,
                    "name": "Papa Roach",
                    "tags": [self.tag2.id],
                    "favourite_child": None,
                },
            ],
            "inclusions": {},
        }
        self.assertResponseData("parent-list", expected)

    def test_parent_list_include_tags(self):
        expected = {
            "count": 2,
            "previous": None,
            "next": None,
            "data": [
                {
                    "id": self.parent1.id,
                    "name": "Papa Johns",
                    "tags": [self.tag1.id, self.tag2.id],
                    "favourite_child": self.child2.pk,
                },
                {
                    "id": self.parent2.id,
                    "name": "Papa Roach",
                    "tags": [self.tag2.id],
                    "favourite_child": None,
                },
            ],
            "inclusions": {
                "testapp.Tag": [
                    {"id": self.tag1.id, "name": "you"},
                    {"id": self.tag2.id, "name": "are"},
                ]
            },
        }
        self.assertResponseData("parent-list", expected, params={"include": "tags"})

    def test_parent_detail(self):
        expected = {
            "data": {
                "id": self.parent2.id,
                "name": "Papa Roach",
                "tags": [self.tag2.id],
                "favourite_child": None,
            },
            "inclusions": {},
        }
        self.assertResponseData("parent-detail", expected, pk=self.parent2.pk)

    def test_parent_detail_with_include(self):
        expected = {
            "data": {
                "id": self.parent2.id,
                "name": "Papa Roach",
                "tags": [self.tag2.id],
                "favourite_child": None,
            },
            "inclusions": {"testapp.Tag": [{"id": self.tag2.id, "name": "are"}]},
        }
        self.assertResponseData(
            "parent-detail", expected, pk=self.parent2.pk, params={"include": "*"}
        )

    def test_nested_include(self):
        expected = {
            "data": {
                "id": self.child2.id,
                "name": "Children of Men",
                "childprops": self.childprops.id,
                "parent": {
                    "id": self.parent1.id,
                    "name": "Papa Johns",
                    "tags": [self.tag1.id, self.tag2.id],
                    "favourite_child": self.child2.id,
                },
                "tags": [],
            },
            "inclusions": {
                "testapp.Tag": [
                    {"id": self.tag1.id, "name": "you"},
                    {"id": self.tag2.id, "name": "are"},
                ]
            },
        }
        self.assertResponseData(
            "child-detail",
            expected,
            params={"include": "parent.tags"},
            pk=self.child2.pk,
        )

    def test_include_all_detail(self):
        expected = {
            "data": {
                "id": self.child2.id,
                "name": "Children of Men",
                "childprops": self.childprops.id,
                "parent": {
                    "id": self.parent1.id,
                    "name": "Papa Johns",
                    "tags": [self.tag1.id, self.tag2.id],
                    "favourite_child": self.child2.id,
                },
                "tags": [],
            },
            "inclusions": {
                "testapp.Tag": [
                    {"id": self.tag1.id, "name": "you"},
                    {"id": self.tag2.id, "name": "are"},
                ],
                "testapp.ChildProps": [
                    {"id": self.childprops.id, "child": self.child2.pk}
                ],
            },
        }
        self.assertResponseData(
            "child-detail", expected, params={"include": "*"}, pk=self.child2.pk
        )

    def test_include_all_list(self):
        expected = {
            "count": 2,
            "next": None,
            "previous": None,
            "data": [
                {
                    "id": self.child1.id,
                    "name": "Children of Bodom",
                    "childprops": None,
                    "parent": {
                        "id": self.parent1.id,
                        "name": "Papa Johns",
                        "tags": [self.tag1.id, self.tag2.id],
                        "favourite_child": self.child2.id,
                    },
                    "tags": [self.tag3.id],
                },
                {
                    "id": self.child2.id,
                    "name": "Children of Men",
                    "childprops": self.childprops.id,
                    "parent": {
                        "id": self.parent1.id,
                        "name": "Papa Johns",
                        "tags": [self.tag1.id, self.tag2.id],
                        "favourite_child": self.child2.id,
                    },
                    "tags": [],
                },
            ],
            "inclusions": {
                "testapp.Tag": [
                    {"id": self.tag1.id, "name": "you"},
                    {"id": self.tag2.id, "name": "are"},
                    {"id": self.tag3.id, "name": "it"},
                ],
                "testapp.ChildProps": [
                    {"id": self.childprops.id, "child": self.child2.pk}
                ],
            },
        }
        self.assertResponseData("child-list", expected, params={"include": "*"})

    def test_include_fk_field(self):
        expected = {
            "data": {
                "id": self.child2.id,
                "name": "Children of Men",
                "childprops": self.childprops.id,
                "parent": {
                    "id": self.parent1.id,
                    "name": "Papa Johns",
                    "tags": [self.tag1.id, self.tag2.id],
                    "favourite_child": self.child2.id,
                },
                "tags": [],
            },
            "inclusions": {
                "testapp.ChildProps": [
                    {"id": self.childprops.id, "child": self.child2.id}
                ]
            },
        }
        self.assertResponseData(
            "child-detail",
            expected,
            params={"include": "childprops"},
            pk=self.child2.pk,
        )

    def test_flattened_inclusions(self):
        expected = {
            "data": {
                "id": self.child1.id,
                "name": "Children of Bodom",
                "childprops": None,
                "parent": {
                    "id": self.parent1.id,
                    "name": "Papa Johns",
                    "tags": [self.tag1.id, self.tag2.id],
                    "favourite_child": self.child2.id,
                },
                "tags": [self.tag3.id],
            },
            "inclusions": {
                "testapp.Tag": [
                    {"id": self.tag1.id, "name": "you"},
                    {"id": self.tag2.id, "name": "are"},
                    {"id": self.tag3.id, "name": "it"},
                ]
            },
        }
        self.assertResponseData(
            "child-detail",
            expected,
            params={"include": "tags,parent.tags"},
            pk=self.child1.pk,
        )

    def test_nested_include_multiple_from_same_child(self):
        self.child2.tags.set([self.tag1])
        self.addCleanup(self.child2.tags.clear)

        expected = {
            "data": {
                "id": self.childprops.id,
                "child": {
                    "id": self.child2.id,
                    "parent": self.parent1.id,
                    "tags": [self.tag1.id],
                },
            },
            "inclusions": {
                "testapp.Tag": [
                    {"id": self.tag1.id, "name": "you"},
                    {
                        "id": self.tag2.id,
                        "name": "are",
                    },  # included from Parent inclusion
                ],
                "testapp.Parent": [
                    {
                        "id": self.parent1.id,
                        "name": "Papa Johns",
                        "tags": [self.tag1.id, self.tag2.id],
                        "favourite_child": self.child2.id,
                    }
                ],
            },
        }

        self.assertResponseData(
            "childprops-detail",
            expected,
            params={"include": "child.tags,child.parent"},
            pk=self.childprops.pk,
        )

    def test_many(self):
        expected = {
            "data": {
                "entries": [
                    {"id": self.entryA.id, "name": "A", "tags": [self.tag1.id]},
                    {"id": self.entryB.id, "name": "B", "tags": [self.tag3.id]},
                ],
                "id": self.container1.id,
                "name": "container 1",
            },
            "inclusions": {
                "testapp.Tag": [
                    {"id": self.tag1.id, "name": "you"},
                    {"id": self.tag3.id, "name": "it"},
                ]
            },
        }

        self.assertResponseData(
            "container-detail",
            expected,
            params={"include": "entries.tags"},
            pk=self.container1.pk,
        )

    def test_post(self):
        url = reverse("parent-list")

        response = self.client.post(
            url, {"name": "Papa Post", "tags": [self.tag2.id], "favourite_child": None}
        )

        json = response.json()
        json["data"].pop("id")
        self.assertEqual(
            json,
            {
                "data": {
                    "favourite_child": None,
                    "name": "Papa Post",
                    "tags": [self.tag2.id],
                },
                "inclusions": {},
            },
        )

    def test_post_with_error(self):
        url = reverse("parent-list")
        response = self.client.post(url, {"wrong": "WRONG"})
        json = response.json()
        # things should not be wrapped in data
        self.assertEqual(
            json,
            {"name": ["This field is required."], "tags": ["This field is required."]},
        )

    def test_post_with_non_field_error(self):
        url = reverse("parent-list")
        response = self.client.post(url, {"name": "Trigger", "tags": [self.tag2.id]})
        json = response.json()
        # things should not be wrapped in data
        self.assertEqual(json, {"invalid": "WRONG"})

    def test_list_action(self):
        url = reverse("parent-check")
        response = self.client.post(url, {"random": "data"})
        json = response.json()
        self.assertEqual(json, {"arbitrary": "content"})

    def test_detail_action(self):
        url = reverse("parent-check2", kwargs={"pk": self.parent1.pk})
        response = self.client.post(url, {"random": "data"})
        json = response.json()
        self.assertEqual(json, {"arbitrary": "content"})

    def test_read_only_inclusions(self):
        """
        NEXT-827 -- Inclusions should work with read-only fields.
        """
        expected = {
            "count": 2,
            "previous": None,
            "next": None,
            "data": [
                {"id": self.entryA.id, "name": "A", "tags": [self.tag1.id]},
                {"id": self.entryB.id, "name": "B", "tags": [self.tag3.id]},
            ],
            "inclusions": {
                "testapp.Tag": [
                    {"id": self.tag1.id, "name": "you"},
                    {"id": self.tag3.id, "name": "it"},
                ]
            },
        }
        self.assertResponseData("entry-list", expected, params={"include": "tags"})

    def test_nullable_relation(self):
        """
        NEXT-856 -- requesting inclusions of nullable relations shouldn't crash.
        """
        a1 = A.objects.create()
        b1 = B.objects.create()
        c1 = C.objects.create()

        b2 = B.objects.create(a=a1)
        c2 = C.objects.create(b=b2)

        c3 = C.objects.create(b=b1)

        expected = {
            "count": 3,
            "previous": None,
            "next": None,
            "data": [
                {"id": c1.id, "b": None},
                {"id": c2.pk, "b": {"id": b2.id, "a": a1.id}},
                {"id": c3.pk, "b": {"id": b1.id, "a": None}},
            ],
            "inclusions": {"testapp.A": [{"id": a1.id}]},
        }
        self.assertResponseData("c-list", expected, params={"include": "b.a"})

    def test_reverse_relation(self):
        """
        NEXT-1052 revealed a problem in inclusions.

        Response data in the form of:

        [{
            'external_notifications':  [],
        }]

        where an inclusion field is in the ExernalNotification serializer
        bugged out.
        """
        main_object = MainObject.objects.create()
        # no actual related objects exist in database

        expected = {
            "data": [{"id": main_object.id, "relatedobject_set": []}],
            "inclusions": {},
        }
        self.assertResponseData("mainobject-list", expected, params={"include": "*"})
