"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details a special object which is used for defining the PickerItem used for the toggle pickers. This simply
ensures that the desired locked arguments are locked and that the desired Picker factory is used as well.
"""


#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

from sims4.utils import staticproperty
from ui.ui_dialog_picker import UiItemPicker, UiDialogObjectPicker
from kuttoe_home_regions.utils import construct_auto_init_factory


#######################################################################################################################
# Factory Tunables                                                                                                    #
#######################################################################################################################

class ToggleItemPicker:
    @staticproperty
    def tunable_factory(): return UiItemPicker.TunableFactory

    @staticmethod
    def get_static_selectable(count: int = 1):
        return construct_auto_init_factory(UiDialogObjectPicker._MaxSelectableStatic, number_selectable=count)

    def __call__(self, **locked_args):
        locked_args.update(max_selectable=self.get_static_selectable())
        return self.tunable_factory(locked_args=locked_args)


#######################################################################################################################
# Module Exports                                                                                                      #
#######################################################################################################################

__all__ = ('ToggleItemPicker', )
