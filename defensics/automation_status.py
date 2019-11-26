import json


class AutomationStatus:
    def __init__(self):
        self.status = 0
        self.errors = []
        self.verdict = ''

    def to_json(self):
        return json.dumps({
            'status': self.status,
            'errors': self.errors,
            'verdict': self.verdict,
        })


