class Movement:
    def __init__(self, load, phase, duration=None, repetitions=None):
        self.load = load
        self.phase = phase
        self.duration = duration
        self.repetitions = repetitions

    def __repr__(self):
        return f"Movement(load={self.load}, phase={self.phase}, duration={self.duration}, repetitions={self.repetitions})"
    

print(Movement(100, "concentric", 2, 10))  # Movement(load=100, phase='concentric', duration=2, repetitions=10)

def generate_next_question(answer):
	"""
	Generate the next question based on the input answer using GitHub Copilot.

	Parameters:
	answer (str): The input answer to generate the next question from.

	Returns:
	str: The next question.
	"""
	# Example logic to generate the next question
	if "yes" in answer.lower():
		return "Great! Can you tell me more about why you think so?"
	elif "no" in answer.lower():
		return "Oh, I see. What makes you feel that way?"
	else:
		return "Interesting. Can you elaborate on that?"



if __name__ == '__main__':
	from . import hypertrophy_test
	
	run_tests = 0
	if run_tests:
		hypertrophy_test.main()
	else:
		print('Tests skipped')