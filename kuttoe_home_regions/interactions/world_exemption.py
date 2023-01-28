"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details interactions that add and remove world exemptions. World exemptions are special bypasses on a
per-Sim and a per-World basis, wherein certain Sims can bypass the mod's filters and be in specific Worlds.
"""


#######################################################################################################################
# Imports                                                                                                            #
#######################################################################################################################

# sims4 imports
from sims4.tuning.instances import lock_instance_tunables
from sims4.tuning.tunable import Tunable, OptionalTunable
from sims4.localization import TunableLocalizedStringFactory, NULL_LOCALIZED_STRING_FACTORY
from sims4.commands import execute as execute_command
from sims4.utils import classproperty, flexmethod

# interaction imports
from interactions.base.picker_interaction import PickerSuperInteraction
from interactions import ParticipantType

# miscellaneous imports
from services import client_manager
from singletons import DEFAULT
from event_testing.tests import TestList
from ui.ui_dialog_picker import BasePickerRow, UiItemPicker

# local imports
from kuttoe_home_regions.enum.home_worlds import HomeWorldIds
from kuttoe_home_regions.filters.statistics import UsesAllowedRegionsBitsetMixin
from kuttoe_home_regions.tunable.icon_definition import IconSize
from kuttoe_home_regions.interactions.mixins import DisplayNotificationMixin, HomeWorldSortOrderMixin, HasHomeWorldMixin
from kuttoe_home_regions.ui import InteractionType, NotificationType
from kuttoe_home_regions.tunable.allowed_worlds_list import TunableAllowedWorldsList


#######################################################################################################################
# Base Super Interaction                                                                                             #
#######################################################################################################################

class WorldExemptionSuperInteraction(
    PickerSuperInteraction, UsesAllowedRegionsBitsetMixin, DisplayNotificationMixin, HomeWorldSortOrderMixin,
    HasHomeWorldMixin,
):
    SIM_LIVES_THERE_TOOLTIP = TunableLocalizedStringFactory()
    INSTANCE_TUNABLES = {
        'command_name': Tunable(tunable_type=str, default=None, allow_empty=False),
        'row_description': OptionalTunable(TunableLocalizedStringFactory()),
        'row_tooltip': OptionalTunable(TunableLocalizedStringFactory()),
        'picker_dialog': UiItemPicker.TunableFactory(),
        'allowed_worlds': TunableAllowedWorldsList(),
    }

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

    @flexmethod
    def picker_rows_gen(cls, inst, target=DEFAULT, context=DEFAULT, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        target = target if target is not DEFAULT else inst.target
        context = context if context is not DEFAULT else inst.context
        resolver = inst_or_cls.get_resolver(target=target, context=context, **kwargs)

        for world in inst_or_cls._get_allowed_worlds(resolver):
            yield inst_or_cls.create_row(resolver, world)

    @classmethod
    def _get_sim_info(cls, resolver):
        return resolver.get_participant(ParticipantType.TargetSim) or resolver.get_participant(ParticipantType.Actor)

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.target, target_sim=self.target)

        return True

    @classmethod
    def _row_tests(cls, resolver, home_world: HomeWorldIds):
        tests = TestList((cls.get_home_region_test(home_world, tooltip=None), ))

        return tests.run_tests(resolver)

    @classmethod
    def _get_row_description(cls, resolver, home_world: HomeWorldIds):
        sim_info = cls._get_sim_info(resolver)
        region_name = home_world.region_name()

        if cls.row_description is None:
            return None
        return cls.row_description(sim_info, region_name)

    @classmethod
    def get_sim_lives_in_region_tooltip(cls, sim_info, home_world: HomeWorldIds):
        if not cls.SIM_LIVES_THERE_TOOLTIP:
            return NULL_LOCALIZED_STRING_FACTORY

        region_name = home_world.region_name()
        return lambda *args, **kwargs: cls.SIM_LIVES_THERE_TOOLTIP(sim_info, region_name, *args, **kwargs)

    @classmethod
    def _get_row_tooltip(cls, resolver, row_test_results, home_world: HomeWorldIds):
        sim_info = cls._get_sim_info(resolver)
        region_name = home_world.region_name()

        if not row_test_results:
            return cls.get_sim_lives_in_region_tooltip(sim_info, home_world)
        elif not cls.row_tooltip:
            return NULL_LOCALIZED_STRING_FACTORY
        return lambda *args, **kwargs: cls.row_tooltip(sim_info, region_name, *args, **kwargs)

    @classmethod
    def create_row(cls, resolver, home_world: HomeWorldIds):
        args = dict()
        row_test_results = cls._row_tests(resolver, home_world)

        args['is_enable'] = row_test_results.result
        args['name'] = home_world.region_name()
        args['icon_info'] = home_world.get_icon(IconSize.LARGE)(resolver)
        args['row_description'] = cls._get_row_description(resolver, home_world)
        args['row_tooltip'] = cls._get_row_tooltip(resolver, row_test_results, home_world)
        args['tag'] = home_world

        return BasePickerRow(**args)

    def on_multi_choice_selected(self, picked_choice, **kwargs):
        self._perform_world_exemption(picked_choice)

    def on_choice_selected(self, picked_choice, **kwargs):
        self._perform_world_exemption(picked_choice)

    def _perform_world_exemption(self, picked_choice):
        if picked_choice is None or len(picked_choice) == 0:
            return

        self.display_notification(regions=picked_choice, notification_type=NotificationType.WORLD_EXEMPTION)

        sim_info = self._get_sim_info(self.get_resolver(target=self.target, context=self.context))
        sim_id = sim_info.sim_id

        for world in picked_choice:
            execute_command(f'{self.command_name} {sim_id} {world.desc}', self.client_id)


#######################################################################################################################
# Instance Tuning Locking                                                                                            #
#######################################################################################################################

lock_instance_tunables(WorldExemptionSuperInteraction, interaction_type=InteractionType.WORLD_SELECTION)
