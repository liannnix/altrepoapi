from flask_restx import fields

from api.package.package import ns

package_info_changelog_el_model = ns.model('PackageInfoChangelogElementModel', {
    'date': fields.String(description='changelog date'),
    'name': fields.String(description='changelog name'),
    'evr': fields.String(description='changelog EVR'),
    'message': fields.String(description='changelog message')
})
package_info_dependencies_model = ns.model('PackageInfoDependenciesModel', {
    'require': fields.List(fields.String, description='package requires'),
    'provide': fields.List(fields.String, description='package provides'),
    'conflict': fields.List(fields.String, description='package conflicts'),
    'obsolete': fields.List(fields.String, description='package obsoletes')
})
package_info_package_model = ns.model('PackageInfoPackageModel', {
    'name': fields.String(attribute='pkg_name', description='package name'),
    'version': fields.String(attribute='pkg_version', description='package version'),
    'release': fields.String(attribute='pkg_release', description='package release'),
    'sha1': fields.String(attribute='pkg_cs', description='package SHA1 header checksum'),
    'packager': fields.String(attribute='pkg_packager', description='package packager name'),
    'packager_email': fields.String(attribute='pkg_packager_email', description='package packager email'),
    'arch': fields.String(attribute='pkg_arch', description='package arch'),
    'epoch': fields.Integer(attribute='pkg_epoch', description='package epoch'),
    'disttag': fields.String(attribute='pkg_disttag', description='package disttag'),
    'sourcepackage': fields.Integer(attribute='pkg_sourcepackage', description='is sourcepackage'),
    'filename': fields.String(attribute='pkg_filename', description='package file'),
    'sourcerpm': fields.String(attribute='pkg_sourcerpm', description='source package file'),
    'serial': fields.Integer(attribute='pkg_serial_', description='package serial'),
    'buildtime': fields.Integer(attribute='pkg_buildtime', description='package build time'),
    'buildhost': fields.String(attribute='pkg_buildhost', description='build host'),
    'size': fields.Integer(attribute='pkg_size', description='package size'),
    'archivesize': fields.Integer(attribute='pkg_archivesize', description='package archive size'),
    'filesize': fields.Integer(attribute='pkg_filesize', description='package file size'),
    'rpmversion': fields.String(attribute='pkg_rpmversion', description='rpm version'),
    'cookie': fields.String(attribute='pkg_cookie', description='package coockie'),
    'license': fields.String(attribute='pkg_license', description='package license'),
    'group': fields.String(attribute='pkg_group_', description='package group'),
    'url': fields.String(attribute='pkg_url', description='package url'),
    'summary': fields.String(attribute='pkg_summary', description='package summary'),
    'description': fields.String(attribute='pkg_description', description='package description'),
    'distribution': fields.String(attribute='pkg_distribution', description='package distribution'),
    'vendor': fields.String(attribute='pkg_vendor', description='package vendor'),
    'os': fields.String(attribute='pkg_os', description='package os'),
    'gif': fields.String(attribute='pkg_gif', description='package gif'),
    'xpm': fields.String(attribute='pkg_xpm', description='package xpm'),
    'icon': fields.String(attribute='pkg_icon', description='package icon'),
    'prein': fields.String(attribute='pkg_prein', description='package prein'),
    'postin': fields.String(attribute='pkg_postin', description='package postin'),
    'preun': fields.String(attribute='pkg_preun', description='package preun'),
    'postun': fields.String(attribute='pkg_postun', description='package postun'),
    'preinprog': fields.List(fields.String, attribute='pkg_preinprog'),
    'postinprog': fields.List(fields.String, attribute='pkg_postinprog'),
    'preunprog': fields.List(fields.String, attribute='pkg_preunprog'),
    'postunprog': fields.List(fields.String, attribute='pkg_postunprog'),
    'buildarchs': fields.List(fields.String, attribute='pkg_buildarchs'),
    'verifyscript': fields.String(attribute='pkg_verifyscript', description='package verifyscript'),
    'verifyscriptprog': fields.List(fields.String, attribute='pkg_verifyscriptprog'),
    'prefixes': fields.List(fields.String, attribute='pkg_prefixes'),
    'instprefixes': fields.List(fields.String, attribute='pkg_instprefixes'),
    'optflags': fields.String(attribute='pkg_optflags', description='package optflags'),
    'disturl': fields.String(attribute='pkg_disturl', description='package disturl'),
    'payloadformat': fields.String(attribute='pkg_payloadformat', description='package payload format'),
    'payloadcompressor': fields.String(attribute='pkg_payloadcompressor', description='package payload compressor'),
    'payloadflags': fields.String(attribute='pkg_payloadflags', description='package payload flags'),
    'platform': fields.String(attribute='pkg_platform', description='package platform'),
    'changelog': fields.Nested(package_info_changelog_el_model, as_list=True, description='package changelog'),
    'files': fields.List(fields.String, description='package files'),
    'depends': fields.Nested(package_info_dependencies_model, as_list=True, description='package dependencies')
})
package_info_model = ns.model('PackageInfoModel', {
    'request_args': fields.Raw(description='request arguments'),
    'length': fields.Integer(description='number of packages found'),
    'packages': fields.Nested(package_info_package_model,
                              description='packages info',
                              as_list=True
                              )
})

