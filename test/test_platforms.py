"""This file contains tests for mozci/platforms.py."""
import pytest
import time
import unittest

# Third party
from mock import (
    Mock,
    patch
)

# This project
from helpers import (
    ALLTHETHINGS,
    SETA_RESULT,
    GRAPH_RESULT
)
from mozci.errors import MissingBuilderError
from mozci.platforms import (
    MAX_PUSHES,
    _get_job_type,
    _include_builders_matching,
    _wanted_builder,
    build_tests_per_platform_graph,
    build_talos_buildernames_for_repo,
    determine_upstream_builder,
    get_associated_platform_name,
    get_buildername_metadata,
    get_downstream_jobs,
    get_SETA_info,
    get_SETA_interval_dict,
    get_max_pushes,
    filter_buildernames,
    find_buildernames,
    is_downstream,
    list_builders,
    get_talos_jobs_for_build,
    get_builder_extra_properties,
)


class TestIsDownstream(unittest.TestCase):

    """Test is_downstream with mock data."""

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_valid(self, fetch_allthethings_data):
        """is_downstream should return True for test jobs and False for build jobs."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        assert is_downstream('Ubuntu VM 12.04 x64 mozilla-beta debug test mochitest-1') is True
        assert is_downstream('Linux x86-64 mozilla-beta build') is False

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_invalid(self, fetch_allthethings_data):
        fetch_allthethings_data.return_value = ALLTHETHINGS
        with pytest.raises(Exception):
            determine_upstream_builder("Not a valid buildername")


class TestFindBuildernames(unittest.TestCase):

    """Test find_buildernames with mock data."""

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_full(self, fetch_allthethings_data):
        """The function should return a list with the specific buildername."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        obtained = sorted(find_buildernames(
            repo='try',
            suite_name='mochitest-1',
            platform='win32',
            job_type='opt')
        )
        expected = sorted([u'Windows XP 32-bit try opt test mochitest-1',
                           u'Windows 7 VM-GFX 32-bit try opt test mochitest-1',
                           u'Windows 7 32-bit try opt test mochitest-1',
                           u'Windows 7 VM 32-bit try opt test mochitest-1'])
        assert obtained == expected

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_with_debug(self, fetch_allthethings_data):
        """The function should return a list with the specific debug buildername."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        obtained = sorted(find_buildernames('try', 'mochitest-1', 'win32', 'debug'))
        expected = sorted([u'Windows 7 32-bit try debug test mochitest-1',
                           u'Windows XP 32-bit try debug test mochitest-1',
                           u'Windows 7 VM-GFX 32-bit try debug test mochitest-1',
                           u'Windows 7 VM 32-bit try debug test mochitest-1'])
        assert obtained == expected

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_without_platform(self, fetch_allthethings_data):
        """The function should return a list with all platforms for that test."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        obtained = sorted(find_buildernames(
            repo='mozilla-beta',
            suite_name='tp5o-e10s',
            job_type=None)
        )
        expected = sorted(['Rev7 MacOSX Yosemite 10.10.5 mozilla-beta talos tp5o-e10s',
                           'Ubuntu HW 12.04 x64 mozilla-beta pgo talos tp5o-e10s',
                           'Windows 7 32-bit mozilla-beta pgo talos tp5o-e10s',
                           'Windows 8 64-bit mozilla-beta pgo talos tp5o-e10s',
                           'Windows XP 32-bit mozilla-beta pgo talos tp5o-e10s'])
        assert obtained == expected

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_without_test(self, fetch_allthethings_data):
        """The function should return a list with all tests for that platform."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        obtained = sorted(find_buildernames(repo='try', platform='android-x86'))
        expected = sorted([u'Android 4.2 x86 Emulator try opt test androidx86-set-4'])
        assert obtained == expected

    def test_invalid(self):
        """The function should raise an error if both platform and test are None."""
        with pytest.raises(AssertionError):
            find_buildernames('try', suite_name=None, platform=None)


class TestFilterBuildernames(unittest.TestCase):

    """Test filter_buildernames with mock data."""

    def test_include_exclude(self):
        """filter_buildernames should return a list matching the criteria."""
        buildernames = ALLTHETHINGS['builders'].keys()
        obtained = sorted(filter_buildernames(
            include=['try', 'mochitest-1', 'Windows'],
            exclude=['debug', 'pgo'],
            buildernames=buildernames
        ))
        expected = [u'Windows 10 64-bit try opt test mochitest-1',
                    u'Windows 7 32-bit try opt test mochitest-1',
                    u'Windows 7 VM 32-bit try opt test mochitest-1',
                    u'Windows 7 VM-GFX 32-bit try opt test mochitest-1',
                    u'Windows 8 64-bit try opt test mochitest-1',
                    u'Windows XP 32-bit try opt test mochitest-1']
        assert obtained == expected


class TestSETA(unittest.TestCase):

    """Test get_SETA_interval_dict and get_SETA_info with mock data."""

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_parse_correctly(self, fetch_allthethings_data):
        """get_SETA_interval_dict should return a dict with correct SETA intervals."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        assert get_SETA_interval_dict() == SETA_RESULT

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_return_correct_data(self, fetch_allthethings_data):
        """get_SETA_info should return a list with correct SETA iterval for given buildername."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        assert get_SETA_info("Ubuntu VM 12.04 x64 fx-team opt test mochitest-2") == [7, 3600]

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_get_max_pushes_with_seta(self, fetch_allthethings_data):
        """get_max_pushes should return the number of pushes associated to the SETA scheduler."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        assert get_max_pushes("Ubuntu VM 12.04 x64 fx-team opt test mochitest-2") == 7

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_get_max_pushes_with_no_seta(self, fetch_allthethings_data):
        """get_max_pushes should return the number of pushes associated to the SETA scheduler."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        assert get_max_pushes("Platform2 mozilla-beta talos tp5o") == MAX_PUSHES


class TestGetPlatform(unittest.TestCase):

    """Test get_associated_platform_name with mock data."""

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_with_test_job(self, fetch_allthethings_data):
        """For non-talos test jobs it should return the platform attribute."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        obtained = get_associated_platform_name('Windows 10 64-bit try opt test mochitest-1')
        assert obtained == 'win64'

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_talos(self, fetch_allthethings_data):
        """For talos jobs it should return the stage-platform attribute."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        assert get_associated_platform_name('Ubuntu HW 12.04 x64 try talos tp5o') == 'linux64'

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_with_build_job(self, fetch_allthethings_data):
        """For build jobs it should return the platform attribute."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        assert get_associated_platform_name('OS X 10.7 try build') == 'macosx64'


