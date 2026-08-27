def fizzbuzz(n):
    if n % 3 == 0 and n % 5 == 0:
        return 'FizzBuzz'
    elif n % 3 == 0:
        return 'Fizz'
    elif n % 5 == 0:
        return 'Buzz'
    else:
        return str(n)

assert fizzbuzz(3) == 'Fizz', 'Test 1 failed'
assert fizzbuzz(5) == 'Buzz', 'Test 2 failed'
assert fizzbuzz(15) == 'FizzBuzz', 'Test 3 failed'
assert fizzbuzz(7) == '7', 'Test 4 failed'