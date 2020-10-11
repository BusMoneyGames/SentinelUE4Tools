from teamcity.unittestpy import TeamcityTestRunner
import unittest


class GeneralTestCase(unittest.TestCase):
    def __init__(self, methodName, param1=None, param2=None):
        super(GeneralTestCase, self).__init__(methodName)

        self.param1 = param1
        self.param2 = param2

    def runTest(self):
        pass  # Test that depends on param 1 and 2.


def load_tests(loader, tests, pattern):
    test_cases = unittest.TestSuite()
    for p1, p2 in [(1, 2), (3, 4),(1, 2), (3, 4),(1, 2), (3, 4),(1, 2), (3, 4)]:
        test_cases.addTest(GeneralTestCase('runTest', p1, p2))
    return test_cases

if __name__ == '__main__':
    unittest.main(testRunner=TeamcityTestRunner())