class TestWantedBuilder(unittest.TestCase):

    """Test _wanted_builder with mock data."""

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_tests(self, fetch_allthethings_data):
        """For pgo builds it should return False as an equivalent opt build exists."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        assert _wanted_builder('Windows XP 32-bit mozilla-central debug test mochitest-1') is True
        assert _wanted_builder('Windows XP 32-bit mozilla-central opt test mochitest-1') is True
        assert _wanted_builder('Windows XP 32-bit mozilla-central pgo test mochitest-1') is True
        assert _wanted_builder('Windows XP 32-bit mozilla-aurora debug test mochitest-1') is True
        assert _wanted_builder('Windows XP 32-bit mozilla-aurora opt test mochitest-1') is True
        assert _wanted_builder('Windows XP 32-bit mozilla-aurora pgo test mochitest-1') is True

        with pytest.raises(MissingBuilderError):
            _wanted_builder('Windows XP 32-bit non-existent-repo1 pgo test mochitest-1')

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_talos(self, fetch_allthethings_data):
        """For opt builds it should return True ."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        assert _wanted_builder('Windows XP 32-bit mozilla-central pgo talos tp5o') is True
        assert _wanted_builder('Windows XP 32-bit mozilla-central talos tp5o') is True
        assert _wanted_builder('Windows XP 32-bit mozilla-aurora pgo talos tp5o') is True
        assert _wanted_builder('Windows XP 32-bit mozilla-aurora talos tp5o') is False
        assert _wanted_builder('Windows XP 32-bit try talos tp5o') is True

        with pytest.raises(MissingBuilderError):
            _wanted_builder('Windows XP 32-bit try pgo talos tp5o') is True


class TestBuildGraph(unittest.TestCase):

    """Test build_tests_per_platform_graph."""

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_build_graph(self, fetch_allthethings_data):
        """Test if the graph has the correct format."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        builders = list_builders(repo_name='try')  # XXX: why are we only choosing try?
        new_graph = build_tests_per_platform_graph(builders)
        assert new_graph == GRAPH_RESULT


class TestDetermineUpstream(unittest.TestCase):

    """Test determine_upstream_builder with mock data."""

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_valid(self, fetch_allthethings_data):
        """Test if the function finds the right builder."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        assert determine_upstream_builder(
            'Windows XP 32-bit try opt test mochitest-1') == 'WINNT 5.2 try build'
        assert determine_upstream_builder(
            'Windows XP 32-bit try debug test mochitest-1') == 'WINNT 5.2 try leak test build'
        assert determine_upstream_builder(
            'Windows XP 32-bit mozilla-beta pgo talos tp5o') == 'WINNT 5.2 mozilla-beta build'

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_no_associated_build(self, fetch_allthethings_data):
        # XXX: Should this test instead raise an exception?
        assert determine_upstream_builder('Windows XP 32-bit mozilla-beta talos tp5o') is None

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_invalid(self, fetch_allthethings_data):
        """Raises Exception for buildernames not in allthethings.json."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        with pytest.raises(Exception):
            determine_upstream_builder("Not a valid buildername")


class TestGetDownstream(unittest.TestCase):

    """Test get_downstream_jobs with data."""

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_valid(self, fetch_allthethings_data):
        """Test if the function finds the right downstream jobs."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        build = 'Android armv7 API 15+ try build'
        obtained = sorted(get_downstream_jobs(build))
        expected = sorted(GRAPH_RESULT['opt']['android-api-15'][build])
        assert obtained == expected


