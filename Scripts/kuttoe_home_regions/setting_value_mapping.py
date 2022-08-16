#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

from snippets import define_snippet
from sims4.tuning.tunable import AutoFactoryInit, OptionalTunable, Tunable, TunableMapping, HasTunableSingletonFactory
from sims4.tuning.tunable import TunableTuple
from sims4.localization import TunableLocalizedStringFactory
from interactions.utils.tunable_icon import TunableIconVariant


#######################################################################################################################
#  Tunables                                                                                                           #
#######################################################################################################################


class SettingValueMapping(TunableMapping):
    def __init__(self, *args, **kwargs):
        kwargs['key_name'] = 'setting_value'
        kwargs['key_type'] = Tunable(tunable_type=bool, default=False)
        kwargs['value_name'] = 'display_data'

        tuple_args = dict()
        tuple_args['text'] = TunableLocalizedStringFactory()
        tuple_args['pie_menu_icon'] = OptionalTunable(TunableIconVariant())
        kwargs['value_type'] = TunableTuple(**tuple_args)

        super().__init__(*args, **kwargs)


class SettingValue(AutoFactoryInit, HasTunableSingletonFactory):
    FACTORY_TUNABLES = {
        'setting_value_mapping': SettingValueMapping(),
    }

    def get_display_data(self, toggle_value: bool):
        return self.setting_value_mapping[toggle_value]


(_, TunableSettingValue) = define_snippet('setting_value', SettingValue.TunableFactory())
