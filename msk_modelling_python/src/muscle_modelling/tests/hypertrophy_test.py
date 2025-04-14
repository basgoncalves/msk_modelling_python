import unittest
from msk_modelling_python.src.muscle_modelling.hypertrophy import Movement, generate_next_question

class TestMovement(unittest.TestCase):
    def test_movement_initialization(self):
        movement = Movement(100, "concentric", 2, 10)
        self.assertEqual(movement.load, 100)
        self.assertEqual(movement.phase, "concentric")
        self.assertEqual(movement.duration, 2)
        self.assertEqual(movement.repetitions, 10)

    def test_movement_repr(self):
        movement = Movement(100, "concentric", 2, 10)
        self.assertEqual(repr(movement), "Movement(load=100, phase=concentric, duration=2, repetitions=10)")

class TestGenerateNextQuestion(unittest.TestCase):
    def test_generate_next_question_yes(self):
        answer = "Yes, I think it's a good idea."
        expected_question = "Great! Can you tell me more about why you think so?"
        self.assertEqual(generate_next_question(answer), expected_question)

    def test_generate_next_question_no(self):
        answer = "No, I don't think it's a good idea."
        expected_question = "Oh, I see. What makes you feel that way?"
        self.assertEqual(generate_next_question(answer), expected_question)

    def test_generate_next_question_other(self):
        answer = "Maybe, I'm not sure."
        expected_question = "Interesting. Can you elaborate on that?"
        self.assertEqual(generate_next_question(answer), expected_question)

if __name__ == '__main__':
    unittest.main()