import sys
sys.path.append('.')

import unittest
import fizzbuzz

class TestFizzBuzz(unittest.TestCase):
    def test_fizzbuzz_1(self):
        self.assertEqual(fizzbuzz.fizzbuzz(3), 'Fizz')

    def test_fizzbuzz_2(self):
        self.assertEqual(fizzbuzz.fizzbuzz(5), 'Buzz')

    def test_fizzbuzz_3(self):
        self.assertEqual(fizzbuzz.fizzbuzz(15), 'FizzBuzz')

    def test_fizzbuzz_4(self):
        self.assertEqual(fizzbuzz.fizzbuzz(7), '7')