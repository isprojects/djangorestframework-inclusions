from django.db import models


class Company(models.Model):
    name = models.CharField(max_length=50)


class Basic(models.Model):
    name = models.CharField(max_length=50)
    company = models.ForeignKey(
        Company, null=True, on_delete=models.PROTECT, related_name="+"
    )


class BasicM2M(models.Model):
    name = models.CharField(max_length=50)
    tags = models.ManyToManyField("Tag")


class Tag(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ("id",)  # NOTE: don't do this in real models

    def __str__(self):
        return self.name


class Parent(models.Model):
    name = models.CharField(max_length=50)
    tags = models.ManyToManyField("Tag")

    favourite_child = models.ForeignKey(
        "Child", null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ("id",)  # NOTE: don't do this in real models

    def __str__(self):
        return self.name


class Child(models.Model):
    parent = models.ForeignKey(Parent, on_delete=models.PROTECT)
    name = models.CharField(max_length=50)

    tags = models.ManyToManyField("Tag")

    class Meta:
        ordering = ("id",)  # NOTE: don't do this in real models


class ChildProps(models.Model):
    child = models.OneToOneField(Child, on_delete=models.PROTECT)

    class Meta:
        ordering = ("id",)  # NOTE: don't do this in real models


class Container(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ("id",)  # NOTE: don't do this in real models


class Entry(models.Model):
    container = models.ForeignKey(Container, null=False, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    tags = models.ManyToManyField("Tag")

    class Meta:
        ordering = ("id",)  # NOTE: don't do this in real models


class A(models.Model):
    class Meta:
        ordering = ("id",)  # NOTE: don't do this in real models


class B(models.Model):
    a = models.ForeignKey("A", null=True, blank=True, on_delete=models.SET_NULL)


class C(models.Model):
    b = models.ForeignKey("B", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ("id",)  # NOTE: don't do this in real models


class D(models.Model):
    tags1 = models.ManyToManyField("Tag", related_name="+")
    tags2 = models.ManyToManyField("Tag", related_name="+")

    class Meta:
        ordering = ("id",)  # NOTE: don't do this in real models


class E(models.Model):
    d = models.ForeignKey("D", on_delete=models.CASCADE)

    class Meta:
        ordering = ("id",)  # NOTE: don't do this in real models


# Regression test models for NEXT-1052


class MainObject(models.Model):
    pass


class RelatedObject(models.Model):
    main = models.ForeignKey(MainObject, on_delete=models.CASCADE)
    a = models.ForeignKey(A, null=True, on_delete=models.SET_NULL)


class SecondLevelRelatedObject(models.Model):
    main = models.ForeignKey(MainObject, null=True, on_delete=models.CASCADE)
    related_object = models.ForeignKey(
        RelatedObject, null=True, on_delete=models.CASCADE
    )


# a model with a property that's exposed directly


class ModelWithProperty(models.Model):
    def basics(self):
        return Basic.objects.all().order_by("id")

    def basics_list(self):
        return list(Basic.objects.all().order_by("id"))


class SubSub(models.Model):
    name = models.CharField(max_length=50)


class Sub(models.Model):
    name = models.CharField(max_length=50)
    company = models.ForeignKey(Company, null=True, on_delete=models.CASCADE)
    sub_sub = models.OneToOneField(SubSub, on_delete=models.CASCADE, null=True)


class ModelWithOptionalSub(models.Model):
    sub = models.OneToOneField(Sub, on_delete=models.CASCADE, null=True)
