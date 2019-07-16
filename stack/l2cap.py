class L2CAP:
    def __init__(self):
        self.channels = []
        self.verify_values = []

    def add_verify_values(self, val):
        self.verify_values.append(val)

    def clear_verify_values(self):
        self.verify_values.clear()

