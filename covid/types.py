import operator


class CachedProperty:
    def __init__(self, func):
        self.func = func
        self.name = None

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner=None):
        if instance is None:
            return owner
        else:
            value = self.func(instance)
            setattr(instance, self.name, value)
            return value


class ComputedProperty(CachedProperty):
    def __get__(self, instance, owner=None):
        if instance is None:
            return owner
        else:
            return self.func(instance)


def cached(func):
    """
    Function interface to CachedProperty.
    """
    return CachedProperty(func)


def alias(name):
    """
    Create an alias property: all access to property are redirected to the
    given attribute.
    """

    fget = operator.attrgetter(name)

    if "." in name:
        base, _, extra = name.partition(".")

        def fset(self, value):
            raise TypeError(f"cannot modify sub-attribute {extra} of {base}")

    else:

        def fset(self, value):
            setattr(self, name, value)

    return property(fget, fset)


def delegate(name):
    """
    Create a delegate: do not write, but if attribute is not defined, delegate
    to another attribute.
    """
    return CachedProperty(operator.attrgetter(name))


def computed(func):
    """
    A writable property-like descriptor.
    """
    return ComputedProperty(func)