class TestTalosBuildernames(unittest.TestCase):

    """We need this class because of the mock module."""

    @patch('mozci.platforms.list_builders')
    def test_talos_buildernames(self, list_builders):
        """Test build_talos_buildernames_for_repo with mock data."""
        list_builders.return_value = [
            'PlatformA try talos buildername',
            'PlatformB try talos buildername',
            'PlatformA try pgo talos buildername',
            'Platform try buildername'
        ]
        assert build_talos_buildernames_for_repo('try') == [
            'PlatformA try talos buildername', 'PlatformB try talos buildername']
        assert build_talos_buildernames_for_repo(repo_name='try', pgo_only=True) == [
            'PlatformA try pgo talos buildername', 'PlatformB try talos buildername']
        assert build_talos_buildernames_for_repo(repo_name='not-a-repo', pgo_only=True) == []

    def test_talos_single_build(self):
        """Test if the function finds the right suite_name."""
        import mozci.platforms
        mozci.platforms.fetch_allthethings_data = Mock(return_value=ALLTHETHINGS)
        DOWNSTREAM = [
            "Ubuntu HW 12.04 x64 mozilla-inbound pgo talos chromez-e10s",
            "Ubuntu HW 12.04 x64 mozilla-inbound pgo talos dromaeojs",
            "Ubuntu HW 12.04 x64 mozilla-inbound pgo talos dromaeojs-e10s"
        ]
        mozci.platforms.get_downstream_jobs = Mock(return_value=DOWNSTREAM)
        build = "Linux x86-64 mozilla-inbound pgo-build"
        assert get_talos_jobs_for_build(build) == DOWNSTREAM


suitename_test_cases = [
    ("Windows XP 32-bit try talos tp5o", "tp5o"),
    ("Windows XP 32-bit try opt test mochitest-1", "mochitest-1"),
]


@pytest.mark.parametrize("test_job, expected", suitename_test_cases)
def test_suite_name(test_job, expected):
    """Test if the function finds the right suite_name."""
    import mozci.platforms
    mozci.platforms.fetch_allthethings_data = Mock(return_value=ALLTHETHINGS)
    obtained = get_buildername_metadata(test_job)['suite_name']
    assert obtained == expected, 'obtained: "%s", expected "%s"' % (obtained, expected)


buildtype_test_cases = [
    ("Windows XP 32-bit try debug test mochitest-1", "debug"),
    ("Windows XP 32-bit try talos tp5o", "opt"),
    ("Windows XP 32-bit try opt test mochitest-1", "opt"),
    ("WINNT 5.2 mozilla-inbound build", "opt"),
    ("WINNT 5.2 mozilla-aurora build", "pgo"),
    ("WINNT 5.2 mozilla-inbound pgo-build", "pgo")
]


@pytest.mark.parametrize("test_job, expected", buildtype_test_cases)
def test_buildtype_name(test_job, expected):
    """Test if the function finds the right build_type."""
    import mozci.platforms
    mozci.platforms.fetch_allthethings_data = Mock(return_value=ALLTHETHINGS)
    obtained = _get_job_type(test_job)
    assert obtained == expected, 'obtained: "{}", expected "{}"'.format(obtained, expected)


def test_include_builders_matching():
    """Test that _include_builders_matching correctly filters builds."""
    BUILDERS = ["Ubuntu HW 12.04 mozilla-aurora talos svgr",
                "Ubuntu VM 12.04 b2g-inbound debug test xpcshell"]
    obtained = _include_builders_matching(BUILDERS, " talos ")
    expected = ["Ubuntu HW 12.04 mozilla-aurora talos svgr"]
    assert obtained == expected, 'obtained: "{}", expected "{}"'.format(obtained, expected)


nightly_test_cases = [
    ("Windows XP 32-bit try debug test mochitest-1", False),
    ("Windows XP 32-bit try talos tp5o", False),
    ("Windows XP 32-bit try opt test mochitest-1", False),
    ("WINNT 5.2 mozilla-central nightly", True),
    ("Android 4.2 x86 mozilla-central nightly", True)
]


@pytest.mark.parametrize("test_job, expected", nightly_test_cases)
def test_nightly_build(test_job, expected):
    """Test whether nightly builds are caught by get_buildername_metadata"""
    import mozci.platforms
    mozci.platforms.fetch_allthethings_data = Mock(return_value=ALLTHETHINGS)
    obtained = get_buildername_metadata(test_job)['nightly']
    assert obtained == expected, 'obtained: "%s", expected "%s"' % (obtained, expected)


@pytest.mark.parametrize("test_job, nightly", nightly_test_cases)
def test_extra_builder_properties(test_job, nightly):
    """Testing the get_builder_extra_properties function for correct buildid"""
    extra_properties = get_builder_extra_properties(test_job)
    if nightly is True:
        assert 'buildid' in extra_properties, "buildid is needed for nightly builds"
        timestamp_now = int(time.strftime("%Y%m%d%H%M%S"))
        timestamp_obtained = int(extra_properties['buildid'])
        limit = 5
        assert timestamp_now - timestamp_obtained < limit, "buildid should be a recent timestamp"
    else:
        assert 'buildid' not in extra_properties, "Non nighlty builds need not have buildid"
