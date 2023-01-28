"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details the metaclass nuts and bolts needed for dynamic enumerations that are built around a tuple instead
of a simple name/value pair.
"""


#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

# python imports
from collections import namedtuple, OrderedDict

# miscellaneous
from typing import Dict, Union, Tuple

import enum
from singletons import DEFAULT, DefaultType

# sim4 imports
from sims4.common import is_available_pack
from sims4.tuning.tunable_base import LoadingAttributes
from sims4.tuning.tunable import TunableSingletonFactory, TunableList, Tunable, TunableReference
from sims4.tuning.dynamic_enum import _get_pack_from_enum_value
from sims4.tuning.merged_tuning_manager import UnavailablePackSafeResourceError
from sims4.resources import get_resource_key
from sims4.repr_utils import standard_repr

#######################################################################################################################
# Named Tuples                                                                                                        #
#######################################################################################################################

EnumItem = namedtuple('EnumItem', ('enum_name', 'enum_value', 'enum_info'))


#######################################################################################################################
# Mixins                                                                                                              #
#######################################################################################################################

class DynamicFactoryEnumMixin:
    @property
    def factory_value(self):
        return self._tuned_values_mapping[self.name]

    def __getattr__(self, name):
        try:
            return getattr(self.factory_value, name)
        except AttributeError:
            raise AttributeError('{} does not have an attribute named {}'.format(self, name))

    def __repr__(self):
        return '<%s.%s: %s = %s>' % (type(self).__name__, self.name, super().__repr__(), self.factory_value)


#######################################################################################################################
# Tunables                                                                                                            #
#######################################################################################################################

class EnumItemFactory(TunableSingletonFactory):
    class TunableReferenceMixin:
        @classmethod
        def _verify_resource_class(cls, resource, class_restrictions=()):
            if resource is None or len(class_restrictions) == 0:
                return resource

            value_mro_set = set([cls.__name__ for cls in resource.mro()])
            for c in class_restrictions:
                if (isinstance(c, str) and c in value_mro_set) or issubclass(resource, c):
                    return resource
            raise ValueError('TunableReference is set to a value that is not allowed by its class restriction.')

        @classmethod
        def _get_resource(cls, reference: TunableReference, resource_id: int = 0):
            manager = reference._manager
            resource_type = manager.TYPE
            class_restrictions = reference._class_restrictions
            pack_safe = reference.pack_safe
            resource_key = get_resource_key(resource_id, resource_type)

            try:
                value = manager.get(resource_key, pack_safe=pack_safe)
            except UnavailablePackSafeResourceError as ex:
                if pack_safe:
                    return None
                else:
                    raise ex
            else:
                return cls._verify_resource_class(value, class_restrictions)

        def __init__(self, **tunable_names: Union[str, Tuple[str, str], Tuple[str, bool]]):
            property_names = dict()
            for key, value in tunable_names.items():
                if type(value) is str:
                    property_names[key] = (value, value)
                elif type(value) is tuple and type(value[1]) is str:
                    property_names[key] = value
                elif type(value) is tuple and type(value[1]) is bool:
                    new_key, private = value
                    property_names[key] = (new_key, f'_{new_key}' if private else new_key)

            self._tunable_names: Dict[str, Tuple[str, str]] = property_names

        @staticmethod
        def create_tunable(cls, key: str):
            tunable: TunableReference = getattr(cls, 'FACTORY_TUNABLES', dict()).get(key, None)
            if tunable is None:
                return None

            return Tunable(tunable_type=int, default=0, allow_empty=tunable._allow_none)

        def __call__(self, cls):
            factory = getattr(cls, 'FACTORY_TYPE', None)

            if not issubclass(factory, tuple) and hasattr(cls, 'FACTORY_TUNABLES'):
                tunables = getattr(cls, 'FACTORY_TUNABLES')

                for old_key, new_key_mapping in self._tunable_names.items():
                    new_key, prop_key = new_key_mapping
                    tunables[new_key] = self.create_tunable(cls, old_key)
                    reference = tunables.pop(old_key)

                    def prop_getter(me, tunable_reference: TunableReference, prop_name: str):
                        return self._get_resource(tunable_reference, getattr(me, prop_name, 0))

                    setattr(factory, old_key, property(lambda me: prop_getter(me, reference, prop_key)))

            setattr(cls, 'FACTORY_TYPE', factory)
            return cls

    class ReprMixin:
        def __init__(self, **remapping: Union[str, type(None), DefaultType]):
            self._remapping = remapping
            self._deleted_properties = set(key for key in remapping if remapping[key] is None)
            self._additional_properties = set(key for key in remapping if remapping[key] is DEFAULT)

        def __contains__(self, item: str):
            return item not in self._deleted_properties

        def __getitem__(self, item: str):
            return self._remapping.get(item, item)

        def keys(self, cls):
            base_keys = set(self[key] for key in getattr(cls, 'FACTORY_TUNABLES', tuple()) if key in self)

            return base_keys | self._additional_properties

        def __call__(self, cls):
            factory = getattr(cls, 'FACTORY_TYPE', None)
            keys = self.keys(cls)

            if not issubclass(factory, tuple) and hasattr(cls, 'FACTORY_TUNABLES'):
                def __repr__(self):
                    return standard_repr(self, **{key: getattr(self, key) for key in keys})

                factory.__repr__ = __repr__

            setattr(cls, 'FACTORY_TYPE', factory)
            return cls

    def __init_subclass__(cls, *args, **kwargs):
        super().__init_subclass__(*args, **kwargs)

    def load_etree_node(self, node, source, expect_error):
        enum_info = super().load_etree_node(node, source, expect_error)
        enum_value = int(node.get(LoadingAttributes.EnumValue))
        enum_name = node.get(LoadingAttributes.Name)

        return EnumItem(enum_name=enum_name, enum_value=enum_value, enum_info=enum_info)

    @staticmethod
    def get_default(value):
        return None


class TunableDynamicFactoryEnumElements(TunableList):
    DESCRIPTION = 'The list of elements in the dynamic enumeration.'

    def __init__(self, factory_cls, finalize, description=DESCRIPTION, **kwargs):
        super().__init__(factory_cls(), description=description, unique_entries=True, **kwargs)
        self._finalize = finalize
        self.needs_deferring = False

    def load_etree_node(self, node, source, expect_error):
        value = super().load_etree_node(node, source, expect_error)
        self._finalize(*value)


class DynamicFactoryEnumMetaclass(enum.Metaclass):
    def __new__(cls, class_name, bases, class_dict,
                factory_cls, dynamic_max_length=None, dynamic_offset=None,
                **kwargs):
        bases += (DynamicFactoryEnumMixin,)
        class_dict['_get_default_value'] = classmethod(cls._get_default_value)
        class_dict['factory_cls'] = factory_cls

        enum_type = super().__new__(cls, class_name, bases, class_dict, offset=dynamic_offset, **kwargs)

        with enum_type.make_mutable():
            enum_type._elements = TunableDynamicFactoryEnumElements(
                factory_cls, enum_type.finalize, maxlength=dynamic_max_length
            )
        return enum_type

    def _get_default_value(cls, value):
        if not hasattr(cls.factory_cls, 'get_default'):
            return None

        return cls.factory_cls.get_default(value)

    def _add_new_enum_value(cls, name, value, info=None):
        super()._add_new_enum_value(name, value)

        if not hasattr(cls, '_tuned_values_mapping'):
            setattr(cls, '_tuned_values_mapping', OrderedDict())
        if info is None:
            info = cls._get_default_value(value)

        cls._tuned_values_mapping[name] = info

    def finalize(cls, *tuned_elements):
        with cls.make_mutable():
            if not hasattr(cls, '_static_index'):
                cls._static_index = len(cls) - 1

            index = cls._static_index + 1
            items = tuple(cls.items())

            for (item_name, item_value) in items[index:]:
                delattr(cls, item_name)
                del cls.name_to_value[item_name]
                del cls.value_to_name[item_value]

            for element in tuned_elements:
                enum_name = element.enum_name
                raw_value = element.enum_value
                factory_value = element.enum_info

                if cls.partitioned and not (cls.locked or is_available_pack(_get_pack_from_enum_value(raw_value))):
                    pass
                else:
                    cls._add_new_enum_value(enum_name, raw_value, factory_value)

    @property
    def factory_values(cls):
        return tuple(cls._tuned_values_mapping)


#######################################################################################################################
# Module exports                                                                                                      #
#######################################################################################################################

__all__ = ('DynamicFactoryEnumMixin', 'EnumItemFactory', 'DynamicFactoryEnumMetaclass', )