pkg_build_dep_el_model = ns.model('PackageBuildDependencyElementModel', {
    'name': fields.String(description='package name'),
    'version': fields.String(description='package version'),
    'release': fields.String(description='package release'),
    'epoch': fields.Integer(description='package epoch'),
    'serial': fields.Integer(attribute='serial_', description='package serial'),
    'sourcerpm': fields.String(description='source package file'),
    'branch': fields.String(description='package set name'),
    'buildtime': fields.String(description='package build time'),
    'archs': fields.List(fields.String, description='package archs'),
    'cycle': fields.List(fields.String, description='package cycle dependencies'),
    'requires': fields.List(fields.String, description='package requirements'),
    'acl': fields.List(fields.String, description='package ACL list')
})
pkg_build_dep_model = ns.model('PackageBuildDependencyModel', {
    'request_args': fields.Raw(description='request arguments'),
    'length': fields.Integer(description='number of packages found'),
    'dependencies': fields.Nested(pkg_build_dep_el_model,
                                  description='build dependency results',
                                  as_list=True
                                  )
})

misconflict_pkg_model = ns.model('PackageMisconflictPackageModel', {
    'input_package': fields.String(description='package name'),
    'conflict_package': fields.String(description='package name'),
    'version': fields.String(description='package version'),
    'release': fields.String(description='package release'),
    'epoch': fields.Integer(description='package epoch'),
    'archs': fields.List(fields.String, description='package archs'),
    'files_with_conflict': fields.List(fields.String, description='conflict files')
})
misconflict_pkgs_model = ns.model('PackageMisconflictPackagesModel', {
    'request_args': fields.Raw(description='request arguments'),
    'length': fields.Integer(description='number of packages found'),
    'conflicts': fields.Nested(misconflict_pkg_model,
                               description='conflicts',
                               as_list=True
                               )
})

pkg_find_pkgset_el_model = ns.model('PackageFindPackagesetElementModel', {
    'branch': fields.String(description='package set name'),
    'pkgset_datetime': fields.String(description='package set date'),
    'sourcepkgname': fields.String(description='source package name'),
    'packages': fields.List(fields.String, description='binary packages list'),
    'version': fields.String(description='package version'),
    'release': fields.String(description='package release'),
    'disttag': fields.String(description='package disttag'),
    'packager_email': fields.String(description='package packager email'),
    'buildtime': fields.String(description='package build time'),
    'archs': fields.List(fields.String, description='binary packages archs')
})
pkg_find_pkgset_model = ns.model('PackageFindPackagesetModel', {
    'request_args': fields.Raw(description='request arguments'),
    'length': fields.Integer(description='number of packages found'),
    'packages': fields.Nested(pkg_find_pkgset_el_model,
                              description='package set packages information',
                              as_list=True
                              )
})

