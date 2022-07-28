#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# python imports
from typing import Dict, Any

# misc imports
import enum
from services import get_instance_manager
from singletons import DEFAULT

# sims 4 imports
from sims4.resources import Types
from sims4.collections import frozendict
from sims4.tuning.tunable import TunableMapping, TunableEnumEntry, Tunable, OptionalTunable, HasTunableFactory
from sims4.tuning.tunable import AutoFactoryInit, TunablePackSafeReference, TunableWorldDescription
from sims4.localization import TunableLocalizedStringFactory
from sims4.common import Pack, is_available_pack
from sims4.utils import classproperty

# interaction imports
from interactions.utils.tunable_icon import TunableIconVariant

# filter imports
from filters.tunable import LivesInRegion

# local imports
from kuttoe_home_regions.enum import DynamicFactoryEnumMetaclass, EnumItemFactory
from kuttoe_home_regions.utils import construct_auto_init_factory


#######################################################################################################################
#  Helper Tuning                                                                                                      #
#######################################################################################################################


class IconSize(enum.Int):
    SMALL = 0
    LARGE = 2


class PackDefinition(OptionalTunable):
    def __init__(self, *args, **kwargs):
        kwargs['tunable'] = TunableEnumEntry(tunable_type=Pack, default=Pack.BASE_GAME)
        kwargs['disabled_name'] = 'requires_none'
        kwargs['disabled_value'] = Pack.BASE_GAME
        kwargs['enabled_name'] = 'requires_pack'

        super().__init__(*args, **kwargs)


class IconMapping(TunableMapping):
    def __init__(self, *args, **kwargs):
        kwargs['key_name'] = 'icon_size'
        kwargs['key_type'] = TunableEnumEntry(tunable_type=IconSize, default=IconSize.SMALL)
        kwargs['value_name'] = 'resource'
        kwargs['value_type'] = TunableIconVariant()

        super().__init__(*args, **kwargs)


class IconDefinition(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = dict(icon_size=TunableEnumEntry(tunable_type=IconSize, default=IconSize.SMALL))

    def __init__(self, home_world, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._home_world: HomeWorldIds = home_world

    @property
    def home_world(self):
        return self._home_world

    @property
    def resource(self):
        return self.home_world.get_icon(self.icon_size)


class TunableIconDefinition(OptionalTunable):
    def __init__(self, *args, **kwargs):
        kwargs['tunable'] = IconDefinition.TunableFactory()
        kwargs['enabled_name'] = 'use_specific'
        kwargs['disabled_name'] = 'use_default'

        super().__init__(*args, **kwargs)


#######################################################################################################################
#  Enumerations                                                                                                       #
#######################################################################################################################


class RegionData:
    def __init__(
            self,
            region_id: int = 0,
            name=None,
            street_for_creation: int = None,
            pack: Pack = Pack.BASE_GAME,
            icon_mapping=frozendict()
    ):
        self._region_id = region_id
        self._name = name
        self._pack = pack
        self._icon_mapping = icon_mapping
        self._street_for_creation = street_for_creation

    @property
    def street_for_creation(self):
        return self._street_for_creation

    @property
    def region_name(self):
        name: TunableLocalizedStringFactory._Wrapper = self._name

        return name

    @property
    def pack(self):
        return self._pack

    @property
    def is_available(self) -> bool:
        return is_available_pack(self.pack)

    @property
    def icon_mapping(self) -> Dict[IconSize, Any]:
        return self._icon_mapping

    @property
    def pie_menu_icon(self):
        return self.get_icon()

    def get_icon(self, icon_size=IconSize.SMALL):
        return self.icon_mapping.get(icon_size, None)


@EnumItemFactory.ReprMixin(name='region_name', region_id=None, region=DEFAULT)
@EnumItemFactory.TunableReferenceMixin(region=('region_id', True))
class RegionDataFactory(EnumItemFactory):
    FACTORY_TUNABLES = {
        'region': TunablePackSafeReference(manager=get_instance_manager(Types.REGION)),
        'name': TunableLocalizedStringFactory(),
        'pack': PackDefinition(),
        'icon_mapping': IconMapping(),
        'street_for_creation': TunableWorldDescription(pack_safe=True),
    }
    FACTORY_TYPE = RegionData

    def __init__(self, *args, **kwargs):
        kwargs.update(self.FACTORY_TUNABLES)
        super().__init__(*args, **kwargs)

    @staticmethod
    def get_default(value):
        return RegionData()


class HomeWorldIds(enum.Int, metaclass=DynamicFactoryEnumMetaclass, factory_cls=RegionDataFactory):
    COMMAND_NAME_BASE = Tunable(tunable_type=str, allow_empty=False, needs_tuning=True, default='')
    DEFAULT = 0

    @classmethod
    def create_enum_set(cls, default=None, invalid_values=None, optional=False, default_enum_list=None, **kwargs):
        from sims4.tuning.tunable import OptionalTunable, TunableEnumSet

        kwargs.update(enum_default=default or HomeWorldIds.DEFAULT)
        kwargs.update(default_enum_list=default_enum_list or frozenset())
        kwargs.update(invalid_enums=invalid_values or (HomeWorldIds.DEFAULT, ))
        enum_set = TunableEnumSet(enum_type=HomeWorldIds, **kwargs)

        return OptionalTunable(enum_set) if optional else enum_set

    @classproperty
    def available_worlds(cls):
        return set(world for world in cls if world.is_available and world is not HomeWorldIds.DEFAULT)

    @classproperty
    def world_list(cls):
        return ', '.join(world.name for world in cls.available_worlds)

    @property
    def command_name_base(self):
        return self.COMMAND_NAME_BASE

    @property
    def desc(self):
        return self.name.replace('_', ' ').title()

    @property
    def pretty_name(self) -> str:
        return self.name.lower()

    @property
    def command_name(self):
        return '{}_{}'.format(self.command_name_base, self.pretty_name)

    @property
    def settings_name_base(self):
        return self.desc.replace(' ', '')

    def create_lives_in_region_filter(self, minimum_filter_score: float = 0.0, *additional_regions, **overrides):
        args = dict()

        args['minimum_filter_score'] = minimum_filter_score
        args['region'] = tuple({self.region, *additional_regions})
        args['street_for_creation'] = self.street_for_creation
        args.update(overrides)

        return construct_auto_init_factory(LivesInRegion, **args)
