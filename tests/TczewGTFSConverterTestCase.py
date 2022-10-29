from unittest import TestCase

from data.TczewGTFSConverter import TczewGTFSConverter
from data.TczewTransportData import TczewTransportData


class TczewGTFSConverterTestCase(TestCase):
    def setUp(self):
        self.tczewGTFSConverter = TczewGTFSConverter(TczewTransportData())

    def test_parseTime(self):
        for (example, expected) in [
            ("000", (0, 0)),
            ("324", (3, 24)),
            ("772", (8, 12)),
        ]:
            self.assertEquals(self.tczewGTFSConverter.parseTime(example), expected)
