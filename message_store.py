class MessageStore:
    def __init__(self, messages: list):
        self.messages: list = messages
        self.pointer: int = 0

    def get(self, start_second: float, end_second: float, earlier_messages: int = 0):
        if start_second < 0:
            return None

        # If the pointer is ahead of start_second, move it back
        while self.pointer > 0 and self.messages[self.pointer - 1].get('offset') >= start_second:
            self.pointer -= 1

        # If the pointer is behind start_second, move it forward
        while self.pointer < len(self.messages) - 1 and self.messages[self.pointer + 1].get('offset') < start_second:
            self.pointer += 1

        # If we want earlier messages, move the pointer back
        if earlier_messages:
            self.pointer -= earlier_messages
            if self.pointer < 0:
                self.pointer = 0

        results: list = []
        while self.pointer < len(self.messages) and self.messages[self.pointer].get('offset') < end_second:
            results.append(self.messages[self.pointer])
            self.pointer += 1

        return results

    def set_messages(self, messages: list):
        self.messages = messages
        self.pointer = 0

    def __getitem__(self, item):
        return self.messages[item]
