import json
import pytest

import mozci.mozci
import mozci.sources

MOCK_JSON = '''{
                "real-repo": {
                    "repo": "https://hg.mozilla.org/integration/real-repo",
                    "graph_branches": ["Real-Repo"],
                    "repo_type": "hg"}}'''


class TestQueries:
    '''This class tests the functions query_repo_url and query_repository'''
    def setup_class(cls):
        '''Replacing query_repositories with a mock function'''
        def mock_query_repositories(clobber=True):
            return json.loads(MOCK_JSON)

        mozci.sources.buildapi.query_repositories = mock_query_repositories

    def test_query_repo_url_valid(self):
        '''A repository in the JSON file must return the corresponding url'''
        assert mozci.mozci.query_repo_url('real-repo') == \
            "https://hg.mozilla.org/integration/real-repo"

    def test_query_repo_url_invalid(self):
        '''A repository not in the JSON file must trigger an exception'''
        with pytest.raises(Exception):
            mozci.mozci.query_repo_url('not-a-repo')

    def test_query_repository_valid(self):
        '''A repository in the JSON file return the corresponding dict'''
        assert mozci.mozci.query_repository('real-repo') == json.loads(MOCK_JSON)['real-repo']

    def test_query_repository_invalid(self):
        '''A repository not in the JSON file must trigger an exception'''
        with pytest.raises(Exception):
            mozci.mozci.query_repository('not-a-repo')
