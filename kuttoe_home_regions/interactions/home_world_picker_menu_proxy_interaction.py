"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details the base class for all _PickerMenuProxyInteraction subclasses that depend on a HomeWorldIds value.
This class provides the HomeWorldId that it represents, allows for pie menu priority, and forwards the icon to the
interaction.
"""


#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

# sims 4 imports
from sims4.utils import classproperty, flexmethod

# miscellaneous imports
from singletons import DEFAULT
from services import current_region as get_current_region

# interaction imports
from interactions.picker.picker_pie_menu_interaction import _PickerPieMenuProxyInteraction
from interactions.base.super_interaction import SuperInteraction


#######################################################################################################################
#  Proxy Interaction                                                                                                  #
#######################################################################################################################

class _HomeWorldPickerMenuProxyInteraction(_PickerPieMenuProxyInteraction):
    @classproperty
    def home_world(cls): return cls.picker_row_data.tag

    @classproperty
    def home_world_name(cls): return cls.home_world.region_name()

    @classproperty
    def pie_menu_priority(cls):
        priority = getattr(super(SuperInteraction), 'pie_menu_priority', 0)
        current_region = get_current_region()
        home_region = cls.home_world

        if home_region is None:
            return priority
        elif home_region in cls.REGION_PRIORITY:
            return cls.get_region_priority(home_region).pie_menu_priority
        elif cls.has_region_bump_up and current_region is home_region.region:
            return cls.CURRENT_REGION_BUMP_UP_PRIORITY
        else:
            return priority

    @flexmethod
    def get_pie_menu_icon_info(cls, inst, target=DEFAULT, context=DEFAULT, **interaction_parameters):
        inst_or_cls = inst if inst is not None else cls
        super_value = super(__class__, inst_or_cls).get_pie_menu_icon_info(target=target, context=context, **interaction_parameters)

        if inst_or_cls.picker_row_data is None:
            return super_value

        return inst_or_cls.picker_row_data.icon_info


#######################################################################################################################
#  Module Exports                                                                                                     #
#######################################################################################################################

__all__ = ('_HomeWorldPickerMenuProxyInteraction', )
