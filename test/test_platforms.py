"""This file contains tests for mozci/platforms.py."""
import pytest
import unittest

from mock import patch
from mock import Mock
from mozci.errors import MozciError
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
)


from helpers import (
    ALLTHETHINGS,
    SETA_RESULT,
    GRAPH_RESULT
)


class TestIsDownstream(unittest.TestCase):

    """Test is_downstream with mock data."""

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_valid(self, fetch_allthethings_data):
        """is_downstream should return True for test jobs and False for build jobs."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        self.assertEquals(
            is_downstream('Ubuntu VM 12.04 x64 mozilla-beta debug test mochitest-1'), True)
        self.assertEquals(
            is_downstream('Linux x86-64 mozilla-beta build'), False)

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
        obtained = sorted(find_buildernames('try', 'mochitest-1', 'win32', 'opt'))
        expected = sorted([u'Windows XP 32-bit try opt test mochitest-1',
                           u'Windows 7 VM-GFX 32-bit try opt test mochitest-1',
                           u'Windows 7 32-bit try opt test mochitest-1',
                           u'Windows 7 VM 32-bit try opt test mochitest-1'])
        self.assertEquals(obtained, expected)

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_with_debug(self, fetch_allthethings_data):
        """The function should return a list with the specific debug buildername."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        obtained = sorted(find_buildernames('try', 'mochitest-1', 'win32', 'debug'))
        expected = sorted([u'Windows 7 32-bit try debug test mochitest-1',
                           u'Windows XP 32-bit try debug test mochitest-1',
                           u'Windows 7 VM-GFX 32-bit try debug test mochitest-1',
                           u'Windows 7 VM 32-bit try debug test mochitest-1'])
        self.assertEquals(obtained, expected)

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_without_platform(self, fetch_allthethings_data):
        """The function should return a list with all platforms for that test."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        obtained = sorted(find_buildernames(repo='mozilla-beta', suite_name='tp5o', job_type=None))
        expected = sorted(['Rev7 MacOSX Yosemite 10.10.5 mozilla-beta talos tp5o',
                           'Ubuntu HW 12.04 x64 mozilla-beta pgo talos tp5o',
                           'Windows 7 32-bit mozilla-beta pgo talos tp5o',
                           'Windows 8 64-bit mozilla-beta pgo talos tp5o',
                           'Windows XP 32-bit mozilla-beta pgo talos tp5o'])
        self.assertEquals(obtained, expected)

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_without_test(self, fetch_allthethings_data):
        """The function should return a list with all tests for that platform."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        obtained = sorted(find_buildernames(repo='try', platform='android-x86'))
        expected = sorted([u'Android 4.2 x86 Emulator try opt test androidx86-set-4'])
        self.assertEquals(obtained, expected)

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
        self.assertEquals(obtained, expected)


class TestSETA(unittest.TestCase):

    """Test get_SETA_interval_dict and get_SETA_info with mock data."""

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_parse_correctly(self, fetch_allthethings_data):
        """get_SETA_interval_dict should return a dict with correct SETA intervals."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        self.assertEquals(
            get_SETA_interval_dict(),
            SETA_RESULT
        )

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_return_correct_data(self, fetch_allthethings_data):
        """get_SETA_info should return a list with correct SETA iterval for given buildername."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        self.assertEquals(
            get_SETA_info("Ubuntu VM 12.04 x64 fx-team opt test mochitest-2"),
            [7, 3600]
        )

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_get_max_pushes_with_seta(self, fetch_allthethings_data):
        """get_max_pushes should return the number of pushes associated to the SETA scheduler."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        self.assertEquals(
            get_max_pushes("Ubuntu VM 12.04 x64 fx-team opt test mochitest-2"), 7)

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_get_max_pushes_with_no_seta(self, fetch_allthethings_data):
        """get_max_pushes should return the number of pushes associated to the SETA scheduler."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        self.assertEquals(
            get_max_pushes("Platform2 mozilla-beta talos tp5o"), MAX_PUSHES)


