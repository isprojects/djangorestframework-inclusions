from django.urls import reverse

import pytest
from rest_framework import serializers
from testapp.models import (
    Basic,
    BasicM2M,
    Company,
    ModelWithOptionalSub,
    ModelWithProperty,
    Sub,
    Tag,
)

from rest_framework_inclusions.core import InclusionLoader


@pytest.mark.django_db
def test_basic(client):
    company = Company.objects.create(name="SKYNET")
    basic = Basic.objects.create(name="You're basic", company=company)

    url = reverse("basic-detail", kwargs={"pk": basic.id})

    response = client.get(url, data={"include": "*"})

    assert response.json() == {
        "data": {"company": company.id, "name": "You're basic"},
        "inclusions": {"testapp.Company": [{"id": company.id, "name": "SKYNET"}]},
    }


@pytest.mark.django_db
def test_basic_m2m(client):
    tag1 = Tag.objects.create(name="One")
    tag2 = Tag.objects.create(name="Two")

    basic = BasicM2M.objects.create(name="You're basic m2m")
    basic.tags.set([tag1, tag2])

    url = reverse("basicm2m-detail", kwargs={"pk": basic.id})

    response = client.get(url, data={"include": "*"})

    assert response.json() == {
        "data": {"tags": [tag1.id, tag2.id], "name": "You're basic m2m"},
        "inclusions": {
            "testapp.Tag": [
                {"id": tag1.id, "name": "One"},
                {"id": tag2.id, "name": "Two"},
            ]
        },
    }


@pytest.mark.django_db
def test_only_inclusion_in_database():
    class NonModelCompanySerializer(serializers.Serializer):
        id = serializers.IntegerField()
        name = serializers.CharField()

    class NonModelSerializer(serializers.Serializer):
        inclusion_serializers = {"company": NonModelCompanySerializer}

        name = serializers.CharField()
        company = serializers.PrimaryKeyRelatedField(read_only=True)

    company = Company.objects.create(name="SKYNET")

    class Model:
        def __init__(self, name, company):
            self.name = name
            self.company = company

    model = Model(name="A", company=company)

    assert InclusionLoader(None).inclusions_dict(
        NonModelSerializer(instance=model)
    ) == {"testapp.Company": [{"id": company.id, "name": "SKYNET"}]}


@pytest.mark.django_db
def test_model_with_property(client):
    skynet = Company.objects.create(name="SKYNET")
    ocp = Company.objects.create(name="Omni Consumer Products")
    Basic.objects.create(name="A", company=skynet)
    Basic.objects.create(name="B", company=ocp)

    obj = ModelWithProperty.objects.create()

    url = reverse("modelwithproperty-detail", kwargs={"pk": obj.id})

    response = client.get(url, data={"include": "*"})

    assert response.json() == {
        "data": {
            "basics": [
                {"name": "A", "company": skynet.id},
                {"name": "B", "company": ocp.id},
            ],
            "basics_list": [
                {"name": "A", "company": skynet.id},
                {"name": "B", "company": ocp.id},
            ],
        },
        "inclusions": {
            "testapp.Company": [
                {"id": 1, "name": "SKYNET"},
                {"id": 2, "name": "Omni Consumer Products"},
            ]
        },
    }


@pytest.mark.django_db
def test_model_with_optional_sub(client):
    skynet = Company.objects.create(name="SKYNET")
    sub = Sub.objects.create(name="SUB", company=skynet)
    obj = ModelWithOptionalSub.objects.create(sub=sub)
    obj_without_sub = ModelWithOptionalSub.objects.create()

    url = reverse("modelwithoptionalsub-detail", kwargs={"pk": obj.id})
    response = client.get(url, data={"include": "*"})

    assert response.json() == {
        "data": {"sub": {"name": "SUB", "company": skynet.id, "sub_sub": None}},
        "inclusions": {"testapp.Company": [{"id": skynet.id, "name": "SKYNET"}]},
    }

    # this will trigger a SkipField when we try to get the sub_sub attribute
    url = reverse("modelwithoptionalsub-detail", kwargs={"pk": obj_without_sub.id})
    response = client.get(url, data={"include": "*"})

    assert response.json() == {
        "data": {"sub": None},
        "inclusions": {},
    }


@pytest.mark.django_db
def test_basic_many(client):
    company = Company.objects.create(name="SKYNET")
    Basic.objects.create(name="You're basic", company=company)
    Basic.objects.create(name="You too", company=company)

    # a detail=False route that gives back a many=True serializer
    url = reverse("basic-many")
    response = client.get(url, data={"include": "*"})
    assert response.json() == {
        "data": [
            {"name": "You're basic", "company": company.id},
            {"name": "You too", "company": company.id},
        ],
        "inclusions": {"testapp.Company": [{"id": company.id, "name": "SKYNET"}]},
    }
