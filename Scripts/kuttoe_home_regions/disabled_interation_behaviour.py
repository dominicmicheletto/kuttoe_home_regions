#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

from snippets import define_snippet
from sims4.tuning.tunable import AutoFactoryInit, OptionalTunable, Tunable, TunableMapping, HasTunableFactory
from sims4.localization import TunableLocalizedStringFactory
from event_testing.tests import CompoundTestList


#######################################################################################################################
#  Tunables                                                                                                           #
#######################################################################################################################


class TooltipReasonMapping(TunableMapping):
    def __init__(self, *args, **kwargs):
        kwargs['key_name'] = 'toggle_value'
        kwargs['key_type'] = Tunable(tunable_type=bool, default=False)
        kwargs['value_name'] = 'display_text'
        kwargs['value_type'] = TunableLocalizedStringFactory()

        super().__init__(*args, **kwargs)


class DisabledInteractionBehaviour(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {
        'base': TunableLocalizedStringFactory(),
        'tooltip_reason_mapping': TooltipReasonMapping(),
    }

    @staticmethod
    def get_tooltip_reason(inst, toggle_value: bool):
        tooltip_reason = inst.tooltip_reason_mapping.get(toggle_value)

        return tooltip_reason() if tooltip_reason else None

    def __init__(self, toggle_value: bool, tests: CompoundTestList, additional_tokens=tuple(), *args, **kwargs):
        self._toggle_value = toggle_value
        self._tests = tests
        self._additional_tokens = additional_tokens

        super().__init__(*args, **kwargs)

    @property
    def toggle_value(self):
        return self._toggle_value

    @property
    def tests(self):
        return self._tests

    @property
    def additional_tokens(self):
        return self._additional_tokens

    @property
    def tooltip_reason(self):
        return self.get_tooltip_reason(self, self.toggle_value)

    def __bool__(self):
        return self.base is not None

    def __call__(self):
        args = dict()
        args['enable_tests'] = self.tests
        args['disable_tooltip'] = self.get_disabled_tooltip()

        return args

    def __iter__(self):
        yield from iter(self().items())

    def get_disabled_tooltip(self):
        if not self:
            return None
        return lambda *tokens: self.base(*self.additional_tokens, self.tooltip_reason, *tokens)


(_, DisabledInteractionBehaviourSnippet) = define_snippet('disabled_interaction_behaviour',
                                                          DisabledInteractionBehaviour.TunableFactory())


class TunableDisabledInteractionBehaviourSnippet(OptionalTunable):
    def __init__(self, *args, **kwargs):
        kwargs['disabled_name'] = 'do_not_show'
        kwargs['enabled_name'] = 'show_interactions'
        kwargs['tunable'] = DisabledInteractionBehaviourSnippet()
        super().__init__(*args, **kwargs)

