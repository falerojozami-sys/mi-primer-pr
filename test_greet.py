import unittest

from greet import greet


class TestGreet(unittest.TestCase):
    def test_greet_with_name(self):
        self.assertEqual(greet("world"), "Hello, world!")

    def test_greet_with_different_name(self):
        self.assertEqual(greet("Ana"), "Hello, Ana!")


if __name__ == "__main__":
    unittest.main()