class TestGetPlatform(unittest.TestCase):

    """Test get_associated_platform_name with mock data."""

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_with_test_job(self, fetch_allthethings_data):
        """For non-talos test jobs it should return the platform attribute."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        obtained = get_associated_platform_name('Windows 10 64-bit try opt test mochitest-1')
        expected = 'win64'
        self.assertEquals(obtained, expected)

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_talos(self, fetch_allthethings_data):
        """For talos jobs it should return the stage-platform attribute."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        self.assertEquals(
            get_associated_platform_name('Ubuntu HW 12.04 x64 try talos tp5o'),
            'linux64')

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_with_build_job(self, fetch_allthethings_data):
        """For build jobs it should return the platform attribute."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        self.assertEquals(
            get_associated_platform_name('OS X 10.7 try build'),
            'macosx64')


class TestWantedBuilder(unittest.TestCase):

    """Test _wanted_builder with mock data."""

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_pgo(self, fetch_allthethings_data):
        """For pgo builds it should return False as an equivalent opt build exists."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        self.assertEquals(
            _wanted_builder('Windows XP 32-bit mozilla-central pgo test mochitest-1'),
            False)
        self.assertEquals(
            _wanted_builder('Windows XP 32-bit mozilla-aurora pgo test mochitest-1'),
            True)
        self.assertEquals(
            _wanted_builder('Windows XP 32-bit mozilla-inbound pgo test mochitest-1'),
            False)
        self.assertEquals(
            _wanted_builder('Windows XP 32-bit mozilla-beta pgo test mochitest-1'),
            True)
        self.assertEquals(
            _wanted_builder('Windows XP 32-bit mozilla-release pgo test mochitest-1'),
            True)
        self.assertEquals(
            _wanted_builder('Windows XP 32-bit mozilla-esr38 pgo test mochitest-1'),
            True)
        self.assertEquals(
            _wanted_builder('Windows XP 32-bit mozilla-esr45 pgo test mochitest-1'),
            True)
        self.assertEquals(
            _wanted_builder('Windows XP 32-bit fx-team pgo test mochitest-1'),
            False)
        with pytest.raises(MozciError):
            _wanted_builder('Windows XP 32-bit non-existent-repo1 pgo test mochitest-1')

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_opt(self, fetch_allthethings_data):
        """For opt builds it should return True ."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        self.assertEquals(
            _wanted_builder('Windows XP 32-bit mozilla-central opt test mochitest-1'),
            True)
        self.assertEquals(
            _wanted_builder('Windows XP 32-bit mozilla-aurora opt test mochitest-1'),
            True)
        self.assertEquals(
            _wanted_builder('Windows XP 32-bit mozilla-inbound opt test mochitest-1'),
            True)
        self.assertEquals(
            _wanted_builder('Windows XP 32-bit mozilla-beta opt test mochitest-1'),
            True)
        self.assertEquals(
            _wanted_builder('Windows XP 32-bit mozilla-release opt test mochitest-1'),
            True)
        self.assertEquals(
            _wanted_builder('Windows XP 32-bit mozilla-esr38 opt test mochitest-1'),
            True)
        self.assertEquals(
            _wanted_builder('Windows XP 32-bit mozilla-esr45 opt test mochitest-1'),
            True)
        self.assertEquals(
            _wanted_builder('Windows XP 32-bit try opt test mochitest-1'),
            True)
        with pytest.raises(MozciError):
            _wanted_builder('Windows XP 32-bit non-existent-repo2 opt test mochitest-1')


class TestBuildGraph(unittest.TestCase):

    """Test build_tests_per_platform_graph."""

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_build_graph(self, fetch_allthethings_data):
        """Test if the graph has the correct format."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        builders = list_builders(repo_name='try')
        builders.sort()
        expected = GRAPH_RESULT
        self.assertEquals(build_tests_per_platform_graph(builders), expected)


class TestDetermineUpstream(unittest.TestCase):

    """Test determine_upstream_builder with mock data."""

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_valid(self, fetch_allthethings_data):
        """Test if the function finds the right builder."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        self.assertEquals(
            determine_upstream_builder('Windows XP 32-bit try opt test mochitest-1'),
            'WINNT 5.2 try build')
        self.assertEquals(
            determine_upstream_builder('Windows XP 32-bit try debug test mochitest-1'),
            'WINNT 5.2 try leak test build')
        self.assertEquals(
            determine_upstream_builder('Windows XP 32-bit mozilla-beta pgo talos tp5o'),
            'WINNT 5.2 mozilla-beta build')
        self.assertEquals(
            determine_upstream_builder('Windows XP 32-bit mozilla-beta talos tp5o'),
            None)

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_invalid(self, fetch_allthethings_data):
        """Raises Exception for buildernames not in allthethings.json."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        with pytest.raises(Exception):
            determine_upstream_builder("Not a valid buildername")
        self.assertEquals(
            determine_upstream_builder("Windows XP 32-bit mozilla-beta talos tp5o"), None)


class TestGetDownstream(unittest.TestCase):

    """Test get_downstream_jobs with data."""

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_valid(self, fetch_allthethings_data):
        """Test if the function finds the right downstream jobs."""
        fetch_allthethings_data.return_value = ALLTHETHINGS
        downstream_builders = sorted(get_downstream_jobs('Android armv7 API 15+ try build'))
        test_result = True
        some_expected = GRAPH_RESULT['opt']['android-api-15']['Android armv7 API 15+ try build']
        for buildername in some_expected:
            if buildername not in downstream_builders:
                test_result = False
                break
        self.assertTrue(test_result)


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
        self.assertEquals(build_talos_buildernames_for_repo('try'),
                          ['PlatformA try talos buildername',
                           'PlatformB try talos buildername'])
        self.assertEquals(build_talos_buildernames_for_repo('try', True),
                          ['PlatformA try pgo talos buildername',
                           'PlatformB try talos buildername'])
        self.assertEquals(build_talos_buildernames_for_repo('not-a-repo'), [])

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
        expected = DOWNSTREAM
        self.assertEquals(get_talos_jobs_for_build(build), expected)


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
    assert obtained == expected, \
        'obtained: "%s", expected "%s"' % (obtained, expected)


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
    assert obtained == expected, \
        'obtained: "%s", expected "%s"' % (obtained, expected)


def test_include_builders_matching():
    """Test that _include_builders_matching correctly filters builds."""
    BUILDERS = ["Ubuntu HW 12.04 mozilla-aurora talos svgr",
                "Ubuntu VM 12.04 b2g-inbound debug test xpcshell"]
    obtained = _include_builders_matching(BUILDERS, " talos ")
    expected = ["Ubuntu HW 12.04 mozilla-aurora talos svgr"]
    assert obtained == expected, \
        'obtained: "%s", expected "%s"' % (obtained, expected)
