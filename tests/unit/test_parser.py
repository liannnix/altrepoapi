import pytest
import datetime

from altrepo_api.api import parser


@pytest.mark.parametrize(
    "test_input,expected_exception,expected",
    [
        ("abc", None, "abc"),
        ("abc123+.-_", None, "abc123+.-_"),
        ("", ValueError, None),
        ("a", ValueError, None),
        ("a*", ValueError, None),
        ("a b", ValueError, None),
        ("a/b", ValueError, None),
    ],
)
def test_pkg_name_type(test_input, expected_exception, expected):
    if not expected_exception:
        assert parser.pkg_name_type(test_input) == expected
    else:
        pytest.raises(expected_exception, parser.pkg_name_type, test_input)


@pytest.mark.parametrize(
    "test_input,expected_exception,expected",
    [
        ("abc", None, "abc"),
        ("abc123+._", None, "abc123+._"),
        ("1.5.9+abc", None, "1.5.9+abc"),
        ("", ValueError, None),
        (" a", ValueError, None),
        ("a*", ValueError, None),
        ("a-b", ValueError, None),
        ("a/b", ValueError, None),
    ],
)
def test_pkg_version_type(test_input, expected_exception, expected):
    if not expected_exception:
        assert parser.pkg_version_type(test_input) == expected
    else:
        pytest.raises(expected_exception, parser.pkg_version_type, test_input)


@pytest.mark.parametrize(
    "test_input,expected_exception,expected",
    [
        ("abc", None, "abc"),
        ("abc123+._", None, "abc123+._"),
        ("1.5.9+abc", None, "1.5.9+abc"),
        ("", ValueError, None),
        (" a", ValueError, None),
        ("a*", ValueError, None),
        ("a-b", ValueError, None),
        ("a/b", ValueError, None),
    ],
)
def test_pkg_release_type(test_input, expected_exception, expected):
    if not expected_exception:
        assert parser.pkg_version_type(test_input) == expected
    else:
        pytest.raises(expected_exception, parser.pkg_version_type, test_input)


@pytest.mark.parametrize(
    "test_input,expected_exception,expected",
    [
        ("sisyphus", None, "sisyphus"),
        ("p10", None, "p10"),
        ("5.1", None, "5.1"),
        ("", ValueError, None),
        (" p10", ValueError, None),
        ("p99", ValueError, None),
        ("5.1.2", ValueError, None),
    ],
)
def test_branch_name_type(test_input, expected_exception, expected):
    if not expected_exception:
        assert parser.branch_name_type(test_input) == expected
    else:
        pytest.raises(expected_exception, parser.branch_name_type, test_input)


@pytest.mark.parametrize(
    "test_input,expected_exception,expected",
    [
        ("x86_64", None, "x86_64"),
        ("ppc64le", None, "ppc64le"),
        ("i586", None, "i586"),
        ("", ValueError, None),
        (" aarch64", ValueError, None),
        ("abc", ValueError, None),
        ("123", ValueError, None),
    ],
)
def test_arch_name_type(test_input, expected_exception, expected):
    if not expected_exception:
        assert parser.arch_name_type(test_input) == expected
    else:
        pytest.raises(expected_exception, parser.arch_name_type, test_input)


@pytest.mark.parametrize(
    "test_input,expected_exception,expected",
    [
        ("Server", None, "Server"),
        ("System/Libraries", None, "System/Libraries"),
        ("Tools/Test tools", None, "Tools/Test tools"),
        ("Development/C++ compiler", None, "Development/C++ compiler"),
        ("", ValueError, None),
        ("system", ValueError, None),
        (" System", ValueError, None),
        ("System\\tools", ValueError, None),
        ("Development/x.compiler", ValueError, None),
    ],
)
def test_pkg_groups_type(test_input, expected_exception, expected):
    if not expected_exception:
        assert parser.pkg_groups_type(test_input) == expected
    else:
        pytest.raises(expected_exception, parser.pkg_groups_type, test_input)


@pytest.mark.parametrize(
    "test_input,expected_exception,expected",
    [
        ("test@test.com", None, "test@test.com"),
        ("t.e_s-t@t.e_s-t", None, "t.e_s-t@t.e_s-t"),
        ("a@b", None, "a@b"),
        ("", ValueError, None),
        (" test@test", ValueError, None),
        ("te st@test", ValueError, None),
        ("test@test ", ValueError, None),
        ("test@ test", ValueError, None),
        ("test at test", ValueError, None),
        ("test@", ValueError, None),
        ("test@x+", ValueError, None),
    ],
)
def test_packager_email_type(test_input, expected_exception, expected):
    if not expected_exception:
        assert parser.packager_email_type(test_input) == expected
    else:
        pytest.raises(expected_exception, parser.packager_email_type, test_input)


