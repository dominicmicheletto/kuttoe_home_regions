"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details a special interaction which toggles the notification settings.
"""


#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

# sims4 imports
from sims4.utils import flexmethod, classproperty
from sims4.tuning.tunable import TunableMapping, TunableTuple, OptionalTunable
from sims4.localization import TunableLocalizedStringFactory
from sims4.tuning.instances import lock_instance_tunables

# interaction imports
from interactions.base.picker_interaction import PickerSuperInteraction
from interactions.picker.picker_pie_menu_interaction import _PickerPieMenuProxyInteraction
from interactions.context import InteractionSource

# miscellaneous imports
from singletons import DEFAULT
from ui.ui_dialog_picker import BasePickerRow, UiItemPicker

# local imports
from kuttoe_home_regions.settings import NotificationType
from kuttoe_home_regions.ui import InteractionType
from kuttoe_home_regions.tunable.toggle_item import ToggleItemMapping, ToggleEntry
from kuttoe_home_regions.tunable.toggle_item_picker import ToggleItemPicker
from kuttoe_home_regions.interactions.mixins import DisplayNotificationMixin
from kuttoe_home_regions.interactions.toggle import ToggleSuperInteraction
from kuttoe_home_regions.utils import construct_auto_init_factory


#######################################################################################################################
# Tunable Definitions                                                                                                 #
#######################################################################################################################

class TunableEnumValueToDisplayDataMapping(TunableMapping):
    def __init__(self, *args, **kwargs):
        tuple_args = dict()
        tuple_args['pie_menu_name'] = TunableLocalizedStringFactory()
        tuple_args['row_tooltip'] = OptionalTunable(TunableLocalizedStringFactory())
        tuple_args['picker_dialog'] = ToggleItemPicker()()

        kwargs['key_type'] = NotificationType.to_enum_entry()
        kwargs['value_type'] = TunableTuple(**tuple_args)
        super().__init__(*args, **kwargs)


#######################################################################################################################
# Proxy Interactions                                                                                                  #
#######################################################################################################################

class _NotificationSettingPickerMenuProxyInteraction(ToggleSuperInteraction, _PickerPieMenuProxyInteraction):
    REMOVE_INSTANCE_TUNABLES = ('setting_key', 'command_name', 'picker_dialog', 'toggle_items')

    @classmethod
    def use_pie_menu(cls): return False

    @flexmethod
    def _use_ellipsized_name(cls, inst): return True

    @classproperty
    def notification_type(cls) -> NotificationType: return cls.picker_row_data.tag

    @classproperty
    def setting_key(cls): return cls.notification_type.setting_name

    @classproperty
    def command_name(cls):
        from kuttoe_home_regions.settings import Settings

        notif_name_builder = getattr(Settings.COMMAND_NAME_BASES, 'notification')
        return notif_name_builder._get_hash_for_suffix(cls.notification_type.pretty_name)[0]

    @classproperty
    def picker_dialog(cls): return cls._get_picker_dialog_for_enum_value(cls.notification_type)

    @classproperty
    def tooltip_base(cls):
        display_name = cls._get_display_name_for_enum_value(cls.notification_type)()

        def _tooltip_base(*args, **kwargs):
            first, *rest = args

            return cls.TOOLTIP_BASE_TEMPLATE(first, display_name, *rest, **kwargs)

        return _tooltip_base

    @classproperty
    def toggle_items(cls):
        args = dict()
        args['toggle_items'] = cls.TOGGLE_ITEMS_TEMPLATE
        args['tooltip_base'] = cls.tooltip_base

        return lambda setting_key: construct_auto_init_factory(ToggleEntry, setting_key=setting_key, **args)

    def _display_notification(self):
        display_name = self._get_display_name_for_enum_value(self.notification_type)()
        extra_args = {'toggle_value': display_name}

        self.display_notification(notification_type=NotificationType.NOTIFICATION_SETTINGS, **extra_args)


#######################################################################################################################
# Super Interactions                                                                                                  #
#######################################################################################################################

class NotificationSettingsPickerInteraction(PickerSuperInteraction, DisplayNotificationMixin):
    TOOLTIP_BASE_TEMPLATE = TunableLocalizedStringFactory()
    ENUM_VALUE_TO_DISPLAY_DATA_MAPPING = TunableEnumValueToDisplayDataMapping()
    TOGGLE_ITEMS_TEMPLATE = ToggleItemMapping()
    INSTANCE_TUNABLES = {
        'picker_dialog': UiItemPicker.TunableFactory(locked_args={'min_choices': 1, 'min_selectable': 1}),
    }

    @classmethod
    def _make_potential_interaction(cls, row_data):
        inst = _NotificationSettingPickerMenuProxyInteraction.generate(cls, picker_row_data=row_data)
        keys = {*cls.INSTANCE_TUNABLES.keys(), *DisplayNotificationMixin.INSTANCE_TUNABLES.keys()}
        keys.difference_update(_NotificationSettingPickerMenuProxyInteraction.REMOVE_INSTANCE_TUNABLES)

        for tunable_name in keys:
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
    def _get_display_name_for_enum_value(cls, enum_value: NotificationType):
        return getattr(cls.ENUM_VALUE_TO_DISPLAY_DATA_MAPPING.get(enum_value), 'pie_menu_name', None)

    @classmethod
    def _get_row_tooltip_for_enum_value(cls, enum_value: NotificationType):
        return getattr(cls.ENUM_VALUE_TO_DISPLAY_DATA_MAPPING.get(enum_value), 'row_tooltip', None)

    @classmethod
    def _get_picker_dialog_for_enum_value(cls, enum_value: NotificationType):
        return getattr(cls.ENUM_VALUE_TO_DISPLAY_DATA_MAPPING.get(enum_value), 'picker_dialog', None)

    @classmethod
    def create_row(cls, resolver, notification_type: NotificationType):
        args = dict()

        args['name'] = cls._get_display_name_for_enum_value(notification_type)(resolver)
        args['row_tooltip'] = cls._get_row_tooltip_for_enum_value(notification_type)
        args['tag'] = notification_type

        return BasePickerRow(**args)

    @flexmethod
    def picker_rows_gen(cls, inst, target=DEFAULT, context=DEFAULT, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        target = target if target is not DEFAULT else inst.target
        context = context if context is not DEFAULT else inst.context
        resolver = inst_or_cls.get_resolver(target=target, context=context, **kwargs)

        for notification_type in NotificationType.exported_values:
            yield inst_or_cls.create_row(resolver, notification_type)

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

lock_instance_tunables(NotificationSettingsPickerInteraction, interaction_type=InteractionType.NOTIFICATION)


#######################################################################################################################
# Module Exports                                                                                                      #
#######################################################################################################################

__all__ = ('NotificationSettingsPickerInteraction', )
