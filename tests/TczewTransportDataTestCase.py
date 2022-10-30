from unittest import TestCase

from data.TczewTransportData import TczewTransportData


class TczewTransportDataTestCase(TestCase):
    def setUp(self):
        self.tczewTransportData = TczewTransportData()

    def test_parseTime(self):
        for (example, expected) in [
            ("000", 0),
            ("324", 204),
            ("712", 432),
        ]:
            self.assertEqual(self.tczewTransportData.parseFirstMinutes(example), expected)
