import unittest


# Business Logic
def add(a: int, b: int) -> int:
    return a + b


# Tests
class TestAddFunction(unittest.TestCase):
    def test_add_positive(self):
        a, b = 10, 10
        expected_result = 20

        result = add(a, b)

        self.assertEqual(result, expected_result)

    def test_add_negative(self):
        a, b = -1, -1
        expected_result = -2

        result = add(a, b)

        assert result == expected_result


if __name__ == "__main__":
    unittest.main()