@pytest.mark.parametrize(
    "test_input,expected_exception,expected",
    [
        ("Test", None, "Test"),
        ("Test Test", None, "Test Test"),
        ("Test T. Test", None, "Test T. Test"),
        ("Test T-est", None, "Test T-est"),
        ("Test T_est", None, "Test T_est"),
        ("test@test.com", None, "test@test.com"),
        ("t.e_s-t@test.com", None, "t.e_s-t@test.com"),
        ("", ValueError, None),
        (" test@test", ValueError, None),
        ("123", ValueError, None),
        ("_Tst", ValueError, None),
        # ("test@ test", ValueError, None),
        ("test ! test", ValueError, None),
        ("1test", ValueError, None),
        ("test@x+y.com", ValueError, None),
    ],
)
def test_packager_name_type(test_input, expected_exception, expected):
    if not expected_exception:
        assert parser.packager_name_type(test_input) == expected
    else:
        pytest.raises(expected_exception, parser.packager_name_type, test_input)


@pytest.mark.parametrize(
    "test_input,expected_exception,expected",
    [
        ("test", None, "test"),
        ("Test", None, "Test"),
        ("test-test", None, "test-test"),
        ("test_test", None, "test_test"),
        ("", ValueError, None),
        ("x", ValueError, None),
        (" xx", ValueError, None),
        ("test ", ValueError, None),
        ("test@test", ValueError, None),
        ("test.test", ValueError, None),
    ],
)
def test_packager_nick_type(test_input, expected_exception, expected):
    if not expected_exception:
        assert parser.packager_nick_type(test_input) == expected
    else:
        pytest.raises(expected_exception, parser.packager_nick_type, test_input)


@pytest.mark.parametrize(
    "test_input,expected_exception,expected",
    [
        ("test", None, "test"),
        ("Test", None, "Test"),
        ("test-test", None, "test-test"),
        ("test_test", None, "test_test"),
        ("", ValueError, None),
        ("x", ValueError, None),
        (" xx", ValueError, None),
        ("test ", ValueError, None),
        ("test@test", ValueError, None),
        ("test.test", ValueError, None),
    ],
)
def test_maintainer_nick_type(test_input, expected_exception, expected):
    if not expected_exception:
        assert parser.maintainer_nick_type(test_input) == expected
    else:
        pytest.raises(expected_exception, parser.maintainer_nick_type, test_input)


@pytest.mark.parametrize(
    "test_input,expected_exception,expected",
    [
        ("01234567890", None, "01234567890"),
        ("abcdef", None, "abcdef"),
        ("ABCDEF", None, "ABCDEF"),
        ("deadBeeF123", None, "deadBeeF123"),
        ("", ValueError, None),
        ("x", ValueError, None),
        (" 123abc", ValueError, None),
        ("123abc ", ValueError, None),
        ("123 abc", ValueError, None),
        ("+-._", ValueError, None),
    ],
)
def test_checksum_type(test_input, expected_exception, expected):
    if not expected_exception:
        assert parser.checksum_type(test_input) == expected
    else:
        pytest.raises(expected_exception, parser.checksum_type, test_input)


@pytest.mark.parametrize(
    "test_input,expected_exception,expected",
    [
        ("a.b.c+123", None, "a.b.c+123"),
        ("p10+123456.100", None, "p10+123456.100"),
        ("test", None, "test"),
        ("", ValueError, None),
        (" test", ValueError, None),
        ("A.b.c+123", ValueError, None),
        ("abc+Test", ValueError, None),
        ("test-123", ValueError, None),
    ],
)
def test_disttag_type(test_input, expected_exception, expected):
    if not expected_exception:
        assert parser.disttag_type(test_input) == expected
    else:
        pytest.raises(expected_exception, parser.disttag_type, test_input)


@pytest.mark.parametrize(
    "test_input,expected_exception,expected",
    [
        ("/test", None, "/test"),
        ("test-123", None, "test-123"),
        ("test_test.123", None, "test_test.123"),
        ("/test/*/test.test*", None, "/test/*/test.test*"),
        ("x*", None, "x*"),
        ("", ValueError, None),
        ("x", ValueError, None),
        (" test", ValueError, None),
        ("/A.b.c+123", ValueError, None),
        ("/abc-Test!", ValueError, None),
        ("/test-123\\x.y", ValueError, None),
    ],
)
def test_file_name_wc_type(test_input, expected_exception, expected):
    if not expected_exception:
        assert parser.file_name_wc_type(test_input) == expected
    else:
        pytest.raises(expected_exception, parser.file_name_wc_type, test_input)


