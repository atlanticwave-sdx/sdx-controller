import json


class ParseHelper:
    def __init__(self):
        pass

    def is_json(self, json_str):
        try:
            json.loads(json_str)
        except ValueError as e:
            return False
        return True

    def find_between(self, s, first, last):
        try:
            start = s.index(first) + len(first)
            end = s.index(last, start)
            return s[start:end]
        except ValueError:
            return ""
