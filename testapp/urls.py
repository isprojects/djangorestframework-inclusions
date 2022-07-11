from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .viewsets import (
    BasicM2MViewSet,
    BasicViewSet,
    CDirectNestedInclusionViewSet,
    ChildPropsViewSet,
    ChildViewSet,
    ChildViewSet2,
    ChildViewSet3,
    ContainerViewSet,
    CustomRendererBasicViewSet,
    CustomRendererChildPropsViewSet,
    CViewSet,
    EntryViewSet,
    EViewSet,
    HyperlinkedChildPropsViewSet,
    HyperlinkedChildViewSet,
    HyperlinkedParentViewSet,
    HyperlinkedTagViewSet,
    MainObjectViewSet,
    ModelWithOptionalSubViewSet,
    ModelWithPropertyViewSet,
    ParentViewSet,
    TagViewSet,
)

router = DefaultRouter()
router.register(r"proto/tags", TagViewSet)
router.register(r"proto/parents", ParentViewSet)
router.register(r"proto/children", ChildViewSet)
router.register(r"proto/children2", ChildViewSet2, basename="child2")
router.register(r"proto/children3", ChildViewSet3, basename="child3")
router.register(r"proto/childconfigs", ChildPropsViewSet)
router.register(r"proto/container", ContainerViewSet)
router.register(r"proto/entries", EntryViewSet)
router.register(r"proto/c", CViewSet)
router.register(r"proto/c-nested", CDirectNestedInclusionViewSet, basename="c-nested")
router.register(r"proto/mainobjects", MainObjectViewSet)
router.register(r"proto/e", EViewSet)

router.register(r"proto/basic", BasicViewSet)
router.register(
    r"proto/custom-basic", CustomRendererBasicViewSet, basename="custom-basic"
)
router.register(
    r"proto/custom-parent",
    CustomRendererChildPropsViewSet,
    basename="custom-childprops",
)
router.register(r"proto/basicm2m", BasicM2MViewSet)
router.register(r"proto/modelwithproperty", ModelWithPropertyViewSet)
router.register(r"proto/modelwithoptionalsub", ModelWithOptionalSubViewSet)

router.register(
    r"proto/tags-hyperlinked", HyperlinkedTagViewSet, basename="tag-hyperlinked"
)
router.register(
    r"proto/children-hyperlinked", HyperlinkedChildViewSet, basename="child-hyperlinked"
)
router.register(
    r"proto/childconfigs-hyperlinked",
    HyperlinkedChildPropsViewSet,
    basename="childprops-hyperlinked",
)
router.register(
    r"proto/parent-hyperlinked", HyperlinkedParentViewSet, basename="parent-hyperlinked"
)


urlpatterns = [path("api/", include(router.urls))]