@pytest.mark.parametrize(
    "test_input,expected_exception,expected",
    [
        ("a.b-c:123", None, "a.b-c:123"),
        ("python(test)", None, "python(test)"),
        ("/test/Test", None, "/test/Test"),
        ("", ValueError, None),
        ("x", ValueError, None),
        (" test", ValueError, None),
        ("a.b-c+123", ValueError, None),
        ("abc\\Test", ValueError, None),
        ("test;123", ValueError, None),
    ],
)
def test_dp_name_type(test_input, expected_exception, expected):
    if not expected_exception:
        assert parser.dp_name_type(test_input) == expected
    else:
        pytest.raises(expected_exception, parser.dp_name_type, test_input)


@pytest.mark.parametrize(
    "test_input,expected_exception,expected",
    [
        ("2020-10-20", None, datetime.datetime(2020, 10, 20)),
        ("2020-02-29", None, datetime.datetime(2020, 2, 29)),
        # ("python(test)", None, "python(test)"),
        # ("/test/Test", None, "/test/Test"),
        ("", ValueError, None),
        ("10-20-2020", ValueError, None),
        ("20200516", ValueError, None),
        ("20-10-20", ValueError, None),
        ("2020/10/20", ValueError, None),
        ("2020.10.20", ValueError, None),
        ("2020-02-30", ValueError, None),  # 29th of February
    ],
)
def test_date_string_type(test_input, expected_exception, expected):
    if not expected_exception:
        assert parser.date_string_type(test_input) == expected
    else:
        pytest.raises(expected_exception, parser.date_string_type, test_input)


@pytest.mark.parametrize(
    "test_input,expected_exception,expected",
    [
        ("12345678-abcd-ef01-2345-67890abcdef0", None, "12345678-abcd-ef01-2345-67890abcdef0"),
        ("", ValueError, None),
        ("x2345678-abcd-ef01-2345-67890abcdef0", ValueError, None),
        (" 12345678-abcd-ef01-2345-67890abcdef0", ValueError, None),
        ("12345678-abcd-ef01-2345-67890abcdef0 ", ValueError, None),
        ("1234567-abcd-ef0-2345-67890abcdef0", ValueError, None),
        ("12345678-abc-ef01-2345-67890abcdef0", ValueError, None),
        ("12345678-abcd-ef0-2345-67890abcdef0", ValueError, None),
        ("12345678-abcd-ef01-345-67890abcdef0", ValueError, None),
        ("12345678-abcd-ef01-2345-67890abcdef", ValueError, None),
    ],
)
def test_uuid_type(test_input, expected_exception, expected):
    if not expected_exception:
        assert parser.uuid_type(test_input) == expected
    else:
        pytest.raises(expected_exception, parser.uuid_type, test_input)


@pytest.mark.parametrize(
    "test_input,expected_exception,expected",
    [
        ("xxx:t.e-s_t::T123:xxx.0.1.2:abc", None, "xxx:t.e-s_t::T123:xxx.0.1.2:abc"),
        ("", ValueError, None),
        (":test", ValueError, None),
        ("test", ValueError, None),
        (" test:test", ValueError, None),
        ("test:test ", ValueError, None),
        ("test: :test ", ValueError, None),
        ("test:+:test", ValueError, None),
        ("test:@:test", ValueError, None),
    ],
)
def test_image_tag_type(test_input, expected_exception, expected):
    if not expected_exception:
        assert parser.image_tag_type(test_input) == expected
    else:
        pytest.raises(expected_exception, parser.image_tag_type, test_input)


@pytest.mark.parametrize(
    "test_input,expected_exception,expected",
    [
        ("0.0.0", None, "0.0.0"),
        ("20200220.0.0", None, "20200220.0.0"),
        ("", ValueError, None),
        ("10", ValueError, None),
        ("1.5", ValueError, None),
        (" 1.2.3", ValueError, None),
        ("1.2.3 ", ValueError, None),
        ("1_2_3", ValueError, None),
        ("1-2-3", ValueError, None),
        ("v1.2.3", ValueError, None),
    ],
)
def test_image_version_type(test_input, expected_exception, expected):
    if not expected_exception:
        assert parser.image_version_type(test_input) == expected
    else:
        pytest.raises(expected_exception, parser.image_version_type, test_input)


