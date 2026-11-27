import fnmatch
import importlib
import json
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


BACKEND = Path(__file__).resolve().parents[1] / "backend" / "api-geolocation-mock"
ENVIRONMENT = {
    "MY_AWS_REGION": "test",
    "OS_ENDPOINT": "test",
    "OS_SECRET_ID": "test",
    "INDEX_NAME": "locations",
    "ADDRESS_RANGE_INDEX": "addresses",
    "ANALYTICS_TABLE_NAME": "analytics",
}


def matches(clause, document):
    if "bool" in clause:
        query = clause["bool"]
        must = query.get("must", [])
        should = query.get("should", [])
        minimum = query.get("minimum_should_match", 0 if must else 1)
        return all(matches(item, document) for item in must) and sum(
            matches(item, document) for item in should
        ) >= minimum
    if "term" in clause:
        field, value = next(iter(clause["term"].items()))
        return document[field] == (value["value"] if isinstance(value, dict) else value)
    if "wildcard" in clause:
        value = clause["wildcard"]["title.keyword"]["value"]
        return fnmatch.fnmatchcase(document["title"].lower(), value.lower())
    if "multi_match" in clause:
        value = clause["multi_match"]["query"].lower()
        return value in document["title"].lower()
    raise AssertionError(f"Unexpected query clause: {clause}")


class GeolocationSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        boto3 = types.ModuleType("boto3")
        boto3.Session = MagicMock()
        auth = types.ModuleType("requests_aws4auth")
        auth.AWS4Auth = MagicMock()
        opensearch = types.ModuleType("opensearchpy")
        opensearch.OpenSearch = MagicMock()
        opensearch.RequestsHttpConnection = MagicMock()
        requests = types.ModuleType("requests")
        old_cwd = os.getcwd()
        try:
            os.chdir(BACKEND)
            sys.path.insert(0, str(BACKEND))
            with patch.dict(sys.modules, {
                "boto3": boto3,
                "requests": requests,
                "requests_aws4auth": auth,
                "opensearchpy": opensearch,
            }):
                cls.module = importlib.import_module("lambda_function")
        finally:
            sys.path.remove(str(BACKEND))
            os.chdir(old_cwd)

    def search(self, q):
        documents = [
            {"title": "Ottawa, Ontario (City)", "type": "ca.gc.nrcan.geoloc.data.model.Geoname"},
            {"title": "Ottawa Street, Ontario", "type": "ca.gc.nrcan.geoloc.data.model.Street"},
            {"title": "Ottawa Street & Main Street", "type": "ca.gc.nrcan.geoloc.data.model.Intersection"},
            {"title": "Ottawa Postal Code", "type": "ca.gc.nrcan.geoloc.data.model.PostalCode"},
        ]
        client = MagicMock()

        def search(index, body):
            bool_query = body["query"]["function_score"]["query"]
            return {"hits": {"hits": [
                {"_source": document} for document in documents if matches(bool_query, document)
            ]}}

        client.search.side_effect = search
        module = self.module
        with patch.dict(os.environ, ENVIRONMENT), \
             patch.object(module, "OpenSearch", return_value=client), \
             patch.object(module, "create_opensearch_index"), \
             patch.object(module, "ip2geo_handler", return_value={}), \
             patch.object(module, "save_to_opensearch"), \
             patch("builtins.print"):
            result = module.lambda_handler({"path": "/en/locate", "q": q}, None)
        self.assertEqual(result["statusCode"], 200, result)
        return json.loads(result["body"]), client.search.call_args.kwargs["body"]

    def test_unmatched_text_and_wildcard_do_not_match_feature_types(self):
        for q in ("ShouldNotReturnStuff", "ShouldNotReturnStuff*"):
            with self.subTest(q=q):
                results, _ = self.search(q)
                self.assertEqual(results, [])

    def test_matching_text_and_wildcard_keep_all_feature_types(self):
        for q in ("Ottawa", "Ottawa*"):
            with self.subTest(q=q):
                results, query = self.search(q)
                self.assertEqual(len(results), 4)
                scoring = query["query"]["function_score"]
                self.assertEqual(len(scoring["query"]["bool"]["should"]), 3)
                self.assertEqual(scoring["score_mode"], "sum")
                self.assertEqual(scoring["boost_mode"], "multiply")


if __name__ == "__main__":
    unittest.main()
