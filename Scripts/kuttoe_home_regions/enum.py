#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# python imports
from collections import namedtuple, OrderedDict

# miscellaneous
import enum

# sim4 imports
from sims4.common import is_available_pack
from sims4.tuning.tunable_base import LoadingAttributes
from sims4.tuning.tunable import TunableSingletonFactory, TunableList
from sims4.tuning.dynamic_enum import _get_pack_from_enum_value


#######################################################################################################################
#  Named Tuples                                                                                                       #
#######################################################################################################################


EnumItem = namedtuple('EnumItem', ('enum_name', 'enum_value', 'enum_info'))


#######################################################################################################################
#  Mixins                                                                                                             #
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
#  Tunables                                                                                                           #
#######################################################################################################################


class EnumItemFactory(TunableSingletonFactory):
    __slots__ = ()

    def load_etree_node(self, node, source, expect_error):
        enum_info = super().load_etree_node(node, source, expect_error)
        enum_value = int(node.get(LoadingAttributes.EnumValue))
        enum_name = node.get(LoadingAttributes.Name)

        return EnumItem(enum_name=enum_name, enum_value=enum_value, enum_info=enum_info)

    @staticmethod
    def get_default(value):
        return None


class TunableDynamicFactoryEnumElements(TunableList):
    def __init__(self, factory_cls, finalize, description='The list of elements in the dynamic enumeration.', **kwargs):
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
        bases += (DynamicFactoryEnumMixin, )
        class_dict['_get_default_value'] = classmethod(cls._get_default_value)
        class_dict['factory_cls'] = factory_cls

        enum_type = super().__new__(cls, class_name, bases, class_dict, offset=dynamic_offset, **kwargs)

        with enum_type.make_mutable():
            enum_type._elements = TunableDynamicFactoryEnumElements(factory_cls, enum_type.finalize,
                                                                    maxlength=dynamic_max_length)
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

