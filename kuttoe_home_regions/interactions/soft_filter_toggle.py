"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details interactions that toggle on and off a given world's soft filter. This is the global soft filter
setting which needs to be enabled for a world to softly allow Sims from other worlds to "pass through".
"""


#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# sims4 imports
from sims4.tuning.instances import lock_instance_tunables
from sims4.tuning.tunable import Tunable
from sims4.utils import classproperty, flexmethod
from sims4.commands import execute as execute_command

# miscellaneous imports
from services import client_manager
from singletons import DEFAULT
from ui.ui_dialog_picker import BasePickerRow

# interaction imports
from interactions.base.picker_interaction import PickerSuperInteraction
from interactions.context import InteractionSource

# local imports
from kuttoe_home_regions.interactions.home_world_picker_menu_proxy_interaction import _HomeWorldPickerMenuProxyInteraction
from kuttoe_home_regions.interactions.mixins import *
from kuttoe_home_regions.tunable.toggle_item import TunableToggleEntrySnippet
from kuttoe_home_regions.tunable.allowed_worlds_list import TunableAllowedWorldsList
from kuttoe_home_regions.ui import InteractionType, NotificationType
from kuttoe_home_regions.enum.home_worlds import HomeWorldIds
from kuttoe_home_regions.tunable.toggle_item_picker import ToggleItemPicker
from kuttoe_home_regions.utils import create_tunable_factory_with_overrides


#######################################################################################################################
#  Proxy Interactions                                                                                                 #
#######################################################################################################################

class _SoftFilterTogglePickerMenuProxyInteraction(_HomeWorldPickerMenuProxyInteraction):
    @classmethod
    def use_pie_menu(cls): return False

    @classproperty
    def client_id(cls): return client_manager().get_first_client_id()

    @classproperty
    def command_name(cls):
        from kuttoe_home_regions.settings import Settings

        base = getattr(Settings.COMMAND_NAME_BASES, 'soft')

        return base(cls.home_world)[0]

    @classmethod
    def has_valid_choice(cls, target, context, **kwargs):
        choices_count = 0

        for _ in cls.picker_rows_gen(target, context, **kwargs):
            choices_count += 1

            if choices_count >= cls.picker_dialog.min_selectable:
                return True

            return False

    @flexmethod
    def picker_rows_gen(cls, inst, target=DEFAULT, context=DEFAULT, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        target = target if target is not DEFAULT else inst.target
        context = context if context is not DEFAULT else inst.context
        resolver = inst_or_cls.get_resolver(target=target, context=context, **kwargs)

        yield from inst_or_cls.toggle_items(cls.setting_key, home_world=inst_or_cls.home_world).picker_rows_gen(resolver)

    def on_choice_selected(self, picked_choice, **kwargs):
        if picked_choice is None or type(picked_choice) is HomeWorldIds:
            return

        execute_command(f'{self.command_name} {picked_choice}', self.client_id)
        self.display_notification(notification_type=NotificationType.SETTINGS_CHANGED)

    @classproperty
    def _picker_dialog(cls):
        region_text = cls.home_world_name
        base_text = cls.picker_dialog.text

        def new_text(*args, **kwargs):
            return base_text(region_text, *args, **kwargs)

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


#######################################################################################################################
#  Super Interactions                                                                                                 #
#######################################################################################################################

class SoftFilterToggleSuperInteraction(PickerSuperInteraction, DisplayNotificationMixin, HomeWorldSortOrderMixin):
    INSTANCE_TUNABLES = {
        'allowed_worlds': TunableAllowedWorldsList(),
        'picker_dialog': ToggleItemPicker()(),
        'toggle_items': TunableToggleEntrySnippet(),
        'setting_key': Tunable(tunable_type=str, default=None, allow_empty=False),
    }

    @classmethod
    def _make_potential_interaction(cls, row_data):
        inst = _SoftFilterTogglePickerMenuProxyInteraction.generate(cls, picker_row_data=row_data)

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
    def create_row(cls, resolver, home_world: HomeWorldIds):
        args = dict()
        args['name'] = home_world.region_name()
        args['icon_info'] = home_world.get_icon()(resolver)
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

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim, target_sim=self.sim)

        yield from super()._run_interaction_gen(timeline)

    def on_multi_choice_selected(self, picked_choice, **kwargs):
        pass

    def on_choice_selected(self, picked_choice, **kwargs):
        pass


#######################################################################################################################
#  Instance Tunable Locking                                                                                           #
#######################################################################################################################

lock_instance_tunables(SoftFilterToggleSuperInteraction, interaction_type=InteractionType.SOFT_FILTER)
