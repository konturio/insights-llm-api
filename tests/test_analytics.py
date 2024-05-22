import unittest

from app.insights_api_client import to_readable_sentence, unit_to_str


class TestAnalytics(unittest.TestCase):

    def test_to_readable_sentence(self):
        world_data = {
            ('mean', 'pop_without_car', 'population'): {
                'numerator': 'pop_without_car',
                 'denominator': 'population',
                 'numeratorLabel': 'Population without a car',
                 'denominatorLabel': 'Population',
                 'calculation': 'mean',
                 'value': 0.009002802597977946,
                 'quality': 0.33564222905226,
                 'emoji': '🚗',
                 'numeratorUnit': 'ppl',
                 'denominatorUnit': 'ppl',
            }
        }
        selected_area_data = [{
            'numerator': 'pop_without_car',
            'denominator': 'population',
            'numeratorLabel': 'Population without a car',
            'denominatorLabel': 'Population',
            'calculation': 'mean',
            'value': 0.3175384925724989,
            'quality': 0.7798245940871434,
            'emoji': '🚗',
            'numeratorUnit': 'ppl',
            'denominatorUnit': 'ppl',
            'world_sigma': 4.3034507224487655,
            'reference_area_sigma': 0,
        }]

        expected = 'mean of 🚗 Population without a car over Population is 0.32 (globally 0.01, 4.30 sigma)'
        actual = to_readable_sentence(selected_area_data, world_data)[0]
        self.assertEqual(expected, actual)

    def test_to_readable_unixtime(self):
        world_data = {
            ('mean', 'max_ts', 'one'): {
                'numerator': 'max_ts',
                'denominator': 'one',
                'numeratorLabel': 'OSM last edit',
                'denominatorLabel': '1',
                'calculation': 'mean',
                'value': 1600113065.1491652,
                'quality': 0.02838493267083375,
                'emoji': '🐱',
                'numeratorUnit': 'unixtime',
                'denominatorUnit': None
            }
        }
        selected_area_data = [{
            'numerator': 'max_ts',
            'denominator': 'one',
            'numeratorLabel': 'OSM last edit',
            'denominatorLabel': '1',
            'calculation': 'mean',
            'value': 1714021374.125,
            'quality': 0.0002680225867511481,
            'emoji': '🐱',
            'numeratorUnit': 'unixtime',
            'denominatorUnit': None,
            'world_sigma': 1.0016197183988316,
            'reference_area_sigma': 0,
        }]

        expected = 'mean of 🐱 OSM last edit is 2024-04-25T09:02:54 (globally 2020-09-14T23:51:05, 1.00 sigma)'
        actual = to_readable_sentence(selected_area_data, world_data)[0]
        self.assertEqual(expected, actual)

    def test_unixtime_stddev(self):
        world_data = {
            ('stddev', 'max_ts', 'one'): {
                'numerator': 'max_ts',
                'denominator': 'one',
                'numeratorLabel': 'OSM last edit',
                'denominatorLabel': '1',
                'calculation': 'mean',
                'value': 113065.1491652,
                'quality': 0.02838493267083375,
                'emoji': None,
                'numeratorUnit': 'unixtime',
                'denominatorUnit': None
            }
        }
        selected_area_data = [{
            'numerator': 'max_ts',
            'denominator': 'one',
            'numeratorLabel': 'OSM last edit',
            'denominatorLabel': '1',
            'calculation': 'stddev',
            'value': 21374.125,
            'quality': 0.0002680225867511481,
            'emoji': None,
            'numeratorUnit': 'unixtime',
            'denominatorUnit': None,
            'world_sigma': 0,
            'reference_area_sigma': 0,
        }]

        expected = 'stddev of OSM last edit is 5:56:14 (globally 1 day, 7:24:25)'
        actual = to_readable_sentence(selected_area_data, world_data)[0]
        self.assertEqual(expected, actual)

    def test_to_readable_gdp(self):
        world_data = {
            ('max', 'gdp', 'population'): {
                'numerator': 'gdp',
                'denominator': 'population',
                'numeratorLabel': 'Gross Domestic Product',
                'denominatorLabel': 'Population',
                'calculation': 'max',
                'value': 130509.65801594242,
                'quality': 0.2901225640920188,
                'emoji': None,
                'numeratorUnit': 'USD',
                'denominatorUnit': 'ppl',
            }
        }
        selected_area_data = [{
            'numerator': 'gdp',
            'denominator': 'population',
            'numeratorLabel': 'Gross Domestic Product',
            'denominatorLabel': 'Population',
            'calculation': 'max',
            'value': 71535.68400170161,
            'quality': 0.41165680673194294,
            'emoji': None,
            'numeratorUnit': 'USD',
            'denominatorUnit': 'ppl',
            'world_sigma': 0,
            'reference_area_sigma': 0,
        }]

        expected = 'max of Gross Domestic Product over Population is 71,535.68 USD/ppl (globally 130,509.66 USD/ppl)'
        actual = to_readable_sentence(selected_area_data, world_data)[0]
        self.assertEqual(expected, actual)

    def test_reference_area(self):
        world_data = {
            ('mean', 'pop_without_car', 'population'): {
                 'numerator': 'pop_without_car',
                 'denominator': 'population',
                 'numeratorLabel': 'Population without a car',
                 'denominatorLabel': 'Population',
                 'calculation': 'mean',
                 'value': 0.009002802597977946,
                 'quality': 0.33564222905226,
                 'emoji': None,
                 'numeratorUnit': 'ppl',
                 'denominatorUnit': 'ppl',
            }
        }
        reference_area_data = {
            ('mean', 'pop_without_car', 'population'): {
                 'numerator': 'pop_without_car',
                 'denominator': 'population',
                 'numeratorLabel': 'Population without a car',
                 'denominatorLabel': 'Population',
                 'calculation': 'mean',
                 'value': 0.2,
                 'quality': 0.7,
                 'emoji': None,
                 'numeratorUnit': 'ppl',
                 'denominatorUnit': 'ppl',
            }
        }
        selected_area_data = [{
            'numerator': 'pop_without_car',
            'denominator': 'population',
            'numeratorLabel': 'Population without a car',
            'denominatorLabel': 'Population',
            'calculation': 'mean',
            'value': 0.3175384925724989,
            'quality': 0.7798245940871434,
            'emoji': None,
            'numeratorUnit': 'ppl',
            'denominatorUnit': 'ppl',
            'world_sigma': 4.3034507224487655,
            'reference_area_sigma': 2.1,
        }]

        expected = 'mean of Population without a car over Population is 0.32 (reference_area 0.20, 2.10 sigma) (globally 0.01, 4.30 sigma)'
        actual = to_readable_sentence(selected_area_data, world_data, reference_area_data)[0]
        self.assertEqual(expected, actual)

    def test_unit_to_str(self):
        # Population without a car over Population
        entry = {
            'numeratorUnit': 'ppl',
            'denominatorUnit': 'ppl',
        }
        s = unit_to_str(entry)
        self.assertEqual(s, '')

        # OSM: waste containers count over Populated area
        entry = {
            'numeratorUnit': 'n',
            'denominatorUnit': 'km2',
        }
        s = unit_to_str(entry)
        self.assertEqual(s, ' n/km2')

        s = unit_to_str(entry, sigma=True)
        self.assertEqual(s, '')

        # Air temperature
        entry = {
            'numeratorUnit': 'celc_deg',
            'denominatorUnit': '1',
        }
        s = unit_to_str(entry)
        self.assertEqual(s, ' celc_deg')

        # Man-days above 32°C, (+1°C scenario) over area km2
        entry = {
            'numeratorUnit': 'other',
            'denominatorUnit': 'km2',
        }
        s = unit_to_str(entry)
        self.assertEqual(s, '')


if __name__ == '__main__':
    unittest.main()
