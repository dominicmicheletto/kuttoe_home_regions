"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details interactions that allow for the tuning of a given world's soft filter. Each world selected is allowed
in or denied from a given world's soft filter, should that world already have a soft filter applied to it.
"""


#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

# sims4 imports
from sims4.tuning.tunable import OptionalTunable
from sims4.localization import TunableLocalizedStringFactory
from sims4.tuning.instances import lock_instance_tunables
from sims4.utils import flexmethod, classproperty
from sims4.commands import execute as execute_command

# miscellaneous imports
from singletons import DEFAULT
from ui.ui_dialog_picker import UiItemPicker, BasePickerRow
from event_testing.tests import TestList

# interaction imports
from interactions.base.picker_interaction import PickerSuperInteraction
from interactions.context import InteractionSource

# local imports
from kuttoe_home_regions.tests import *
from kuttoe_home_regions.commands import AlterType
from kuttoe_home_regions.ui import InteractionType, NotificationType
from kuttoe_home_regions.interactions.home_world_picker_menu_proxy_interaction import _HomeWorldPickerMenuProxyInteraction
from kuttoe_home_regions.interactions.mixins import *
from kuttoe_home_regions.tunable.allowed_worlds_list import TunableAllowedWorldsList
from kuttoe_home_regions.enum.home_worlds import HomeWorldIds
from kuttoe_home_regions.tunable.icon_definition import IconSize
from kuttoe_home_regions.utils import create_tunable_factory_with_overrides


#######################################################################################################################
# Proxy Interactions                                                                                                  #
#######################################################################################################################

class _RegionExpansionWorldSelectorPickerMenuProxyInteraction(HasEllipsizedNamedMixin, _HomeWorldPickerMenuProxyInteraction):
    @classmethod
    def use_pie_menu(cls): return False

    @classproperty
    def picker_dialog(cls): return cls.world_selector_dialog

    @classmethod
    def has_valid_choice(cls, target, context, **kwargs):
        choices_count = 0

        for _ in cls.picker_rows_gen(target, context, **kwargs):
            choices_count += 1

            if choices_count >= cls.picker_dialog.min_selectable:
                return True

            return False

    @classproperty
    def command_name(cls):
        from kuttoe_home_regions.settings import Settings

        name = cls.alter_type.name.lower()
        base = getattr(Settings.COMMAND_NAME_BASES, name)

        return base(cls.home_world)[0]

    def _on_picker_selected(self, dialog):
        if dialog.accepted:
            results = dialog.get_result_tags()
            if len(results) >= dialog.min_selectable:
                self._on_successful_picker_selection(results)

    def _on_successful_picker_selection(self, picked_choices):
        if picked_choices is None or len(picked_choices) == 0:
            return

        for choice in picked_choices:
            self._apply_filter_selection(choice)

        self.display_notification(notification_type=NotificationType.SETTINGS_CHANGED)

    def _apply_filter_selection(self, picked_choice):
        execute_command(f'{self.command_name} {picked_choice.desc}', self.client_id)

    def _run_interaction_gen(self, timeline):
        super(RegionExpansionWorldSelectorSuperInteraction, self)._run_interaction_gen(timeline)

        yield from super()._run_interaction_gen(timeline)

    @flexmethod
    def picker_rows_gen(cls, inst, target=DEFAULT, context=DEFAULT, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        target = target if target is not DEFAULT else inst.target
        context = context if context is not DEFAULT else inst.context
        resolver = inst_or_cls.get_resolver(target=target, context=context, **kwargs)

        for world in inst_or_cls._get_allowed_worlds(resolver):
            if world is not cls.home_world:
                yield inst_or_cls.create_row(resolver, world)

    @classmethod
    def _row_tests(cls, resolver, home_world: HomeWorldIds):
        tests = TestList((get_is_world_available_test(cls.home_world, home_world, cls.alter_type),))

        return tests.run_tests(resolver)

    @classmethod
    def _get_row_tooltip(cls, test_results, home_world: HomeWorldIds):
        region_name = home_world.region_name()
        target_region_name = cls.home_world_name

        if test_results.result:
            return None
        elif cls.row_tooltip is None:
            return None
        else:
            return lambda *args, **kwargs: cls.row_tooltip(region_name, target_region_name, *args, **kwargs)

    @classmethod
    def create_row(cls, resolver, home_world: HomeWorldIds):
        test_results = cls._row_tests(resolver, home_world)
        args = dict()

        args['is_enable'] = test_results.result
        args['name'] = home_world.region_name()
        args['icon_info'] = home_world.get_icon(IconSize.LARGE)(resolver)
        args['row_tooltip'] = cls._get_row_tooltip(test_results, home_world)
        args['tag'] = home_world

        return BasePickerRow(**args)


#######################################################################################################################
# Super Interactions                                                                                                  #
#######################################################################################################################

@HasPickerProxyInteractionMixin(_RegionExpansionWorldSelectorPickerMenuProxyInteraction)
class RegionExpansionWorldSelectorSuperInteraction(
    PickerSuperInteraction, DisplayNotificationMixin, HomeWorldSortOrderMixin
):
    BIDIRECTIONAL_TOGGLE_TOKEN = TunableLocalizedStringFactory()
    ENABLED_TOKEN = TunableLocalizedStringFactory()
    DISABLED_TOKEN = TunableLocalizedStringFactory()

    INSTANCE_TUNABLES = {
        'alter_type': AlterType.to_enum_entry(),
        'picker_dialog': UiItemPicker.TunableFactory(),
        'allowed_worlds': TunableAllowedWorldsList(),
        'world_selector_dialog': UiItemPicker.TunableFactory(),
        'no_worlds_available_tooltip': OptionalTunable(TunableLocalizedStringFactory()),
        'row_tooltip': OptionalTunable(TunableLocalizedStringFactory()),
        'row_name': OptionalTunable(TunableLocalizedStringFactory()),
    }

    @classmethod
    def _row_tests(cls, resolver, home_world: HomeWorldIds):
        has_worlds_test = get_worlds_available_left_test(home_world, cls.alter_type, cls.no_worlds_available_tooltip)
        tests = TestList((has_worlds_test, ))

        return tests.run_tests(resolver)

    @classmethod
    def _get_row_name(cls, home_world: HomeWorldIds):
        region_name = home_world.region_name()

        if cls.row_name is None:
            return region_name
        else:
            return cls.row_name(region_name)

    @classmethod
    def create_row(cls, resolver, home_world: HomeWorldIds):
        test_results = cls._row_tests(resolver, home_world)
        args = dict()

        args['is_enable'] = test_results.result
        args['name'] = cls._get_row_name(home_world)
        args['icon_info'] = home_world.get_icon()(resolver)
        args['row_tooltip'] = test_results.tooltip
        args['tag'] = home_world

        return BasePickerRow(**args)

    @flexmethod
    def picker_rows_gen(cls, inst, target=DEFAULT, context=DEFAULT, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        target = target if target is not DEFAULT else inst.target
        context = context if context is not DEFAULT else inst.context
        resolver = inst_or_cls.get_resolver(target=target, context=context, **kwargs)

        for world in inst_or_cls._get_allowed_worlds(resolver):
            yield inst_or_cls.create_row(resolver, world)

    @classproperty
    def _picker_dialog(cls):
        region_text = cls.home_world.region_name()

        def new_text(*tokens, **_tokens):
            from kuttoe_home_regions.settings import Settings

            base_text = cls.picker_dialog.text(region_text, *tokens, **_tokens)
            state_text = Settings.get_token('bidirectional_toggle', cls.ENABLED_TOKEN, cls.DISABLED_TOKEN)

            return cls.BIDIRECTIONAL_TOGGLE_TOKEN(base_text, state_text)

        return create_tunable_factory_with_overrides(cls.picker_dialog, text=new_text)

    def _create_dialog(self, owner, target_sim=None, target=None, **kwargs):
        if self.picker_dialog.title is None:
            title = lambda *_, **__: self.get_name(apply_name_modifiers=False)
        else:
            title = self.picker_dialog.title

        dialog = self._picker_dialog(owner, title=title, resolver=self.get_resolver())
        self._setup_dialog(dialog, **kwargs)
        dialog.set_target_sim(target_sim)
        dialog.set_target(target)
        dialog.current_selected = self._get_current_selected_count()
        dialog.add_listener(self._on_picker_selected)

        return dialog

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

lock_instance_tunables(RegionExpansionWorldSelectorSuperInteraction, interaction_type=InteractionType.SETTING_WORLD_PICKER)


#######################################################################################################################
# Module Exports                                                                                                      #
#######################################################################################################################

__all__ = ('RegionExpansionWorldSelectorSuperInteraction', )