pkg_by_file_name_el_model = ns.model('PackageByFileNameElementModel', {
    'name': fields.String(description='package name'),
    'version': fields.String(description='package version'),
    'release': fields.String(description='package release'),
    'disttag': fields.String(description='package disttag'),
    'sha1': fields.String(attribute='pkgcs', description='package name'),
    'branch': fields.String(description='package set name'),
    'arch': fields.String(description='package arch'),
    'files': fields.List(fields.String, description='found files')
})
pkg_by_file_name_model = ns.model('PackageByFileNameModel', {
    'request_args': fields.Raw(description='request arguments'),
    'length': fields.Integer(description='number of packages found'),
    'packages': fields.Nested(pkg_by_file_name_el_model,
                              description='package set packages information',
                              as_list=True
                              )
})

dependent_packages_el_model = ns.model('DependentPackagesElementModel', {
    'name': fields.String(description='package name'),
    'version': fields.String(description='package version'),
    'release': fields.String(description='package release'),
    'epoch': fields.Integer(description='package epoch'),
    'serial': fields.Integer(description='package serial'),
    'sourcerpm': fields.String(description='source package file'),
    'branch': fields.String(description='package set name'),
    'archs': fields.List(fields.String, description='binary packages archs')
})
dependent_packages_model = ns.model('DependentPackagesModel', {
    'request_args': fields.Raw(description='request arguments'),
    'length': fields.Integer(description='number of packages found'),
    'packages': fields.Nested(dependent_packages_el_model,
                              description='dependent packages information',
                              as_list=True
                              )
})

unpackaged_dirs_args_el_model = ns.model('UnpackagedDirsElementModel', {
    'package': fields.String(description='package name'),
    'directory': fields.String(description='unpackaged directory'),
    'version': fields.String(description='package version'),
    'release': fields.String(description='package release'),
    'epoch': fields.Integer(description='package epoch'),
    'packager': fields.String(description='maintainer name'),
    'email': fields.String(description='maintainer email'),
    'archs': fields.List(fields.String, description='binary packages archs')
})
unpackaged_dirs_args_model = ns.model('UnpackagedDirsModel', {
    'request_args': fields.Raw(description='request arguments'),
    'length': fields.Integer(description='number of packages found'),
    'packages': fields.Nested(unpackaged_dirs_args_el_model,
                              description='packages with unpackaged directories',
                              as_list=True
                              )
})

build_dep_set_pkg_model = ns.model('BuildDependencySetPackageModel', {
    'name': fields.String(description='package name'),
    'version': fields.String(description='package version'),
    'release': fields.String(description='package release'),
    'epoch': fields.Integer(description='package epoch'),
    'archs': fields.List(fields.String, description='binary packages archs')
})
build_dep_set_pkgs_model = ns.model('BuildDependencySetPackagesModel', {
    'package': fields.String(description='source package name'),
    'length': fields.Integer(description='number of dependency packages found'),
    'depends': fields.Nested(build_dep_set_pkg_model,
                             description='build requirements packages information',
                             as_list=True
                             )
})
build_dep_set_model = ns.model('BuildDependencySetModel', {
    'request_args': fields.Raw(description='request arguments'),
    'length': fields.Integer(description='number of packages found'),
    'packages': fields.Nested(build_dep_set_pkgs_model,
                              description='build requirements packages information',
                              as_list=True
                              )
})

repocop_json_model = ns.model('RepocopJsonModel', {
    'pkg_name': fields.String(description='package name'),
    'pkg_version': fields.String(description='package version'),
    'pkg_release': fields.String(description='package release'),
    'pkg_arch': fields.String(description='package arch'),
    'rc_srcpkg_name': fields.String(description='source package name'),
    'rc_srcpkg_version': fields.String(description='source package version'),
    'rc_srcpkg_release': fields.String(description='source package version'),
    'rc_test_name': fields.String(description='repocop test name'),
    'rc_test_status': fields.String(description='repocop test status'),
    'rc_test_message': fields.String(description='repocop test message'),
    'rc_test_date': fields.DateTime(description='repocop test message'),
})
repocop_json_list_model = ns.model('RepocopJsonListModel', {
    'request_args': fields.Raw(description='request arguments'),
    'length': fields.Integer(description='number of packages found'),
    'packages': fields.Nested(repocop_json_model, description='repocop packages info', as_list=True)
})
