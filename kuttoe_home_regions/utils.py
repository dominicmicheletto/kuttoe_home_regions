"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details utility functions and classes.
"""

#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# typing imports
from typing import Set, NamedTuple, Dict, Any, Callable, Tuple, Union

# python imports
from functools import wraps
from collections import defaultdict
import operator

# game imports
import enum

# sims4 imports
from sims4.utils import classproperty, constproperty, exception_protected
from sims4.tuning.tunable import TunableFactory
from sims4.collections import make_immutable_slots_class as make_immutable_slots, _ImmutableSlotsBase
from sims4.resources import Types, get_resource_key
from sims4.tuning.dynamic_enum import DynamicEnum
from sims4.tuning.instance_manager import InstanceManager

# miscellaneous
import services
from services import get_instance_manager
from element_utils import CleanupType
from tag import Tag
from singletons import DEFAULT

# interaction imports
from interactions.utils.tunable import DoCommand
from interactions.utils.success_chance import SuccessChance
from interactions import ParticipantType

# zone modifier imports
from zone_modifier.zone_modifier import ZoneModifier
from zone_modifier.zone_modifier_service import ZoneModifierService

# objects
from objects.definition_manager import DefinitionManager
from objects.game_object import GameObject


#######################################################################################################################
# Decorators                                                                                                          #
#######################################################################################################################


class on_load_complete:
    __slots__ = ('_manager_type', '_safe',)

    def __init__(self, manager_type: Types = Types.TUNING, safe=True):
        self._manager_type = manager_type
        self._safe = safe

    @property
    def manager(self) -> InstanceManager: return get_instance_manager(self._manager_type)

    @property
    def safe(self): return self._safe

    @property
    def manager_type(self): return self._manager_type

    def __wrapper__(self, target_func: Callable) -> Callable:
        @wraps(target_func)
        @exception_protected
        def safe_wrapper(*args, **kwargs):
            try:
                target_func(*args, **kwargs)
            except BaseException as ex:
                if not self._safe:
                    raise ex

        return safe_wrapper

    def __call__(self, target_func: Callable) -> Callable:
        func = self.__wrapper__(target_func)
        self.manager.add_on_load_complete(func)

        return func


class _cached_property_base:
    __slots__ = ('fget', 'value', 'property_type')
    _missing = object()

    class PropertyType(enum.Int):
        INSTANCE = 0
        CLASS = 1
        STATIC = 2

    def __init__(self, fget, property_type: PropertyType = PropertyType.INSTANCE):
        self.fget = fget
        self.value = defaultdict(lambda: self._missing)
        self.property_type = property_type

    def __get__(self, inst, owner):
        if inst is None and self.property_type == self.PropertyType.INSTANCE:
            return self

        arg = self._get_fget_args(inst, owner, self.property_type)
        if self.value[arg] is self._missing:
            self.value[arg] = self(inst, owner)

        return self.value[arg]

    @classmethod
    def _get_fget_args(cls, inst, owner, property_type):
        PropertyType = cls.PropertyType

        return {PropertyType.INSTANCE: inst, PropertyType.CLASS: owner, PropertyType.STATIC: None}[property_type]

    def __call__(self, inst, owner):
        arg = self._get_fget_args(inst, owner, self.property_type)

        if arg is not None:
            return self.fget(arg)
        return self.fget()


class _conditional_cached_property_base(_cached_property_base):
    __slots__ = ('_condition', '_fallback', )

    def __init__(self, condition=lambda *_, **__: True, fallback=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._condition = condition
        self._fallback = fallback

    def __call__(self, inst, owner):
        arg = self._get_fget_args(inst, owner, self.property_type)
        value = self._condition(arg) if arg is not None else self._condition()

        if value:
            return super().__call__(inst, owner)
        else:
            return self._fallback


class _filtered_cached_property_base(_cached_property_base):
    __slots__ = ('_filter_func', '_iterable_type', )

    def __init__(self, filter_func=lambda *_, **__: True, iterable_type=DEFAULT, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._filter_func = filter_func
        self._iterable_type = iterable_type

    def __call__(self, inst, owner):
        arg = self._get_fget_args(inst, owner, self.property_type)
        filter_func = lambda value: self._filter_func(value=value, inst_or_cls=arg)
        unfiltered_value = super().__call__(inst, owner)
        iterable_type = type(unfiltered_value) if self._iterable_type is DEFAULT else self._iterable_type

        return iterable_type(value for value in unfiltered_value if filter_func(value))


class conditional_cached_property:
    __slots__ = ('_condition', '_fallback',)

    def __init__(self, condition=lambda *_, **__: True, fallback=None):
        self._condition = condition
        self._fallback = fallback

    def __call__(self, fget, property_type=_cached_property_base.PropertyType.INSTANCE):
        return _conditional_cached_property_base(self._condition, self._fallback, fget=fget, property_type=property_type)


class filtered_cached_property:
    __slots__ = ('_filter_func', '_iterable_type', )

    def __init__(self, filter_func=lambda *_, **__: True, iterable_type=DEFAULT):
        self._filter_func = filter_func
        self._iterable_type = iterable_type

    def __call__(self, fget, property_type=_cached_property_base.PropertyType.INSTANCE):
        return _filtered_cached_property_base(self._filter_func, self._iterable_type, fget=fget, property_type=property_type)


class cached_property(_cached_property_base):
    def __init__(self, fget):
        super().__init__(fget)


class cached_classproperty(_cached_property_base):
    def __init__(self, fget):
        super().__init__(fget, property_type=self.PropertyType.CLASS)


class conditional_cached_classproperty(conditional_cached_property):
    def __call__(self, fget):
        return super().__call__(fget, property_type=_cached_property_base.PropertyType.CLASS)


class filtered_cached_classproperty(filtered_cached_property):
    def __call__(self, fget):
        return super().__call__(fget, property_type=_cached_property_base.PropertyType.CLASS)


class cached_staticproperty(_cached_property_base):
    def __init__(self, fget):
        super().__init__(fget, property_type=self.PropertyType.STATIC)


class conditional_cached_staticproperty(conditional_cached_property):
    def __call__(self, fget):
        return super().__call__(fget, property_type=_cached_property_base.PropertyType.STATIC)


class filtered_cached_staticproperty(filtered_cached_property):
    def __call__(self, fget):
        return super().__call__(fget, property_type=_cached_property_base.PropertyType.STATIC)


class leroidetout_injector:
    __slots__ = ('_target_object', '_target_function_name', '_safe', '_default_value', )

    def __init__(self, target_object: Any, target_function_name: str, safe: bool = False, default_value=None) -> None:
        self._target_object = target_object
        self._target_function_name = str(target_function_name)
        self._safe = safe
        self._default_value = default_value

    @property
    def safe(self):
        return self._safe

    @property
    def target_object(self):
        return self._target_object

    @property
    def target_function_name(self):
        return self._target_function_name

    @property
    def target_function(self) -> Callable:
        return getattr(self.target_object, self.target_function_name, None)

    @property
    def has_function(self) -> bool:
        return hasattr(self.target_object, self.target_function_name)

    @property
    def default_value(self):
        return self._default_value

    @staticmethod
    def __wrapper__(original: Callable, target: Callable) -> Callable:
        import inspect

        @wraps(original)
        def _function_wrapper(*args, **kwargs):
            func = original.fget if type(original) is property else original
            wrapped_func = target(func, *args, **kwargs)

            return wrapped_func

        if inspect.ismethod(original):
            return classmethod(_function_wrapper)
        elif type(original) is property:
            return property(_function_wrapper)
        else:
            return _function_wrapper

    def __call__(self, func: Callable) -> Callable:
        if self.safe and not self.has_function:
            return func

        setattr(self.target_object, self.target_function_name, self.__wrapper__(self.target_function, func))
        return func


class enum_entry_factory:
    __slots__ = ('_default', '_invalid', '_method_name', '_kwargs', )
    DEFAULT_METHOD_NAME = 'to_enum_entry'

    def __init__(self, default: str, invalid: Tuple[str, ...], method_name: str = DEFAULT, **kwargs):
        self._default = default
        self._invalid = invalid
        self._method_name = self.DEFAULT_METHOD_NAME if method_name is DEFAULT else method_name
        self._kwargs = kwargs

    @staticmethod
    def get_enum_values_from_name(enum_cls, *names: str):
        return tuple(enum_cls[name] for name in names if name in enum_cls)

    @staticmethod
    def get_enum_value_from_name_or_value(enum_cls, name_or_value):
        if type(name_or_value) is enum_cls:
            return name_or_value
        return enum_cls[name_or_value]

    @classmethod
    def get_and_verify_default_value(cls, enum_cls, name: str):
        values_tuple = cls.get_enum_values_from_name(enum_cls, name)

        if not values_tuple:
            raise ValueError(f'Invalid default value: {name} does not exist in {enum_cls}')
        return next(iter(values_tuple))

    @classmethod
    def _create_method(cls, default_value, invalid_values, **my_kwargs):
        from sims4.tuning.tunable import TunableEnumEntry
        get_value = cls.get_enum_value_from_name_or_value

        def to_enum_entry(self, default=DEFAULT, invalid=DEFAULT, **kwargs):
            default = get_value(self, default_value if default is DEFAULT else default)
            invalid = tuple(get_value(self, value) for value in (invalid_values if invalid is DEFAULT else invalid))
            kwargs = {**my_kwargs, **kwargs}

            return TunableEnumEntry(tunable_type=self, default=default, invalid_enums=invalid, **kwargs)

        return to_enum_entry

    def __call__(self, enum_cls):
        default_value = self.get_and_verify_default_value(enum_cls, self._default)
        invalid_values = self.get_enum_values_from_name(enum_cls, *self._invalid)
        to_enum_entry_func = self._create_method(default_value, invalid_values, **self._kwargs)

        with enum_cls.make_mutable():
            setattr(enum_cls, self._method_name, classmethod(to_enum_entry_func))

        return enum_cls


class enum_set_factory:
    __slots__ = ('_default', '_default_enum_list', '_invalid', '_method_name', '_kwargs',)
    DEFAULT_METHOD_NAME = 'to_enum_set'

    def __init__(
            self,
            default: str,
            invalid: Tuple[str, ...],
            default_enum_list: Tuple[str, ...] = DEFAULT,
            method_name: str = DEFAULT,
            **kwargs
    ):
        self._default = default
        self._invalid = invalid
        self._method_name = self.DEFAULT_METHOD_NAME if method_name is DEFAULT else method_name
        self._kwargs = kwargs
        self._default_enum_list = (default, ) if default_enum_list is DEFAULT else default_enum_list

    @staticmethod
    def get_enum_values_from_name(enum_cls, *names: str):
        return tuple(enum_cls[name] for name in names if name in enum_cls)

    @classmethod
    def _create_method(cls, default_value, default_enum_values, invalid_values, **my_kwargs):
        from sims4.tuning.tunable import OptionalTunable, TunableEnumSet

        def to_enum_entry(self, default=DEFAULT, enum_values=DEFAULT, invalid=DEFAULT, optional=False, **kwargs):
            default = default_value if default is DEFAULT else default
            enum_values = frozenset(default_enum_values if enum_values is DEFAULT else enum_values)
            invalid = invalid_values if invalid is DEFAULT else invalid
            kwargs = {**my_kwargs, **kwargs}

            enum_set = TunableEnumSet(
                enum_type=self, invalid_enums=invalid, enum_default=default, default_enum_list=enum_values, **kwargs
            )

            return OptionalTunable(enum_set) if optional else enum_set

        return to_enum_entry

    def __call__(self, enum_cls):
        default_value = next(iter(self.get_enum_values_from_name(enum_cls, self._default)))
        default_enum_list = self.get_enum_values_from_name(enum_cls, *self._default_enum_list)
        invalid_values = self.get_enum_values_from_name(enum_cls, *self._invalid)
        to_enum_entry_func = self._create_method(default_value, default_enum_list, invalid_values, **self._kwargs)

        with enum_cls.make_mutable():
            setattr(enum_cls, self._method_name, classmethod(to_enum_entry_func))

        return enum_cls


#######################################################################################################################
# Named Tuples                                                                                                        #
#######################################################################################################################


class FunctionArgs(NamedTuple):
    args: tuple = tuple()
    kwargs: Dict[str, Any] = dict()

    def __call__(self, func):
        return func(*self.args, **self.kwargs)


#######################################################################################################################
# Enumerations                                                                                                        #
#######################################################################################################################


@enum_entry_factory(default='INVALID', invalid=('INVALID', ))
class InteractionTargetType(DynamicEnum):
    INVALID = 0

    @classmethod
    def get_tuning_cls(cls, tuning_id: int) -> GameObject:
        definition_manager = services.definition_manager()

        return super(DefinitionManager, definition_manager).get(tuning_id)

    @classmethod
    def verify_all_values(cls):
        for entry in cls:
            if entry is cls.INVALID:
                continue

            if entry.tuning_cls is None:
                raise AttributeError('Unable to load tunable class for {} ({})'.format(entry, hex(entry.value)))

    @property
    def tuning_cls(self):
        return self.get_tuning_cls(self.value)

    def update_affordance_list(self, *affordances):
        if not self.tuning_cls:
            return 0

        self.tuning_cls._super_affordances += affordances
        return len(self.tuning_cls._super_affordances)

    def update_and_register_affordances(self, *affordances):
        affordance_manager = services.get_instance_manager(Types.INTERACTION)

        collected_affordances = set()
        for affordance in affordances:
            interaction = affordance.interaction
            resource_key = affordance.resource_key

            affordance_manager.register_tuned_class(interaction, resource_key)
            collected_affordances.add(interaction)

        return self.update_affordance_list(*collected_affordances)


class BoundTypes(enum.IntFlags):
    NONE = 0
    LEFT = 1
    RIGHT = 2
    BOTH = LEFT | RIGHT


#######################################################################################################################
#  Helper Functions                                                                                                   #
#######################################################################################################################


def create_tunable_reference(tuning_type: Types, pack_safe: bool = True, class_restrictions=(), *args, **kwargs):
    from sims4.tuning.tunable import TunableReference

    manager = get_instance_manager(tuning_type)
    return TunableReference(manager=manager, class_restrictions=class_restrictions, pack_safe=pack_safe, *args,
                            **kwargs)


def make_immutable_slots_class(**kwargs) -> _ImmutableSlotsBase:
    return make_immutable_slots(kwargs.keys())(kwargs)


def construct_auto_init_factory(factory_cls: type, has_factory=True, factory_options: Dict[str, Any] = None, **values):
    base = factory_cls.TunableFactory(**(factory_options or dict())) if has_factory else factory_cls
    default = base._default
    factory = base.FACTORY_TYPE

    factory_keys: Set[str] = set()
    parents = factory_cls.mro()
    for base_cls in parents[::-1]:
        factory_keys.update(getattr(base_cls, 'FACTORY_TUNABLES', dict().keys()))
    keys_to_ignore = {'verify_tunable_callback', }
    keys = factory_keys - keys_to_ignore

    factory_values = {key: getattr(default, key, None) for key in keys}
    factory_values.update(values)

    return factory(**factory_values)


class CommandsList(tuple):
    class ArgumentType(enum.Int):
        PARTICIPANT = 0
        LITERAL = 1
        TAG = 2

    _ARG_TYPE_MAPPING = {
        ArgumentType.PARTICIPANT: DoCommand.ARG_TYPE_PARTICIPANT,
        ArgumentType.LITERAL: DoCommand.ARG_TYPE_LITERAL,
        ArgumentType.TAG: DoCommand.ARG_TYPE_TAG,
    }

    @classmethod
    def _make_entry(cls, value, arg_type: ArgumentType = ArgumentType.LITERAL):
        args = dict()
        args['arg_type'] = cls._ARG_TYPE_MAPPING[arg_type]
        args['argument'] = value

        return make_immutable_slots_class(**args)

    def _add_value(self, entry):
        return type(self)([*self, entry])

    def add_participant(self, participant: ParticipantType = ParticipantType.TargetSim):
        return self._add_value(self._make_entry(participant, self.ArgumentType.PARTICIPANT))

    def add_string(self, value: str):
        return self._add_value(self._make_entry(value, self.ArgumentType.LITERAL))

    def add_number(self, value: float):
        return self._add_value(self._make_entry(value, self.ArgumentType.LITERAL))

    def add_boolean(self, value: bool):
        return self._add_value(self._make_entry(value, self.ArgumentType.LITERAL))

    def add_tag(self, tag: Tag):
        return self._add_value(self._make_entry(tag, self.ArgumentType.TAG))

    def to_do_command(self, command_name: str):
        return make_do_command(command_name, *self)


def make_do_command(command_name: str, *additional_arguments):
    class _RunCommand(DoCommand):
        @classproperty
        def factory(cls): return cls

        @classproperty
        def command(cls) -> str: return command_name

        @classproperty
        def arguments(cls): return additional_arguments

        @classproperty
        def _timing(cls):
            args = dict()
            args['timing'] = cls.AT_END
            args['xevt_id'] = None
            args['offset_time'] = None
            args['supports_failsafe'] = None
            args['criticality'] = CleanupType.OnCancel

            return make_immutable_slots_class(**args)

        @constproperty
        def success_chance(): return SuccessChance.ONE

        def __init__(self, interaction, *, sequence=(), **kwargs):
            super().__init__(interaction, timing=self._timing, sequence=sequence, **kwargs)

    return _RunCommand


def create_tunable_factory_with_overrides(factory_cls, **overrides):
    tuned_values = factory_cls._tuned_values.clone_with_overrides(**overrides)

    return TunableFactory.TunableFactoryWrapper(tuned_values, factory_cls._name, factory_cls.factory)


def get_zone_modifiers(zone_id: int = None) -> Set[ZoneModifier]:
    zone_modifier_service: ZoneModifierService = services.get_zone_modifier_service()
    zone_id = zone_id or services.current_zone_id()

    return zone_modifier_service.get_zone_modifiers(zone_id, force_refresh=True)


def does_zone_have_modifier(modifier: ZoneModifier, zone_id: int = None):
    return modifier in get_zone_modifiers(zone_id)


def does_zone_have_modifiers(*modifiers: ZoneModifier, num_required: int = 1, zone_id: int = None):
    return len(get_zone_modifiers(zone_id) & set(modifiers)) >= num_required


def matches_bounds(value_to_test, bound_conditions: BoundTypes, bounds: Tuple[Union[int, float], Union[int, float]]):
    left, right = bounds
    left_op = operator.le if bound_conditions & BoundTypes.LEFT else operator.lt
    right_op = operator.ge if bound_conditions & BoundTypes.RIGHT else operator.gt

    return left_op(left, value_to_test) and right_op(right, value_to_test)


#######################################################################################################################
#  Mixins                                                                                                             #
#######################################################################################################################

class SnippetMixin:
    __slots__ = ('_snippet', '_snippet_name', '_use_list_reference', '_factory', )

    def __init_subclass__(cls, snippet_name: str, use_list_reference=False, factory_options: dict = None, *args, **kwargs):
        factory_options = factory_options or dict()

        cls._factory = cls.TunableFactory(**factory_options)
        cls._use_list_reference = use_list_reference
        cls._snippet_name = snippet_name
        cls._snippet = cls.define_snippet(snippet_name, use_list_reference=use_list_reference, **factory_options)

        super().__init_subclass__(*args, **kwargs)

    @classproperty
    def SnippetReference(cls): return cls._snippet[0]

    @classproperty
    def SnippetVariant(cls): return cls._snippet[1]

    @classproperty
    def factory(cls): return cls._factory

    @classproperty
    def use_list_reference(cls): return cls._use_list_reference

    @classmethod
    def get_registered_snippets(cls):
        from snippets import get_defined_snippets_gen

        return tuple(get_defined_snippets_gen(cls._snippet_name))

    @classmethod
    def define_snippet(cls, snippet_name: str, use_list_reference=False, **factory_options):
        from snippets import define_snippet

        factory = cls.TunableFactory(**factory_options)
        return define_snippet(snippet_name, factory, use_list_reference=use_list_reference)


class ManagedTuningMixin:
    __slots__ = ('tuning_type', )

    def __init_subclass__(cls, tuning_type: Types, *args, **kwargs):
        cls.tuning_type = tuning_type
        super().__init_subclass__(*args, **kwargs)

    @classproperty
    def manager(cls) -> InstanceManager: return services.get_instance_manager(cls.tuning_type)

    @classproperty
    def types(cls) -> dict: return cls.manager.types

    @classmethod
    def tuned_values(cls): return cls.types.values()

    @classmethod
    def get_order_types(cls, only_subclasses_of=None): return cls.manager.get_ordered_types(only_subclasses_of)

    def __getitem__(self, *tuning_ids):
        tuning = (self.manager.get(get_resource_key(tuning_id, self.tuning_type), None) for tuning_id in tuning_ids)
        fetched_values = iter(filter(lambda value: value is not None, tuning))

        yield from fetched_values


#######################################################################################################################
#  Module Exports                                                                                                     #
#######################################################################################################################

__all__ = (
    'does_zone_have_modifier', 'does_zone_have_modifiers',
    'get_zone_modifiers',
    'create_tunable_factory_with_overrides',
    'make_do_command',
    'CommandsList',
    'construct_auto_init_factory',
    'make_immutable_slots_class',
    'create_tunable_reference',
    'InteractionTargetType',
    'on_load_complete',
    'enum_entry_factory', 'enum_set_factory',
    'cached_property', 'cached_classproperty', 'cached_staticproperty',
    'conditional_cached_property', 'conditional_cached_classproperty', 'conditional_cached_staticproperty',
    'filtered_cached_property', 'filtered_cached_classproperty', 'filtered_cached_staticproperty',
    'FunctionArgs',
    'SnippetMixin',
    'ManagedTuningMixin',
    'leroidetout_injector',
    'matches_bounds', 'BoundTypes'
)
