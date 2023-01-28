"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details mixins that are used amongst all the custom interactions.
"""


#######################################################################################################################
# Imports                                                                                                            #
#######################################################################################################################

# sims4 imports
from sims4.localization import TunableLocalizedStringFactory
from sims4.utils import classproperty, flexmethod
from sims4.tuning.tunable import OptionalTunable, Tunable, TunableRange, TunableMapping

# miscellaneous imports
import services
from singletons import DEFAULT
from interactions import ParticipantType

# local imports
from kuttoe_home_regions.ui import InteractionType, NotificationType, TunableNotificationSnippet
from kuttoe_home_regions.utils import construct_auto_init_factory
from kuttoe_home_regions.enum.home_worlds import HomeWorldIds, WorldType


#######################################################################################################################
# Helper Tunable Definitions                                                                                         #
#######################################################################################################################

class TunablePieMenuPriorityMapping(TunableMapping):
    def __init__(self, *args, **kwargs):
        kwargs['key_type'] = WorldType.to_enum_entry()
        kwargs['key_name'] = 'world_type'
        kwargs['value_type'] = TunableRange(tunable_type=int, default=0, maximum=10, minimum=0)
        kwargs['value_name'] = 'pie_menu_priority'

        super().__init__(*args, **kwargs)


#######################################################################################################################
# Mixins                                                                                                             #
#######################################################################################################################

class DisplayNotificationMixin:
    INSTANCE_TUNABLES = {
        'interaction_type': InteractionType.to_enum_entry(default='COMMAND'),
        'notification': OptionalTunable(tunable=TunableNotificationSnippet()),
    }

    @staticmethod
    def _should_show_notification(notification_type):
        if notification_type is NotificationType.NOTIFICATION_SETTINGS:
            return True

        from kuttoe_home_regions.settings import Settings
        return Settings.should_show_notification[notification_type]

    @property
    def _notification(self):
        if hasattr(self, 'include_default_world'):
            return self.include_default_world.notification
        return self.notification

    @property
    def has_notification(self): return self._notification is not None

    @property
    def dialog(self): return getattr(self._notification, 'value', None)

    def display_notification(self, notification_type=NotificationType.SUCCESS, **extra_data):
        if not self.has_notification or not self._should_show_notification(notification_type):
            return

        dialog = self.dialog(self, self.interaction_type, **extra_data).dialog
        dialog.show_dialog()


class HomeWorldSortOrderMixin:
    INSTANCE_TUNABLES = {'bump_up_current_region': Tunable(tunable_type=bool, default=False)}
    REMOVE_INSTANCE_TUNABLES = ('pie_menu_priority', )
    REGION_PRIORITY = TunablePieMenuPriorityMapping()
    CURRENT_REGION_BUMP_UP_PRIORITY = TunableRange(tunable_type=int, default=8, maximum=10, minimum=0)

    @classproperty
    def has_region_bump_up(cls) -> bool:
        return getattr(cls, 'bump_up_current_region', False)

    @classmethod
    def _sort_worlds(cls, worlds_list, reverse: bool = False):
        """
        Sorts worlds_list by the following criteria:
        - current region FIRST
        - world type ( Base Game, Residential, Vacation, Hidden)
        - region name (alphabetical)
        """

        current_region = services.current_region()

        def key(world: HomeWorldIds):
            if cls.has_region_bump_up and current_region is world.region:
                return 0, 0, 0
            return 1, int(world.world_type), str(world.name)

        return sorted(worlds_list, key=key, reverse=reverse)

    @flexmethod
    def _get_allowed_worlds(cls, inst, resolver):
        inst_or_cls = inst if inst is not None else cls
        worlds = inst_or_cls.allowed_worlds.get_worlds(resolver)

        return inst_or_cls._sort_worlds(worlds)

    @classmethod
    def get_region_priority(cls, home_world: HomeWorldIds):
        return cls.REGION_PRIORITY.get(home_world.world_type, 0)


class HasHomeWorldMixin:
    ALREADY_RESIDENT_TOOLTIP = TunableLocalizedStringFactory()

    @classmethod
    def get_home_region_test(cls, home_world: HomeWorldIds, participant=DEFAULT, tooltip=DEFAULT, negate: bool = True):
        from world.world_tests import HomeRegionTest

        args = dict()
        args['negate'] = negate
        args['participant'] = ParticipantType.TargetSim if participant is DEFAULT else participant
        args['region'] = home_world.region
        args['tooltip'] = cls.ALREADY_RESIDENT_TOOLTIP if tooltip is DEFAULT else tooltip

        return construct_auto_init_factory(HomeRegionTest, **args)


#######################################################################################################################
# Module Exports                                                                                                     #
#######################################################################################################################

__all__ = ('HasHomeWorldMixin', 'DisplayNotificationMixin', 'HomeWorldSortOrderMixin',)
