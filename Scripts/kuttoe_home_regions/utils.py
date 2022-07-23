#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# python imports
from functools import wraps

# game imports
import enum

# sims4 imports
from sims4.utils import classproperty, constproperty, exception_protected
from sims4.tuning.tunable import TunableFactory
from sims4.collections import make_immutable_slots_class as make_immutable_slots, _ImmutableSlotsBase
from sims4.resources import Types
from sims4.tuning.dynamic_enum import DynamicEnum

# miscellaneous
import services
from services import get_instance_manager
from element_utils import CleanupType
from tag import Tag

# interaction imports
from interactions.utils.tunable import DoCommand
from interactions.utils.success_chance import SuccessChance
from interactions import ParticipantType

# objects
from objects.definition_manager import DefinitionManager
from objects.game_object import GameObject


#######################################################################################################################
# Enumerations                                                                                                        #
#######################################################################################################################


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
                raise AttributeError('Unable to load tuning class for {} ({})'.format(entry, hex(entry.value)))

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

        collected_affordances = []
        for affordance in affordances:
            interaction = affordance.interaction
            resource_key = affordance.resource_key

            affordance_manager.register_tuned_class(interaction, resource_key)
            collected_affordances.append(interaction)

        return self.update_affordance_list(*collected_affordances)


#######################################################################################################################
#  Helper Functions                                                                                                   #
#######################################################################################################################


def on_load_complete(manager_type: Types, safe=True):
    def wrapper(func):
        @wraps(func)
        def safe_function(manager):
            try:
                func(manager)
            except BaseException as ex:
                if not safe:
                    raise ex

        wrapper.__name__ = func.__name__
        get_instance_manager(manager_type).add_on_load_complete(exception_protected(safe_function))

    return wrapper


def make_immutable_slots_class(**kwargs) -> _ImmutableSlotsBase:
    return make_immutable_slots(kwargs.keys())(kwargs)


def construct_auto_init_factory(factory_cls, has_factory=True, **values):
    base = factory_cls.TunableFactory() if has_factory else factory_cls
    default = base._default
    factory = base.FACTORY_TYPE

    factory_keys = set()
    parents = factory_cls.__mro__
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


def make_do_command(command_name: str, *additional_arguments):
    class _RunCommand(DoCommand):
        @classproperty
        def factory(cls):
            return cls

        @classproperty
        def command(cls) -> str:
            return command_name

        @classproperty
        def arguments(cls):
            return additional_arguments

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
        def success_chance():
            return SuccessChance.ONE

        def __init__(self, interaction, *, sequence=(), **kwargs):
            super().__init__(interaction, timing=self._timing, sequence=sequence, **kwargs)

    return _RunCommand


def create_tunable_factory_with_overrides(factory_cls, **overrides):
    tuned_values = factory_cls._tuned_values.clone_with_overrides(**overrides)

    return TunableFactory.TunableFactoryWrapper(tuned_values, factory_cls._name, factory_cls.factory)

