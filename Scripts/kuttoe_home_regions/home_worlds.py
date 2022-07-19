#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

import re
from services import get_instance_manager
from sims4.resources import Types
from sims4.tuning.dynamic_enum import DynamicEnum
from sims4.tuning.tunable import TunablePackSafeReference, TunableMapping, TunableEnumEntry, Tunable
from sims4.tuning.tunable import OptionalTunable, TunableTuple
from sims4.localization import TunableLocalizedStringFactory
from sims4.common import Pack, is_available_pack
from interactions.utils.tunable_icon import TunableIconVariant


#######################################################################################################################
#  Enumerations                                                                                                       #
#######################################################################################################################


class PackDefinition(OptionalTunable):
    def __init__(self, *args, **kwargs):
        kwargs['tunable'] = TunableEnumEntry(tunable_type=Pack, default=Pack.BASE_GAME)
        kwargs['disabled_name'] = 'requires_none'
        kwargs['disabled_value'] = Pack.BASE_GAME
        kwargs['enabled_name'] = 'requires_pack'

        super().__init__(*args, **kwargs)


class HomeWorldIds(DynamicEnum):
    COMMAND_NAME_BASE = Tunable(tunable_type=str, allow_empty=False, needs_tuning=True, default='')
    DEFAULT = 0

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
        return getattr(self.region_data, 'pie_menu_icon', None)

    @property
    def settings_name_base(self):
        return self.desc.replace(' ', '')

    @classmethod
    def get_home_world_from_setting_name(cls, setting_name: str):
        base = setting_name.split('_')[0]
        parts = re.findall('[A-Z][^A-Z]*', base)
        name = '_'.join(parts).upper()

        return cls[name] if name in cls else cls.DEFAULT


class RegionMapping(TunableMapping):
    def __init__(self, *args, **kwargs):
        kwargs['key_name'] = 'world_name'
        kwargs['key_type'] = TunableEnumEntry(tunable_type=HomeWorldIds, default=HomeWorldIds.DEFAULT)
        kwargs['value_name'] = 'region_data'

        tuple_args = dict()
        tuple_args['region'] = TunablePackSafeReference(manager=get_instance_manager(Types.REGION))
        tuple_args['name'] = TunableLocalizedStringFactory()
        tuple_args['pack'] = PackDefinition()
        tuple_args['pie_menu_icon'] = OptionalTunable(tunable=TunableIconVariant())
        kwargs['value_type'] = TunableTuple(**tuple_args)

        super().__init__(*args, **kwargs)


with HomeWorldIds.make_mutable():
    HomeWorldIds.REGION_MAPPING = RegionMapping()

