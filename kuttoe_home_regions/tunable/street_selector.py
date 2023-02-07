"""
For Home Regions mod by Kuttoe & LeRoiDeTout
https://kuttoe.itch.io/keep-sims-in-home-region#download

This file details the tunable structures for a "world selector". This allows for Home Worlds to list either one
specific creation street or have a weighted list of them. This allows for some control over which streets a
Sim created by the game via the Home Region filters is assigned.
"""


#######################################################################################################################
# Imports                                                                                                             #
#######################################################################################################################

# sims4 imports
from sims4.tuning.tunable import TunableVariant, HasTunableSingletonFactory, AutoFactoryInit, Tunable, TunableMapping
from sims4.random import pop_weighted

# local imports
from kuttoe_home_regions.enum.neighbourhood_streets import NeighbourhoodStreets


#######################################################################################################################
# Tuning Definitions                                                                                                  #
#######################################################################################################################

class TunableStreetsListMapping(TunableMapping):
    def __init__(self, *args, **kwargs):
        kwargs['key_type'] = NeighbourhoodStreets.create_enum_entry()
        kwargs['key_name'] = 'street'
        kwargs['value_type'] = Tunable(tunable_type=float, default=1.0)
        kwargs['value_name'] = 'weight'

        super().__init__(*args, **kwargs)


#######################################################################################################################
# Factory Definitions                                                                                                 #
#######################################################################################################################

class TunableStreetSelectorVariant(TunableVariant):
    class _StreetSelectorBase(HasTunableSingletonFactory, AutoFactoryInit):
        @classmethod
        def get_street_from_id(cls, street_id: int):
            return NeighbourhoodStreets[NeighbourhoodStreets.value_to_name[street_id]]

        @property
        def supports_multiple_streets(self): return False

        @property
        def streets(self):
            return frozenset(self.get_street_from_id(street_id) for street_id in self.street_ids)

        def get_default_weight(self, street):
            return self[street]

    class _SpecificStreetSelector(_StreetSelectorBase):
        FACTORY_TUNABLES = {
            'street': NeighbourhoodStreets.create_enum_entry()
        }

        @property
        def street_ids(self):
            return frozenset({self.street.value, })

        def __contains__(self, street):
            return street is self.street or street in self.street_ids

        def __getitem__(self, street):
            return 1.0 if street in self else 0.0

        def __iter__(self):
            yield from ((self.street, 1.0), )

        def __call__(self):
            return self.street

    class _WeightedStreetListSelector(_StreetSelectorBase):
        FACTORY_TUNABLES = {
            'streets_list': TunableStreetsListMapping()
        }

        @property
        def supports_multiple_streets(self): return True

        @property
        def street_weights(self):
            from kuttoe_home_regions.settings import Settings

            return Settings.street_weights

        @property
        def street_ids(self):
            return frozenset(street.value for street in self.streets_list)

        def get_default_weight(self, street):
            if type(street) in (str, int):
                street = self.get_street_from_id(int(street))

            return self.streets_list.get(street)

        def __contains__(self, street):
            return street in self.streets_list or street in self.street_ids

        def __getitem__(self, street):
            if type(street) in (str, int):
                street = self.get_street_from_id(int(street))

            if street.dict_key in self.street_weights:
                return self.street_weights[street.dict_key]

            return self.streets_list.get(street)

        def __iter__(self):
            yield from ((street, self[street]) for street in self.streets_list)

        def __call__(self):
            return pop_weighted(list(self), flipped=True)

    def __init__(self, *args, **kwargs):
        factories = {'specify': self._SpecificStreetSelector, 'streets_list': self._WeightedStreetListSelector}
        kwargs.update({key: factory.TunableFactory() for (key, factory) in factories.items()})
        kwargs['default'] = 'streets_list'

        super().__init__(*args, **kwargs)


#######################################################################################################################
# Module Exports                                                                                                      #
#######################################################################################################################

__all__ = ('TunableStreetSelectorVariant', )
