"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details an interaction that allows for setting the soft filter value for specific worlds.
"""


#######################################################################################################################
# Imports                                                                                                            #
#######################################################################################################################

# sims4 imports
from sims4.tuning.instances import lock_instance_tunables
from sims4.tuning.tunable import TunableVariant, OptionalTunable, Tunable
from sims4.utils import classproperty, flexmethod, exception_protected
from sims4.localization import TunableLocalizedStringFactory, LocalizationHelperTuning

# miscellaneous imports
from singletons import DEFAULT
from event_testing.tests import TestList

# ui imports
from ui.ui_dialog_picker import BasePickerRow
from ui.ui_dialog_generic import UiDialogTextInputOk, UiDialogTextInputOkCancel

# interaction imports
from interactions.base.picker_interaction import PickerSuperInteraction
from interactions.context import InteractionSource

# local imports
from kuttoe_home_regions.interactions.home_world_picker_menu_proxy_interaction import _HomeWorldPickerMenuProxyInteraction
from kuttoe_home_regions.interactions.mixins import *
from kuttoe_home_regions.tunable.allowed_worlds_list import TunableAllowedWorldsList
from kuttoe_home_regions.ui import InteractionType, NotificationType
from kuttoe_home_regions.enum.home_worlds import HomeWorldIds
from kuttoe_home_regions.utils import create_tunable_factory_with_overrides
from kuttoe_home_regions.commands import kuttoe_set_region_soft_filter_value
from kuttoe_home_regions.tests import get_soft_filter_enabled_test


#######################################################################################################################
# Proxy Interactions                                                                                                  #
#######################################################################################################################

class _SetSoftFilterValuePickerMenuProxyInteraction(_HomeWorldPickerMenuProxyInteraction):
    @classmethod
    def use_pie_menu(cls): return False

    @classproperty
    def text_input_overrides(cls):
        from kuttoe_home_regions.settings import Settings

        overrides = dict()
        value = str(cls.world_settings[Settings.WorldSettingNames.SOFT_FILTER_VALUE])
        overrides[cls.TEXT_INPUT_SOFT_FILTER_VALUE] = lambda *_, **__: LocalizationHelperTuning.get_raw_text(value)

        return overrides

    @exception_protected
    def _on_response(self, dialog):
        if not dialog.accepted:
            return False

        soft_filter_value = dialog.text_input_responses.get(self.TEXT_INPUT_SOFT_FILTER_VALUE)
        try:
            soft_filter_value = float(soft_filter_value)
            valid = kuttoe_set_region_soft_filter_value(self.home_world, soft_filter_value, _connection=self.client_id)

            if not valid:
                raise ValueError(f'Invalid soft toggle value: {valid}')
        except ValueError:
            self._show_input_dialog(is_error=True)
        else:
            args = dict(regions=(self.home_world, ), filter_value=soft_filter_value)
            self.display_notification(notification_type=NotificationType.SETTINGS_CHANGED, **args)

        return True

    def _show_input_dialog(self, is_error: bool = False):
        def new_text(*tokens, **_tokens):
            base_text = self.set_value_dialog.text(self.MIN_VALUE, self.MAX_VALUE, *tokens, **_tokens)

            if is_error and self.invalid_entry_warning is not None:
                return self.invalid_entry_warning(base_text)
            return base_text

        def new_title(*tokens, **_tokens):
            region_text = self.home_world.region_name()
            return self.set_value_dialog.title(region_text, *tokens, **_tokens)

        dialog_cls = create_tunable_factory_with_overrides(self.set_value_dialog, text=new_text, title=new_title)
        dialog = dialog_cls(None, self.get_resolver())
        dialog.show_dialog(on_response=self._on_response, text_input_overrides=self.text_input_overrides)

    def _run_interaction_gen(self, timeline):
        self._show_input_dialog(False)
        return True


#######################################################################################################################
# Super Interactions                                                                                                  #
#######################################################################################################################

class SetSoftFilterValueImmediateSuperInteraction(PickerSuperInteraction, DisplayNotificationMixin, HomeWorldSortOrderMixin):
    TEXT_INPUT_SOFT_FILTER_VALUE = 'soft_filter_value'
    MIN_VALUE = Tunable(tunable_type=float, default=0.0)
    MAX_VALUE = Tunable(tunable_type=float, default=1.0)

    INSTANCE_TUNABLES = {
        'set_value_dialog': TunableVariant(
            ok_dialog=UiDialogTextInputOk.TunableFactory(text_inputs=(TEXT_INPUT_SOFT_FILTER_VALUE,)),
            ok_cancel_dialog=UiDialogTextInputOkCancel.TunableFactory(text_inputs=(TEXT_INPUT_SOFT_FILTER_VALUE,)),
        ),
        'allowed_worlds': TunableAllowedWorldsList(),
        'invalid_entry_warning': OptionalTunable(TunableLocalizedStringFactory()),
        'soft_filter_disabled_tooltip': OptionalTunable(TunableLocalizedStringFactory()),
    }

    @classmethod
    def _make_potential_interaction(cls, row_data):
        inst = _SetSoftFilterValuePickerMenuProxyInteraction.generate(cls, picker_row_data=row_data)

        for tunable_name in cls.INSTANCE_TUNABLES.keys():
            setattr(inst, tunable_name, getattr(cls, tunable_name))

        return inst

    @classmethod
    def potential_interactions(cls, target, context, **kwargs):
        if cls.use_pie_menu():
            if context.source == InteractionSource.AUTONOMY and not cls.allow_autonomous:
                return

            recipe_ingredients_map = {}
            funds_source = cls.funds_source if hasattr(cls, 'funds_source') else None
            kwargs['recipe_ingredients_map'] = recipe_ingredients_map

            for row_data in cls.picker_rows_gen(target, context, funds_source=funds_source, **kwargs):
                if not row_data.available_as_pie_menu:
                    pass
                else:
                    affordance = cls._make_potential_interaction(row_data)
                    for aop in affordance.potential_interactions(target, context, **kwargs):
                        yield aop
        else:
            yield from super().potential_interactions(target, context, **kwargs)

    @classmethod
    def _row_tests(cls, resolver, home_world: HomeWorldIds):
        soft_filter_enabled_test = get_soft_filter_enabled_test(home_world, cls.soft_filter_disabled_tooltip)
        tests = TestList((soft_filter_enabled_test, ))

        return tests.run_tests(resolver)

    @classmethod
    def create_row(cls, resolver, home_world: HomeWorldIds):
        test_results = cls._row_tests(resolver, home_world)
        args = dict()

        args['is_enable'] = test_results.result
        args['name'] = home_world.region_name()
        args['icon_info'] = home_world.get_icon()(resolver)
        args['tag'] = home_world
        args['row_tooltip'] = test_results.tooltip

        return BasePickerRow(**args)

    @flexmethod
    def picker_rows_gen(cls, inst, target=DEFAULT, context=DEFAULT, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        target = target if target is not DEFAULT else inst.target
        context = context if context is not DEFAULT else inst.context
        resolver = inst_or_cls.get_resolver(target=target, context=context, **kwargs)

        for world in inst_or_cls._get_allowed_worlds(resolver):
            yield inst_or_cls.create_row(resolver, world)

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(None, target_sim=self.sim)

        yield from super()._run_interaction_gen(timeline)

    def on_multi_choice_selected(self, picked_choice, **kwargs):
        pass

    def on_choice_selected(self, picked_choice, **kwargs):
        pass


#######################################################################################################################
# Instance Tunable Locking                                                                                            #
#######################################################################################################################

lock_instance_tunables(SetSoftFilterValueImmediateSuperInteraction, interaction_type=InteractionType.SOFT_FILTER_VALUE)
