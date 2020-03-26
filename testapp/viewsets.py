from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from rest_framework_inclusions.renderer import InclusionJSONRenderer

from .models import (
    Basic,
    BasicM2M,
    C,
    Child,
    ChildProps,
    Container,
    E,
    Entry,
    MainObject,
    ModelWithOptionalSub,
    ModelWithProperty,
    Parent,
    Tag,
)
from .serializers import (
    BasicM2MSerializer,
    BasicSerializer,
    ChildPropsSerializer2,
    ChildSerializer,
    ChildSerializer2,
    ChildSerializer3,
    CInclusionSerializer,
    ContainerSerializer,
    CSerializer,
    EntryReadOnlyTagsSerializer,
    ESerializer,
    MainObjectSerializer,
    ModelWithOptionalSubSerializer,
    ModelWithPropertySerializer,
    ParentSerializer,
    TagSerializer,
)


class CommonMixin:
    permission_classes = ()
    authentication_classes = ()
    renderer_classes = (InclusionJSONRenderer,)
    serializer_class = TagSerializer


class BasicViewSet(CommonMixin, viewsets.ModelViewSet):
    serializer_class = BasicSerializer
    queryset = Basic.objects.all()

    @action(detail=False)
    def many(self, request, *args, **kwargs):
        serializer = BasicSerializer(
            instance=Basic.objects.all().order_by("id"), many=True
        )
        return Response(serializer.data)


class BasicM2MViewSet(CommonMixin, viewsets.ModelViewSet):
    serializer_class = BasicM2MSerializer
    queryset = BasicM2M.objects.all()


class TagViewSet(CommonMixin, viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    pagination_class = None

    @action(detail=False)
    def custom_action(self, request):
        serializer = TagSerializer(self.get_queryset(), many=True)
        return Response(serializer.data)


class ParentViewSet(CommonMixin, viewsets.ModelViewSet):
    serializer_class = ParentSerializer
    queryset = Parent.objects.all()

    @action(detail=False, methods=["post"])
    def check(self, request):
        return Response({"arbitrary": "content"})

    @action(detail=True, methods=["post"])
    def check2(self, request, **kw):
        return Response({"arbitrary": "content"})


class ChildViewSet(CommonMixin, viewsets.ModelViewSet):
    serializer_class = ChildSerializer
    queryset = Child.objects.all()


class ChildViewSet2(CommonMixin, viewsets.ModelViewSet):
    serializer_class = ChildSerializer2
    queryset = Child.objects.all()


class ChildViewSet3(CommonMixin, viewsets.ModelViewSet):
    serializer_class = ChildSerializer3
    queryset = Child.objects.all()


class ChildPropsViewSet(CommonMixin, viewsets.ModelViewSet):
    serializer_class = ChildPropsSerializer2
    queryset = ChildProps.objects.all()


class ContainerViewSet(CommonMixin, viewsets.ModelViewSet):
    serializer_class = ContainerSerializer
    queryset = Container.objects.all()


class EntryViewSet(CommonMixin, viewsets.ModelViewSet):
    serializer_class = EntryReadOnlyTagsSerializer
    queryset = Entry.objects.all()


class CViewSet(CommonMixin, viewsets.ModelViewSet):
    serializer_class = CSerializer
    queryset = C.objects.all()

    @action(detail=True)
    def custom_action(self, request, *args, **kwargs):
        serializer = CSerializer(self.get_object())
        return Response(serializer.data)


class CDirectNestedInclusionViewSet(CommonMixin, viewsets.ModelViewSet):
    serializer_class = CInclusionSerializer
    queryset = C.objects.all()
    pagination_class = None


class MainObjectViewSet(CommonMixin, viewsets.ModelViewSet):
    queryset = MainObject.objects.all()
    serializer_class = MainObjectSerializer
    pagination_class = None


class EViewSet(CommonMixin, viewsets.ModelViewSet):
    serializer_class = ESerializer
    queryset = E.objects.all()


class ModelWithPropertyViewSet(CommonMixin, viewsets.ModelViewSet):
    serializer_class = ModelWithPropertySerializer
    queryset = ModelWithProperty.objects.all()


class ModelWithOptionalSubViewSet(CommonMixin, viewsets.ModelViewSet):
    serializer_class = ModelWithOptionalSubSerializer
    queryset = ModelWithOptionalSub.objects.all()
