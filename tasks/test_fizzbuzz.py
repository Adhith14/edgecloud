def test_fizzbuzz():
    assert fizzbuzz(3) == 'Fizz', 'Failed on multiple of 3'
    assert fizzbuzz(5) == 'Buzz', 'Failed on multiple of 5'
    assert fizzbuzz(15) == 'FizzBuzz', 'Failed on multiple of both 3 and 5'
    assert fizzbuzz(7) == '7', 'Failed on non-multiple'

if __name__ == '__main__':
    test_fizzbuzz()