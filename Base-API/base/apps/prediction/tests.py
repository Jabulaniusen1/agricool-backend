from django.test import TestCase

# Create your tests here.


class Test(TestCase):
    def test(self):
        self.assertEqual(1, 1)


class StateViewSetTest(TestCase):
    def setUp(self):
        pass

    def tests(self):
        """
        should return expected - proper & empty

        prep :
            dump into markets,
                    states,
                    crop,
                    Market,
                    MLPredictionData

        setup user - any type would work

        expect empty for strange country user
                expect db data for know country
        """

    def test_get_parameters_for_prediction(self):
        """ """
        return


class PredictionsDataGraphAPIViewTest(TestCase):

    def setUp(self):
        pass

    def tests(self):
        pass


class PredictionsDataTableAPIViewTest(TestCase):

    def setUp(self):
        pass

    def tests(self):
        pass
