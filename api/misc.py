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

lut = LookupTables()
