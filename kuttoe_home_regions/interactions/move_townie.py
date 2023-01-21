"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details interactions that move townies around, assigning them a given home world.
"""


#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# sims4 imports
from sims4.localization import TunableLocalizedStringFactory
from sims4.tuning.instances import lock_instance_tunables
from sims4.tuning.tunable import Tunable, OptionalTunable, TunableEnumEntry
from sims4.commands import execute as execute_command
from sims4.utils import classproperty, flexmethod

# interaction imports
from interactions.base.picker_interaction import PickerSuperInteraction, SimPickerInteraction
from interactions import ParticipantType, ParticipantTypeSingle
from interactions.context import InteractionSource

# miscellaneous imports
from services import client_manager, sim_info_manager
from singletons import DEFAULT
from ui.ui_dialog_picker import BasePickerRow, UiItemPicker, UiSimPicker
from event_testing.tests import TestList, TunableTestSet
from filters.tunable import TunableSimFilter

# local imports
from kuttoe_home_regions.interactions.mixins import *
from kuttoe_home_regions.interactions.home_world_picker_menu_proxy_interaction import _HomeWorldPickerMenuProxyInteraction
from kuttoe_home_regions.tunable.allowed_worlds_list import TunableAllowedWorldsList
from kuttoe_home_regions.enum.home_worlds import HomeWorldIds
from kuttoe_home_regions.utils import create_tunable_factory_with_overrides
from kuttoe_home_regions.ui import InteractionType


#######################################################################################################################
#  Proxy Interactions                                                                                                 #
#######################################################################################################################

class _MoveMultipleTowniesPickerPieMenuProxyInteraction(_HomeWorldPickerMenuProxyInteraction, SimPickerInteraction):
    REMOVE_INSTANCE_TUNABLES = ('picker_dialog', 'pie_menu_priority', )

    @classmethod
    def _additional_sim_tests(cls):
        region_test = cls.get_home_region_test(cls.home_world, participant=ParticipantType.Actor, tooltip=None, negate=True)

        return TestList((region_test, ))

    @flexmethod
    def _get_valid_sim_choices_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        super_result = super()._get_valid_sim_choices_gen(target, context, **kwargs)
        additional_sim_tests = inst_or_cls._additional_sim_tests()

        for filter_result in super_result:
            sim_info = filter_result.sim_info
            resolver = sim_info.get_resolver()
            result = additional_sim_tests.run_tests(resolver)

            if result:
                yield filter_result

    @staticmethod
    def get_sim_info(sim_id: int): return sim_info_manager().get(sim_id)

    @classmethod
    def get_sim_infos(cls, *sim_ids: int): return tuple(cls.get_sim_info(sim_id) for sim_id in sim_ids)

    @classproperty
    def picker_dialog(cls):
        region_text = cls.home_world_name
        base_text = cls.sim_picker_dialog.text

        def new_text(*args, **kwargs):
            return base_text(region_text, *args, **kwargs)

        return create_tunable_factory_with_overrides(cls.sim_picker_dialog, text=new_text)

    @classmethod
    def use_pie_menu(cls): return False

    def _push_continuations(self, *args, **kwargs):
        super()._push_continuations(*args, **kwargs)

        picked_choice = args[0]
        if picked_choice is None or len(picked_choice) == 0 or type(picked_choice[0]) is HomeWorldIds:
            return

        for choice in picked_choice:
            self._move_townie(choice)

        self.display_notification(sim_infos=self.get_sim_infos(*picked_choice))

    def _run_interaction_gen(self, timeline):
        super(SimPickerInteraction, self)._run_interaction_gen(timeline)

        yield from super()._run_interaction_gen(timeline)

    def _move_townie(self, picked_choice):
        execute_command(f'{self.COMMAND_NAME} {picked_choice} {self.home_world.desc}', self.client_id)


#######################################################################################################################
#  Super Interactions                                                                                                 #
#######################################################################################################################

class MoveTownieSuperInteraction(
    PickerSuperInteraction, DisplayNotificationMixin, HomeWorldSortOrderMixin, HasHomeWorldMixin
):
    COMMAND_NAME = Tunable(tunable_type=str, default=None, allow_empty=False)
    INSTANCE_TUNABLES = {
        'picker_dialog': UiItemPicker.TunableFactory(locked_args={'min_choices': 1, 'min_selectable': 1}),
        'allowed_worlds': TunableAllowedWorldsList(),
        'row_tooltip': OptionalTunable(TunableLocalizedStringFactory()),
    }

    @classmethod
    def _make_potential_interaction(cls, row_data):
        return _HomeWorldPickerMenuProxyInteraction.generate(cls, picker_row_data=row_data)

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

    @classproperty
    def client_id(cls):
        return client_manager().get_first_client_id()

    @classmethod
    def has_valid_choice(cls, target, context, **kwargs):
        choices_count = 0

        for _ in cls.picker_rows_gen(target, context, **kwargs):
            choices_count += 1

            if choices_count >= cls.picker_dialog.min_selectable:
                return True

            return False

    @classmethod
    def _row_tests(cls, resolver, home_world: HomeWorldIds):
        tests = TestList((cls.get_home_region_test(home_world), ))

        return tests.run_tests(resolver)

    @classmethod
    def _get_row_tooltip(cls, resolver, test_results, home_world: HomeWorldIds):
        if test_results.tooltip is not None and not test_results.result:
            return test_results.tooltip

        sim_info = resolver.get_participant(ParticipantType.TargetSim)
        region_name = home_world.region_name()

        if cls.row_tooltip is None:
            return None
        return lambda *args, **kwargs: cls.row_tooltip(sim_info, region_name, *args, **kwargs)

    @classmethod
    def create_row(cls, resolver, home_world: HomeWorldIds):
        test_results = cls._row_tests(resolver, home_world)
        args = dict()

        args['is_enable'] = test_results.result
        args['name'] = home_world.region_name()
        args['icon_info'] = home_world.get_icon()(resolver)
        args['row_tooltip'] = cls._get_row_tooltip(resolver, test_results, home_world)
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
        self._show_picker_dialog(self.sim, target_sim=self.target)

        yield from super()._run_interaction_gen(timeline)

    def on_choice_selected(self, picked_choice, **kwargs):
        self._move_townie(picked_choice)

        self.display_notification(sim_infos=(self.target,))

    def on_multi_choice_selected(self, picked_choice, **kwargs):
        pass

    def _move_townie(self, picked_choice):
        sim_id = self.target.sim_id

        execute_command(f'{self.COMMAND_NAME} {sim_id} {picked_choice.desc}', self.client_id)


class MoveMultipleTowniesSuperInteraction(MoveTownieSuperInteraction):
    INSTANCE_TUNABLES = {
        'include_actor_sim': Tunable(tunable_type=bool, default=False),
        'include_target_sim': Tunable(tunable_type=bool, default=False),
        'include_uninstantiated_sims': Tunable(tunable_type=bool, default=True),
        'sim_filter': OptionalTunable(
            tunable=TunableSimFilter.TunablePackSafeReference(),
            disabled_name='no_filter', enabled_name='sim_filter_selected'),
        'sim_filter_household_override': OptionalTunable(
            tunable=TunableEnumEntry(tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.TargetSim,
                                     invalid_enums=(ParticipantTypeSingle.Actor,))),
        'sim_filter_requesting_sim': TunableEnumEntry(tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor),
        'create_sim_if_no_valid_choices': Tunable(tunable_type=bool, default=False),
        'sim_tests': TunableTestSet(),
        'sim_picker_dialog': UiSimPicker.TunableFactory(),
    }

    @classmethod
    def _make_potential_interaction(cls, row_data):
        inst = _MoveMultipleTowniesPickerPieMenuProxyInteraction.generate(cls, picker_row_data=row_data)

        for tunable_name in cls.INSTANCE_TUNABLES.keys():
            setattr(inst, tunable_name, getattr(cls, tunable_name))

        return inst

    def on_choice_selected(self, picked_choice, **kwargs):
        pass


#######################################################################################################################
#  Instance Tunable Locking                                                                                           #
#######################################################################################################################

lock_instance_tunables(MoveTownieSuperInteraction, interaction_type=InteractionType.COMMAND)
lock_instance_tunables(MoveMultipleTowniesSuperInteraction, interaction_type=InteractionType.PICKER)
