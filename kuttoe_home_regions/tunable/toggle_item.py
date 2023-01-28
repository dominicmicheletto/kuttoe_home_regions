"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details tunables used for creating the information that defines the picker rows on a setting toggle picker.
"""


#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

# sims4 imports
from sims4.tuning.tunable import Tunable, HasTunableFactory, AutoFactoryInit, TunableMapping, TunableTuple
from sims4.tuning.tunable import OptionalTunable
from sims4.localization import TunableLocalizedStringFactory

# miscellaneous imports
from interactions.utils.tunable_icon import TunableIconVariant
from ui.ui_dialog_picker import BasePickerRow
from singletons import DEFAULT

# local imports
from kuttoe_home_regions.utils import SnippetMixin
from kuttoe_home_regions.enum.home_worlds import HomeWorldIds


#######################################################################################################################
# Tuning Definitions                                                                                                  #
#######################################################################################################################

class ToggleItemMapping(TunableMapping):
    def __init__(self, *args, **kwargs):
        tuple_args = dict()
        tuple_args['icon'] = OptionalTunable(TunableIconVariant())
        tuple_args['item_text'] = TunableLocalizedStringFactory()
        tuple_args['item_tooltip'] = TunableLocalizedStringFactory()

        kwargs['key_name'] = 'toggle_value'
        kwargs['key_type'] = Tunable(tunable_type=str, default=None, allow_empty=False, needs_tuning=True)
        kwargs['value_name'] = 'item_info'
        kwargs['value_type'] = TunableTuple(**tuple_args)

        super().__init__(*args, **kwargs)


#######################################################################################################################
# Factory Definitions                                                                                                 #
#######################################################################################################################

class ToggleEntry(HasTunableFactory, AutoFactoryInit, SnippetMixin, snippet_name='toggle_entry'):
    FACTORY_TUNABLES = {
        'tooltip_base': TunableLocalizedStringFactory(),
        'toggle_items': ToggleItemMapping(),
    }

    @staticmethod
    def get_icon(resolver, item_info):
        if item_info.icon is None:
            return None

        return item_info.icon(resolver)

    def __init__(self, setting_key: str, home_world: HomeWorldIds = DEFAULT, *args, **kwargs):
        self._setting_key = setting_key
        self._home_world = home_world

        super().__init__(*args, **kwargs)

    @property
    def setting_key(self): return self._setting_key

    @property
    def home_world(self): return self._home_world

    @property
    def has_home_world(self): return self._home_world is not DEFAULT

    @property
    def setting_value(self):
        from kuttoe_home_regions.settings import Settings

        if not self.has_home_world:
            return Settings.settings[self._setting_key]
        else:
            return Settings.get_world_settings(self._home_world)[self._setting_key]

    def is_value_enabled(self, toggle_value: str):
        return str(self.setting_value) != toggle_value

    def get_tooltip(self, is_enabled, item_info):
        home_world, has_home_world = self._home_world, self.has_home_world
        tooltip_base = self.tooltip_base

        if is_enabled:
            return None

        def tooltip(*args, **kwargs):
            item_tooltip = item_info.item_tooltip()
            world_arg = (home_world.region_name(), ) if has_home_world else tuple()

            return tooltip_base(*world_arg, item_tooltip, *args, **kwargs)

        return tooltip

    def create_row(self, resolver, toggle_value: str, item_info):
        args = dict()
        is_enable = self.is_value_enabled(toggle_value)

        args['name'] = item_info.item_text()
        args['icon_info'] = self.get_icon(resolver, item_info)
        args['is_enable'] = is_enable
        args['row_tooltip'] = self.get_tooltip(is_enable, item_info)
        args['tag'] = toggle_value

        return BasePickerRow(**args)

    def picker_rows_gen(self, resolver):
        for (toggle_value, item_info) in self.toggle_items.items():
            yield self.create_row(resolver, toggle_value, item_info)


#######################################################################################################################
#  Module Exports                                                                                                     #
#######################################################################################################################

(TunableToggleEntryReference, TunableToggleEntrySnippet) = ToggleEntry._snippet
__all__ = ('TunableToggleEntryReference', 'TunableToggleEntrySnippet', 'ToggleEntry', 'ToggleItemMapping', )