@pytest.mark.parametrize(
    "test_input,expected_exception,expected",
    [
        ("slinux", None, "slinux"),
        ("alt-server", None, "alt-server"),
        ("alt-server-v", None, "alt-server-v"),
        ("alt-education", None, "alt-education"),
        ("alt-workstation", None, "alt-workstation"),
        ("alt-kworkstation", None, "alt-kworkstation"),
        ("", ValueError, None),
        (" slinux", ValueError, None),
        ("slinux ", ValueError, None),
        ("server", ValueError, None),
        ("workstation", ValueError, None),
    ],
)
def test_img_edition_type(test_input, expected_exception, expected):
    if not expected_exception:
        assert parser.img_edition_type(test_input) == expected
    else:
        pytest.raises(expected_exception, parser.img_edition_type, test_input)


@pytest.mark.parametrize(
    "test_input,expected_exception,expected",
    [
        ("i586", None, "i586"),
        ("x86_64", None, "x86_64"),
        ("ppc64le", None, "ppc64le"),
        ("", ValueError, None),
        ("xxx", ValueError, None),
        (" armh", ValueError, None),
        ("armh ", ValueError, None),
    ],
)
def test_img_arch_type(test_input, expected_exception, expected):
    if not expected_exception:
        assert parser.img_arch_type(test_input) == expected
    else:
        pytest.raises(expected_exception, parser.img_arch_type, test_input)


@pytest.mark.parametrize(
    "test_input,expected_exception,expected",
    [
        ("install", None, "install"),
        ("live", None, "live"),
        ("rescue", None, "rescue"),
        ("", ValueError, None),
        ("test", ValueError, None),
        (" live", ValueError, None),
        ("live ", ValueError, None),
    ],
)
def test_img_variant_type(test_input, expected_exception, expected):
    if not expected_exception:
        assert parser.img_variant_type(test_input) == expected
    else:
        pytest.raises(expected_exception, parser.img_variant_type, test_input)


@pytest.mark.parametrize(
    "test_input,expected_exception,expected",
    [
        ("iso", None, "iso"),
        ("rpms", None, "rpms"),
        ("altinst", None, "altinst"),
        ("live", None, "live"),
        ("rescue", None, "rescue"),
        ("", ValueError, None),
        ("test", ValueError, None),
        (" live", ValueError, None),
        ("live ", ValueError, None),
    ],
)
def test_img_component_type(test_input, expected_exception, expected):
    if not expected_exception:
        assert parser.img_component_type(test_input) == expected
    else:
        pytest.raises(expected_exception, parser.img_component_type, test_input)


@pytest.mark.parametrize(
    "test_input,expected_exception,expected",
    [
        ("rc", None, "rc"),
        ("beta", None, "beta"),
        ("alpha", None, "alpha"),
        ("release", None, "release"),
        ("", ValueError, None),
        ("test", ValueError, None),
        (" beta", ValueError, None),
        ("beta ", ValueError, None),
    ],
)
def test_img_release_type(test_input, expected_exception, expected):
    if not expected_exception:
        assert parser.img_release_type(test_input) == expected
    else:
        pytest.raises(expected_exception, parser.img_release_type, test_input)


@pytest.mark.parametrize(
    "test_input,expected_exception,expected",
    [
        ("rootfs-sysvinit", None, "rootfs-sysvinit"),
        ("rootfs-systemd-etcnet", None, "rootfs-systemd-etcnet"),
        ("opennebula", None, "opennebula"),
        ("workstation", None, "workstation"),
        ("", ValueError, None),
        (" workstation", ValueError, None),
        ("workstation ", ValueError, None),
        ("workstation+", ValueError, None),
    ],
)
def test_img_flavor_type(test_input, expected_exception, expected):
    if not expected_exception:
        assert parser.img_flavor_type(test_input) == expected
    else:
        pytest.raises(expected_exception, parser.img_flavor_type, test_input)


@pytest.mark.parametrize(
    "test_input,expected_exception,expected",
    [
        ("abc", None, "abc"),
        ("abc,def", None, "abc,def"),
        ("abc123+.-_", None, "abc123+.-_"),
        ("", ValueError, None),
        ("a", ValueError, None),
        ("ab,c", ValueError, None),
        ("a,bc", ValueError, None),
        (",bc", ValueError, None),
        ("a*", ValueError, None),
        ("a b", ValueError, None),
        ("a/b", ValueError, None),
    ],
)
def test_pkg_name_list_type(test_input, expected_exception, expected):
    if not expected_exception:
        assert parser.pkg_name_list_type(test_input) == expected
    else:
        pytest.raises(expected_exception, parser.pkg_name_list_type, test_input)
