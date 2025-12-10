class MockOpenAIResponse:
    def __init__(self, text):
        self.text = text

    @property
    def choices(self):
        return [{"message": {"content": self.text}}]


def mock_chatcompletion_create(*args, **kwargs):
    prompt = kwargs["messages"][0]["content"]

    if "Summarize" in prompt:
        return MockOpenAIResponse("Mock summary.")
    if "Answer clearly" in prompt:
        return MockOpenAIResponse("Mock answer: methodology is CNN.")

    return MockOpenAIResponse("Mock generic response.")
