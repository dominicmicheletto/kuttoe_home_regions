import services
from sims4.resources import Types
from sims4.utils import classproperty
from event_testing.test_variants import TunableTestBasedScoreTestVariant
from event_testing.test_based_score import TestBasedScore
from event_testing.tests import TunableTestVariant
from sims4.tuning.instances import HashedTunedInstanceMetaclass
from sims4.tuning.tunable import HasTunableReference, TunableTuple, Tunable, TunableList, TunableSet, TunableMapping, TunableVariant, HasTunableSingletonFactory, AutoFactoryInit

from typing import Iterable

import sims4.log
logger = sims4.log.Logger('Test Based Score')


"""
example XML:


<I c="TestBasedScoreInjector"> <!-- n, s, m depend on what you want to name it and how you put the files into the script -->
  <L n="injections">
    <U>
      <V n="test_selector" t="single">
        <U n="single">
          <T n="test">12345</T>
        </U>
      </V>
      <U n="injections">
        <L n="scores">
        </L>
        <L n="batch_test_scores">
        </L>
      </U>
    </U>
    <U>
      <V n="test_selector" t="multiple">
        <U n="multiple">
          <L n="test_list">
            <T>12345</T>
            <T>67890</T>
          </L>
        </U>
      </V>
      <U n="injections">
        <L n="scores">
        </L>
        <L n="batch_test_scores">
        </L>
      </U>
    </U>
  </L>
</I>
"""



class TestBasedScoreSelector(TunableVariant):
    class _SelectorBase(HasTunableSingletonFactory, AutoFactoryInit):
        def get_all(self) -> Iterable[TestBasedScore]:
            pass
        
        @staticmethod
        def inject_and_update(cls, score_data, batch_scores):
            cls._scores += score_data
            cls._batch_test_scores += batch_scores
            
            cls._tuning_loaded_callback()
        
        def get_all_filtered(self) -> Iterable[TestBasedScore]:
            return (test for test in self.get_all() if test is not None)
        
        def apply_injections_to_all(self, score_data, batch_scores):
            for test in self.get_all_filtered():
                self.inject_and_update(test, score_data, batch_scores)
        
    class _SingleTestSelector(_SelectorBase):
        FACTORY_TUNABLES = dict(test=TestBasedScore.TunablePackSafeReference())
        
        def get_all(self):
            return (self.test, )
    
    class _MultipleTestsSelector(_SelectorBase):
        FACTORY_TUNABLES = dict(test_list=TunableSet(TestBasedScore.TunablePackSafeReference()))
        
        def get_all(self):
            return self.test_list
    
    def __init__(self, *args, **kwargs):
        kwargs['single'] = self._SingleTestSelector.TunableFactory()
        kwargs['multiple'] = self._MultipleTestsSelector.TunableFactory()
        
        super().__init__(*args, **kwargs)


class ScoreTuple(TunableTuple):
    def __init__(self, *args, **kwargs):
        kwargs['test'] = TunableTestVariant()
        kwargs['score'] = Tunable(tunable_type=float, default=1)
        
        super().__init__(*args, **kwargs)


class BatchTestTuple(TunableTuple):
    def __init__(self, *args, **kwargs):
        kwargs['test'] = TunableTestBasedScoreTestVariant()
        
        super().__init__(*args, **kwargs)


class TestBasedScoreInjectionTuple(TunableTuple):
    def __init__(self, *args, **kwargs):
        kwargs['scores'] = TunableList(tunable=ScoreTuple())
        kwargs['batch_test_scores'] = TunableList(tunable=BatchTestTuple())
        
        super().__init__(*args, **kwargs)


class TestBasedScoreInjectionMapping(TunableMapping):
    def __init__(self, *args, **kwargs):
        kwargs['key_name'] = 'test_selector'
        kwargs['key_type'] = TestBasedScoreSelector()
        kwargs['value_name'] = 'injections'
        kwargs['value_type'] = TestBasedScoreInjectionTuple()
        
        super().__init__(*args, **kwargs)


class TestBasedScoreInjector(
    HasTunableReference,
    metaclass=HashedTunedInstanceMetaclass,
    manager=services.get_instance_manager(Types.SNIPPET)
):
    
    INSTANCE_TUNABLES = dict(injections=TestBasedScoreInjectionMapping())
    
    @classmethod
    def _verify_tuning_callback(cls):
        for score in cls._scores:
            if score.test is None:
                logger.error('Invalid tuning. Test in test based score ({}) is tuned to None. Please set a valid test!', cls, owner='rfleig')
    
    @classmethod
    def _tuning_loaded_callback(cls) -> None:
        for (test_selector, injections) in cls.injections.items():
            scores, batch_scores = injections.scores, injections.batch_test_scores
            
            test_selector.apply_injections_to_all(scores, batch_scores)
