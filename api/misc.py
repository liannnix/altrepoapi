from dataclasses import dataclass

@dataclass(frozen=True)
class LookupTables:
    known_branches = ['c8.1', 'p8', 'p7', 'p9', 'sisyphus', 'c8', 'c9f1', 'c9f2']
    known_archs = [
        'x86_64', 'noarch', 'x86_64-i586', 'armh', 'arm',
        'i586', 'pentium4', 'athlon', 'pentium3', 'i686',
        'armv5tel', 'k6', 'aarch64', 'ppc64le', 'e2kv4',
        'e2k', 'mipsel'
    ]
    default_archs = ['x86_64', 'i586', 'aarch64', 'armh', 'ppc64le', 'noarch']
    package_params = [
        'pkg_cs', 'pkg_packager', 'pkg_packager_email', 'pkg_name', 'pkg_arch', 'pkg_version',
        'pkg_release', 'pkg_epoch', 'pkg_serial_', 'pkg_buildtime', 'pkg_buildhost', 'pkg_size',
        'pkg_archivesize', 'pkg_rpmversion', 'pkg_cookie', 'pkg_disttag', 'pkg_sourcerpm',
        'pkg_filename', 'pkg_filesize', 'pkg_srcrpm_hash', 'pkg_summary', 'pkg_description',
        'pkg_distribution', 'pkg_vendor', 'pkg_gif', 'pkg_xpm', 'pkg_license', 'pkg_group_',
        'pkg_url', 'pkg_os', 'pkg_prein', 'pkg_postin', 'pkg_preun', 'pkg_postun', 'pkg_icon',
        'pkg_preinprog', 'pkg_postinprog', 'pkg_preunprog', 'pkg_postunprog', 'pkg_buildarchs',
        'pkg_verifyscript', 'pkg_verifyscriptprog', 'pkg_prefixes', 'pkg_instprefixes',
        'pkg_optflags', 'pkg_disturl', 'pkg_payloadformat', 'pkg_payloadcompressor',
        'pkg_payloadflags', 'pkg_platform', 'pkg_sourcepackage'
    ]

lut = LookupTables()
