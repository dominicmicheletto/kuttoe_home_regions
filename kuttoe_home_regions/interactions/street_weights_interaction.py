"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details interactions that allow for altering the weight of the creation streets on a per-world basis. There is
a Picker of Worlds -> Picker of Streets -> Text Input pipeline.
"""


#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

# sims4 imports
from sims4.tuning.tunable import OptionalTunable, TunableVariant, Tunable, TunableMapping
from sims4.localization import TunableLocalizedStringFactory, LocalizationHelperTuning
from sims4.tuning.instances import lock_instance_tunables
from sims4.utils import flexmethod, classproperty, exception_protected
from sims4.collections import frozendict

# miscellaneous imports
from singletons import DEFAULT
from collections import namedtuple
from ui.ui_dialog_picker import UiItemPicker, BasePickerRow
from ui.ui_dialog_generic import UiDialogTextInputOk, UiDialogTextInputOkCancel

# interaction imports
from interactions.base.picker_interaction import PickerSuperInteraction

# local imports
from kuttoe_home_regions.ui import InteractionType, NotificationType
from kuttoe_home_regions.interactions.mixins import *
from kuttoe_home_regions.enum.home_worlds import HomeWorldIds
from kuttoe_home_regions.enum.neighbourhood_streets import NeighbourhoodStreets
from kuttoe_home_regions.commands.base_commands import kuttoe_alter_street_weights, AlterStreetWeightReasons
from kuttoe_home_regions.utils import create_tunable_factory_with_overrides
from kuttoe_home_regions.interactions.home_world_picker_menu_proxy_interaction import _HomeWorldPickerMenuProxyInteraction
from kuttoe_home_regions.tunable.allowed_worlds_list import TunableAllowedWorldsList


#######################################################################################################################
# Picked Row Data                                                                                                     #
#######################################################################################################################

WorldAndStreetData = namedtuple('WorldAndStreetData', ['home_world', 'street'])


#######################################################################################################################
# Miscellaneous Tuning                                                                                                #
#######################################################################################################################

class TunableInvalidWarningEntryMapping(TunableMapping):
    def __init__(self, *args, **kwargs):
        kwargs['key_type'] = AlterStreetWeightReasons.to_enum_entry()
        kwargs['key_name'] = 'reason'
        kwargs['value_type'] = TunableLocalizedStringFactory()
        kwargs['value_name'] = 'string'

        super().__init__(*args, **kwargs)


#######################################################################################################################
# Proxy Interactions                                                                                                  #
#######################################################################################################################

class _StreetWeightsPickerMenuProxyInteraction(HasEllipsizedNamedMixin, _HomeWorldPickerMenuProxyInteraction):
    @classmethod
    def use_pie_menu(cls): return False

    @classmethod
    def has_valid_choice(cls, target, context, **kwargs):
        choices_count = 0

        for _ in cls.picker_rows_gen(target, context, **kwargs):
            choices_count += 1

            if choices_count >= cls.picker_dialog.min_selectable:
                return True

            return False

    @classproperty
    def picker_dialog(cls): return cls.street_picker_dialog

    @classproperty
    def creation_street(cls): return cls.home_world.street_for_creation

    @classproperty
    def street_weights(cls):
        street_keys = cls.creation_street.streets_list.keys()
        creation_street = cls.creation_street

        def get_weights(key):
            return creation_street.get_default_weight(key), creation_street[key]

        return frozendict({key: get_weights(key) for key in street_keys})

    @classmethod
    def _get_row_description(cls, street: NeighbourhoodStreets):
        if cls.row_description is None:
            return None

        default, current = cls.street_weights[street]
        return cls.row_description(default, current)

    @classmethod
    def _get_row_tooltip(cls, street: NeighbourhoodStreets):
        if cls.street_picker_tooltip is None:
            return None

        return lambda *_, **__: cls.street_picker_tooltip(cls.home_world_name, street.street_name(), *_, **__)

    def _create_dialog(self, owner, target_sim=None, target=None, **kwargs):
        if self.picker_dialog.title is None:
            title = lambda *_, **__: self.get_name(apply_name_modifiers=False)
        else:
            title = self.picker_dialog.title

        def new_title(*token_args, **token_kwargs):
            return title(self.home_world_name, *token_args, **token_kwargs)

        def new_text(*token_args, **token_kwargs):
            return self.picker_dialog.text(self.home_world_name, *token_args, **token_kwargs)

        dialog = self.picker_dialog(owner, title=new_title, text=new_text, resolver=self.get_resolver())
        self._setup_dialog(dialog, **kwargs)
        dialog.set_target_sim(target_sim)
        dialog.set_target(target)
        dialog.current_selected = self._get_current_selected_count()
        dialog.add_listener(self._on_picker_selected)

        return dialog

    @classmethod
    def create_row(cls, resolver, street: NeighbourhoodStreets):
        args = dict()

        args['is_enable'] = True
        args['name'] = street.street_name()
        args['row_description'] = cls._get_row_description(street)
        args['row_tooltip'] = cls._get_row_tooltip(street)
        args['tag'] = WorldAndStreetData(cls.home_world, street)
        args['icon_info'] = street.icon(resolver) if street.icon else None

        return BasePickerRow(**args)

    @flexmethod
    def picker_rows_gen(cls, inst, target=DEFAULT, context=DEFAULT, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        target = target if target is not DEFAULT else inst.target
        context = context if context is not DEFAULT else inst.context
        resolver = inst_or_cls.get_resolver(target=target, context=context, **kwargs)

        for street in inst_or_cls.creation_street.streets_list.keys():
            yield inst_or_cls.create_row(resolver, street)

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(None, target_sim=self.sim)

        yield from super()._run_interaction_gen(timeline)

    @classmethod
    def text_input_overrides(cls, street: NeighbourhoodStreets):
        overrides = dict()
        value = str(cls.creation_street[street])
        overrides[cls.TEXT_INPUT_STREET_WEIGHT_VALUE] = lambda *_, **__: LocalizationHelperTuning.get_raw_text(value)

        return overrides

    @exception_protected
    def _on_text_input_response(self, dialog, street: NeighbourhoodStreets):
        if not dialog.accepted:
            return False

        street_weight_value = dialog.text_input_responses.get(self.TEXT_INPUT_STREET_WEIGHT_VALUE)
        try:
            street_weight_value = float(street_weight_value)
            valid = kuttoe_alter_street_weights(street, self.home_world, street_weight_value, _connection=self.client_id)

            if not valid:
                raise ValueError(valid)
        except ValueError as ex:
            arg = ex.args[0]
            error_reason = AlterStreetWeightReasons.INVALID_VALUE if type(arg) is str else arg.reason

            self._show_input_dialog(error_reason=error_reason, street=street)
        else:
            args = dict(regions=(self.home_world,), street=street, form_value=street_weight_value)
            self.display_notification(notification_type=NotificationType.SETTINGS_CHANGED, **args)

        return True

    def _show_input_dialog(self, street: NeighbourhoodStreets, error_reason: AlterStreetWeightReasons = None):
        region_text = self.home_world_name
        street_text = street.street_name()

        def new_text(*tokens, **_tokens):
            base_text = self.set_value_dialog.text(street_text, self.MIN_VALUE, *tokens, **_tokens)

            if error_reason is not None:
                invalid_entry_warning = self.get_invalid_entry_warning(error_reason)

                return invalid_entry_warning(base_text) if invalid_entry_warning is not None else base_text
            return base_text

        def new_title(*tokens, **_tokens):
            return self.set_value_dialog.title(region_text, street_text, *tokens, **_tokens)

        def _on_response(input_dialog):
            return self._on_text_input_response(input_dialog, street=street)

        dialog_cls = create_tunable_factory_with_overrides(self.set_value_dialog, text=new_text, title=new_title)
        dialog = dialog_cls(None, self.get_resolver())
        dialog.show_dialog(on_response=_on_response, text_input_overrides=self.text_input_overrides(street))

    def on_choice_selected(self, picked_choice, **_):
        if type(picked_choice) is not WorldAndStreetData:
            return

        self._show_input_dialog(picked_choice.street)

    @classmethod
    def get_invalid_entry_warning(cls, reason: AlterStreetWeightReasons):
        if cls.invalid_entry_warning is None:
            return None

        return cls.invalid_entry_warning.get(reason, None)


#######################################################################################################################
# Super Interactions                                                                                                  #
#######################################################################################################################

@HasPickerProxyInteractionMixin(_StreetWeightsPickerMenuProxyInteraction)
class StreetWeightsPickerSuperInteraction(PickerSuperInteraction, DisplayNotificationMixin, HomeWorldSortOrderMixin):
    TEXT_INPUT_STREET_WEIGHT_VALUE = 'street_weight_value'
    MIN_VALUE = Tunable(tunable_type=float, default=0.0)

    INSTANCE_TUNABLES = {
        'row_description': OptionalTunable(TunableLocalizedStringFactory()),
        'street_picker_dialog': UiItemPicker.TunableFactory(),
        'row_tooltip': OptionalTunable(TunableLocalizedStringFactory()),
        'street_picker_tooltip': OptionalTunable(TunableLocalizedStringFactory()),
        'set_value_dialog': TunableVariant(
            ok_dialog=UiDialogTextInputOk.TunableFactory(text_inputs=(TEXT_INPUT_STREET_WEIGHT_VALUE,)),
            ok_cancel_dialog=UiDialogTextInputOkCancel.TunableFactory(text_inputs=(TEXT_INPUT_STREET_WEIGHT_VALUE,)),
        ),
        'invalid_entry_warning': OptionalTunable(TunableInvalidWarningEntryMapping()),
        'allowed_worlds': TunableAllowedWorldsList(),
    }

    @classmethod
    def _get_row_tooltip(cls, home_world: HomeWorldIds):
        if cls.row_tooltip is None:
            return None

        return lambda *_, **__: cls.row_tooltip(home_world.region_name(), *_, **__)

    @classmethod
    def create_row(cls, resolver, home_world: HomeWorldIds):
        args = dict()

        args['is_enable'] = True
        args['name'] = home_world.region_name()
        args['icon_info'] = home_world.get_icon()(resolver)
        args['row_tooltip'] = cls._get_row_tooltip(home_world)
        args['tag'] = home_world

        return BasePickerRow(**args)

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(None, target_sim=self.sim)

        yield from super()._run_interaction_gen(timeline)

    def on_multi_choice_selected(self, picked_choice, **kwargs):
        pass

    def on_choice_selected(self, picked_choice, **kwargs):
        pass

    @flexmethod
    def picker_rows_gen(cls, inst, target=DEFAULT, context=DEFAULT, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        target = target if target is not DEFAULT else inst.target
        context = context if context is not DEFAULT else inst.context
        resolver = inst_or_cls.get_resolver(target=target, context=context, **kwargs)

        for world in inst_or_cls._get_allowed_worlds(resolver):
            yield inst_or_cls.create_row(resolver, world)


#######################################################################################################################
# Instance Tunable Locking                                                                                            #
#######################################################################################################################

lock_instance_tunables(StreetWeightsPickerSuperInteraction, interaction_type=InteractionType.STREET_WEIGHTS)


#######################################################################################################################
# Module Exports                                                                                                      #
#######################################################################################################################

__all__ = ('StreetWeightsPickerSuperInteraction', )
