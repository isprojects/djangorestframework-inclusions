from rest_framework import serializers

from .models import (
    A,
    B,
    Basic,
    BasicM2M,
    C,
    Child,
    ChildProps,
    Company,
    Container,
    D,
    E,
    Entry,
    MainObject,
    ModelWithOptionalSub,
    ModelWithProperty,
    Parent,
    RelatedObject,
    SecondLevelRelatedObject,
    Sub,
    SubSub,
    Tag,
)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = "__all__"


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "name"]


class BasicSerializer(serializers.ModelSerializer):
    inclusion_serializers = {"company": CompanySerializer}

    class Meta:
        model = Basic
        fields = ["name", "company"]


class BasicM2MSerializer(serializers.ModelSerializer):
    inclusion_serializers = {"tags": TagSerializer}

    class Meta:
        model = BasicM2M
        fields = ["name", "tags"]


class ParentSerializer(serializers.ModelSerializer):

    inclusion_serializers = {"tags": TagSerializer}

    class Meta:
        model = Parent
        fields = "__all__"

    def create(self, validated_data):
        if validated_data.get("name") == "Trigger":
            raise serializers.ValidationError({"invalid": "WRONG"})

        return super().create(validated_data)


class ParentSerializer2(serializers.ModelSerializer):
    inclusion_serializers = {"favourite_child": "testapp.serializers.ChildSerializer3"}

    class Meta:
        model = Parent
        fields = ("id", "favourite_child")


class ChildPropsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChildProps
        fields = "__all__"


class ChildSerializer(serializers.ModelSerializer):
    parent = ParentSerializer()

    inclusion_serializers = {"childprops": ChildPropsSerializer, "tags": TagSerializer}

    class Meta:
        model = Child
        fields = ("id", "parent", "name", "childprops", "tags")


class ChildSerializer2(serializers.ModelSerializer):

    inclusion_serializers = {"parent": ParentSerializer, "tags": TagSerializer}

    class Meta:
        model = Child
        fields = ("id", "parent", "tags")


class ChildSerializer3(serializers.ModelSerializer):

    inclusion_serializers = {"parent": ParentSerializer2}

    class Meta:
        model = Child
        fields = ("id", "parent")


class ChildPropsSerializer2(serializers.ModelSerializer):
    child = ChildSerializer2()

    class Meta:
        model = ChildProps
        fields = ("id", "child")


class EntrySerializer(serializers.ModelSerializer):
    inclusion_serializers = {"tags": TagSerializer}

    class Meta:
        model = Entry
        fields = ("id", "name", "tags")


class EntryReadOnlyTagsSerializer(EntrySerializer):
    class Meta(EntrySerializer.Meta):
        read_only_fields = ("tags",)


class ContainerSerializer(serializers.ModelSerializer):
    entries = EntrySerializer(many=True, source="entry_set")

    class Meta:
        model = Container
        fields = ("id", "name", "entries")


class ASerializer(serializers.ModelSerializer):
    class Meta:
        model = A
        fields = ("id",)


class BSerializer(serializers.ModelSerializer):
    inclusion_serializers = {"a": ASerializer}

    class Meta:
        model = B
        fields = ("id", "a")


class CSerializer(serializers.ModelSerializer):
    b = BSerializer()

    class Meta:
        model = C
        fields = ("id", "b")


class CInclusionSerializer(serializers.ModelSerializer):
    inclusion_serializers = {"b": BSerializer}

    class Meta:
        model = C
        fields = ("id", "b")


class SecondLevelRelatedObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecondLevelRelatedObject
        fields = ("id",)


class RelatedObjectSerializer(serializers.ModelSerializer):
    inclusion_serializers = {"a": ASerializer}

    secondlevelrelatedobject_set = SecondLevelRelatedObjectSerializer(
        many=True, read_only=True
    )

    class Meta:
        model = RelatedObject
        fields = ("id", "a", "secondlevelrelatedobject_set")


class MainObjectSerializer(serializers.ModelSerializer):
    relatedobject_set = RelatedObjectSerializer(many=True, read_only=True)

    class Meta:
        model = MainObject
        fields = ("id", "relatedobject_set")


class DSerializer(serializers.ModelSerializer):
    inclusion_serializers = {"tags1": TagSerializer, "tags2": TagSerializer}

    class Meta:
        model = D
        fields = ("id", "tags1", "tags2")


class ESerializer(serializers.ModelSerializer):
    inclusion_serializers = {"d": DSerializer}

    class Meta:
        model = E
        fields = ("id", "d")


class ModelWithPropertySerializer(serializers.ModelSerializer):
    inclusion_serializers = {"companies": CompanySerializer}

    basics = BasicSerializer(many=True, read_only=True)

    basics_list = BasicSerializer(many=True, read_only=True)

    class Meta:
        model = ModelWithProperty
        fields = ("basics", "basics_list")


class SubSubSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubSub
        fields = ("name",)


class SubSerializer(serializers.ModelSerializer):
    inclusion_serializers = {"company": CompanySerializer}

    sub_sub = SubSubSerializer(read_only=True)

    class Meta:
        model = Sub
        fields = ("name", "company", "sub_sub")


class ModelWithOptionalSubSerializer(serializers.ModelSerializer):
    sub = SubSerializer(default=None)

    class Meta:
        model = ModelWithOptionalSub
        fields = ("sub",)
