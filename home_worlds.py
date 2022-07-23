#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

import enum
from services import get_instance_manager
from sims4.resources import Types
from sims4.tuning.dynamic_enum import DynamicEnum
from sims4.tuning.tunable import TunablePackSafeReference, TunableMapping, TunableEnumEntry, Tunable
from sims4.tuning.tunable import OptionalTunable, TunableTuple, HasTunableFactory, AutoFactoryInit
from sims4.localization import TunableLocalizedStringFactory
from sims4.common import Pack, is_available_pack
from sims4.utils import classproperty
from interactions.utils.tunable_icon import TunableIconVariant


#######################################################################################################################
#  Enumerations                                                                                                       #
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


class HomeWorldIds(DynamicEnum):
    COMMAND_NAME_BASE = Tunable(tunable_type=str, allow_empty=False, needs_tuning=True, default='')
    DEFAULT = 0

    @classproperty
    def world_list(cls):
        return ', '.join(world.name for world in cls if world.is_available and world is not HomeWorldIds.DEFAULT)

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
    def region_data(self):
        return self.REGION_MAPPING.get(self, None)

    @property
    def region(self):
        return getattr(self.region_data, 'region', None)

    @property
    def pack(self) -> Pack:
        return getattr(self.region_data, 'pack', Pack.BASE_GAME)

    @property
    def is_available(self) -> bool:
        return is_available_pack(self.pack)

    @property
    def region_name(self):
        return getattr(self.region_data, 'name', None)

    @property
    def pie_menu_icon(self):
        return self.get_icon()

    @property
    def settings_name_base(self):
        return self.desc.replace(' ', '')

    def get_icon(self, icon_size=IconSize.SMALL):
        return getattr(self.region_data, 'icon_mapping', dict()).get(icon_size, None)


class RegionMapping(TunableMapping):
    def __init__(self, *args, **kwargs):
        kwargs['key_name'] = 'world_name'
        kwargs['key_type'] = TunableEnumEntry(tunable_type=HomeWorldIds, default=HomeWorldIds.DEFAULT)
        kwargs['value_name'] = 'region_data'

        tuple_args = dict()
        tuple_args['region'] = TunablePackSafeReference(manager=get_instance_manager(Types.REGION))
        tuple_args['name'] = TunableLocalizedStringFactory()
        tuple_args['pack'] = PackDefinition()
        tuple_args['icon_mapping'] = IconMapping()
        kwargs['value_type'] = TunableTuple(**tuple_args)

        super().__init__(*args, **kwargs)


with HomeWorldIds.make_mutable():
    HomeWorldIds.REGION_MAPPING = RegionMapping()

