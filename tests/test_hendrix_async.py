from unittest import skipUnless

from rest_framework.test import APITestCase

from hendrix.utils.test_utils import AsyncTestMixin
from the_comm_app.plumbing import PhoneLine
from the_comm_app.voice.voice_features import Feature


try:
    from hendrix.experience import crosstown_traffic
    HENDRIX_INSTALLED = True
except ImportError:
    HENDRIX_INSTALLED = False


@skipUnless(HENDRIX_INSTALLED, "Skipping because hendrix is not installed.")
class SideEffectOccursAsync(AsyncTestMixin, APITestCase):

    class AsyncPhoneLine(PhoneLine):
        pass

    def test_long_side_effect_was_started(self):
        class SomeFeature(Feature):
            pass

        phone_line = self.AsyncPhoneLine()
        phone_line.runner = crosstown_traffic.follow_response()
        feature = phone_line.add_feature(SomeFeature)

        # The feature hasn't yet started.
        self.assertFalse(feature.has_started)
        self.assertFalse(feature.is_finished)

        feature() # Once we call it, it has started by not finished.
        self.assertTrue(feature.has_started)
        self.assertFalse(feature.is_finished)

        # But after running the crosstown_traffic, is is finished.
        task = self.next_task()
        task()
        self.assertTrue(feature.has_started)
        self.assertTrue(feature.is_finished)

    def test_long_side_effect_was_added_to_crosstown_traffic(self):
        class LongFeature(Feature):
            pass

        phone_line = self.AsyncPhoneLine()
        phone_line.runner = crosstown_traffic.follow_response()
        long_feature = phone_line.add_feature(LongFeature)

        self.assertNumCrosstownTasks(0)

        # The feature hasn't yet been integrated.
        self.assertRaises(StopIteration, self.next_task)

        phone_line.integrate_features()

        # Now it's been added to crosstown_traffic.
        task = self.next_task()
        self.assertEqual(long_feature.run, task)
        self.assertNumCrosstownTasks(1)

