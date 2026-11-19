import unittest

import app as app_module


class FakeCollection:
    def __init__(self):
        self.documents = []

    def insert_one(self, document):
        self.documents.append(dict(document))

    def find(self, _query, _projection):
        return [dict(document) for document in self.documents]


class FlaskAppTest(unittest.TestCase):
    def setUp(self):
        self.original_collection = app_module.collection
        app_module.collection = FakeCollection()
        app_module.app.config["TESTING"] = True
        self.client = app_module.app.test_client()

    def tearDown(self):
        app_module.collection = self.original_collection

    def test_index(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Welcome to the Flask app!", response.data)

    def test_post_and_get_data(self):
        response = self.client.post("/data", json={"sampleKey": "sampleValue"})
        self.assertEqual(response.status_code, 201)

        response = self.client.get("/data")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [{"sampleKey": "sampleValue"}])

    def test_post_requires_json_object(self):
        response = self.client.post("/data", data="text", content_type="text/plain")
        self.assertEqual(response.status_code, 400)

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
