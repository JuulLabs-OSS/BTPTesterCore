class ResponseHandler:
    def __init__(self):
        self.status = 200
        self.contentType = "application/json"
        self.contents = "{}"

    def get_contents(self):
        return self.contents

    def read(self):
        return self.contents

    def set_status(self, status):
        self.status = status

    def get_status(self):
        return self.status

    def get_content_type(self):
        return self.contentType
