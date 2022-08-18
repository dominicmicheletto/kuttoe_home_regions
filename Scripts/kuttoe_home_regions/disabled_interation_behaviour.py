#######################################################################################################################
#  Imports                                                                                                            #
#######################################################################################################################

from snippets import define_snippet
from sims4.tuning.tunable import AutoFactoryInit, OptionalTunable, Tunable, TunableMapping, HasTunableSingletonFactory
from sims4.localization import TunableLocalizedStringFactory


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


class DisabledInteractionBehaviour(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {
        'base': TunableLocalizedStringFactory(),
        'tooltip_reason_mapping': TooltipReasonMapping(),
    }
    TOOLTIP_REPR_PROPERTY = '__tooltip_repr__'

    @classmethod
    def get_tooltip_from_token(cls, token):
        return getattr(token, cls.TOOLTIP_REPR_PROPERTY, token)

    def get_tooltip_reason(self, toggle_value: bool):
        tooltip_reason = self.tooltip_reason_mapping.get(toggle_value)

        return tooltip_reason() if tooltip_reason else None

    def get_disabled_tooltip(self, toggle_value: bool, *additional_tokens):
        base = self.base
        tooltip_reason = self.get_tooltip_reason(toggle_value)
        tooltip_tokens = (self.get_tooltip_from_token(token) for token in additional_tokens)

        if not base:
            return None
        return lambda *tokens: base(*tooltip_tokens, tooltip_reason, *tokens)

    @staticmethod
    def create_picker(inst, tests, toggle_value: bool, *additional_tokens, **args):
        value = getattr(inst, 'value', inst)

        if value:
            args['enable_tests'] = tests
            args['disable_tooltip'] = value.get_disabled_tooltip(toggle_value, *additional_tokens)
            args['visibility_tests'] = None
        else:
            args['enable_tests'] = None
            args['disable_tooltip'] = None
            args['visibility_tests'] = tests

        return args


(_, DisabledInteractionBehaviourSnippet) = define_snippet('disabled_interaction_behaviour',
                                                          DisabledInteractionBehaviour.TunableFactory())


class TunableDisabledInteractionBehaviourSnippet(OptionalTunable):
    def __init__(self, *args, **kwargs):
        kwargs['disabled_name'] = 'do_not_show'
        kwargs['enabled_name'] = 'show_interactions'
        kwargs['tunable'] = DisabledInteractionBehaviourSnippet()
        super().__init__(*args, **kwargs)

