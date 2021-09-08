from flask_restx import fields

from api.packageset.packageset import ns

pkgset_compare_pkg_model = ns.model(
    "PackagesetComparePackageModel",
    {
        "name": fields.String(description="package name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
    },
)
pkgset_compare_el_model = ns.model(
    "PackagesetCompareElementModel",
    {
        "pkgset1": fields.String(description="packageset #1 name"),
        "pkgset2": fields.String(description="packageset #2 name"),
        "package1": fields.Nested(
            pkgset_compare_pkg_model, description="package from packageset #1"
        ),
        "package2": fields.Nested(
            pkgset_compare_pkg_model, description="package from packageset #2"
        ),
    },
)
pkgset_compare_model = ns.model(
    "PackagesetCompareModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "packages": fields.Nested(
            pkgset_compare_el_model,
            description="unpackaged directories information",
            as_list=True,
        ),
    },
)

pkgset_packages_el_model = ns.model(
    "PackagesetPackagesElementModel",
    {
        "name": fields.String(description="package name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "summary": fields.String(description="package summary"),
        "url": fields.String(description="package url"),
        "license": fields.String(description="package license"),
        "category": fields.String(description="package category"),
        "maintainers": fields.List(fields.String, description="package maintainers"),
        "acl_list": fields.List(fields.String, description="package ACL list"),
        "archs": fields.List(fields.String, description="package archs"),
    },
)
pkgset_packages_model = ns.model(
    "PackagesetPackagesModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "packages": fields.Nested(
            pkgset_packages_el_model,
            description="unpackaged directories information",
            as_list=True,
        ),
    },
)

pkgset_status_post_el_model = ns.model(
    "PackageSetPostElementModel",
    {
        "pkgset_name": fields.String(description="package set name"),
        "rs_start_date": fields.DateTime(description="support start date"),
        "rs_end_date": fields.DateTime(description="support end date"),
        "rs_show": fields.Integer(description="0 - hide branch, 1 - show branch"),
        "rs_description_ru": fields.String(description="html description in Russian in Base64 format"),
        "rs_description_en": fields.String(description="html description in English in Base64 format")
    }
)
pkgset_status_post_model = ns.model(
    "PackageSetPostModel",
    {
        "branches": fields.Nested(
            pkgset_status_post_el_model, description="package set info", as_list=True
        )
    },
)

pkgset_status_get_el_model = ns.model(
    "PackageSetGetElementModel",
    {
        "branch": fields.String(description="package set name"),
        "start_date": fields.DateTime(description="support start date"),
        "end_date": fields.DateTime(description="support end date"),
        "show": fields.Integer(description="0 - hide branch, 1 - show branch"),
        "description_ru": fields.String(description="html description in Russian"),
        "description_en": fields.String(description="html description in English")
    }
)
pkgset_status_get_model = ns.model(
    "PackageSetGetModel",
    {
        "branches": fields.Nested(
            pkgset_status_get_el_model, description="package set info", as_list=True
        )
    },
)