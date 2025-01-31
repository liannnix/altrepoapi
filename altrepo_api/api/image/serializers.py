# ALTRepo API
# Copyright (C) 2021-2025  BaseALT Ltd

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re
from flask_restx import fields

from .namespace import get_namespace

ns = get_namespace()

all_iso_element_model = ns.model(
    "ImageAllISOElementModel",
    {
        "branch": fields.String(description="ISO image base branch"),
        "name": fields.String(description="ISO image package set name"),
        "tag": fields.String(description="ISO image package set tag"),
        "file": fields.String(description="ISO image file name"),
        "date": fields.DateTime(description="ISO image package set date"),
        "uuid": fields.String(description="ISO image package set UUID"),
    },
)
all_iso_model = ns.model(
    "ImageAllISOModel",
    {
        "length": fields.Integer(description="number of ISO images"),
        "images": fields.Nested(
            all_iso_element_model,
            description="list of ISO images package sets information",
            as_list=True,
        ),
    },
)

image_info_comp_model = ns.model(
    "ImageInfoComponentModel",
    {
        "name": fields.String(description="Component name"),
        "size": fields.String(
            description="Component size (human readable)", attribute="image_size"
        ),
        "packages": fields.Integer(
            description="Component packages count", attribute="pkg_count"
        ),
        "uuid": fields.String(description="Component package set UUID"),
        "ruuid": fields.String(description="Component package set root UUID"),
        "kv": fields.Raw(description="Component metadata"),
    },
)
image_info_el_model = ns.model(
    "ImageInfoElementModel",
    {
        "date": fields.DateTime(description="Image package set date"),
        "uuid": fields.String(description="Image package set UUID"),
        "tag": fields.String(description="Image package set tag"),
        "branch": fields.String(description="Image base branch"),
        "edition": fields.String(description="Image edition"),
        "flavor": fields.String(description="Image flavor"),
        "platform": fields.String(description="Image platform"),
        "release": fields.String(description="Image release type"),
        "version_major": fields.Integer(description="Image version major"),
        "version_minor": fields.Integer(description="Image version minor"),
        "version_sub": fields.Integer(description="Image version sub"),
        "arch": fields.String(description="Image architecture"),
        "variant": fields.String(description="Image variant"),
        "type": fields.String(description="Image type"),
        "file": fields.String(description="Image file name"),
        "url": fields.List(fields.String(description="download URL")),
        "md5sum": fields.String(description="Image MD5 checksum"),
        "gost12sum": fields.String(description="Image GOST12 checksum"),
        "sha256sum": fields.String(description="Image SHA256 checksum"),
        "components": fields.Nested(
            image_info_comp_model,
            description="list of image components information",
            as_list=True,
        ),
    },
)
image_info_model = ns.model(
    "ImageInfoModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of images"),
        "images": fields.Nested(
            image_info_el_model,
            description="list of images information",
            as_list=True,
        ),
    },
)

pkg_inspect_el1_model = ns.model(
    "ImagePackagesElement1Model",
    {
        "hash": fields.String(description="package hash UInt64 as string"),
        "arch": fields.String(description="package architecture"),
        "name": fields.String(description="package name"),
        "epoch": fields.Integer(description="package epoch"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "disttag": fields.String(description="package disttag"),
        "buildtime": fields.Integer(description="package build time"),
    },
)
pkg_inspect_el2_model = ns.inherit(
    "ImagePackagesElement2Model",
    pkg_inspect_el1_model,
    {
        "task_id": fields.Integer(description="build task id"),
        "subtask_id": fields.Integer(description="build task subtask id"),
    },
)
pkg_inspect_regular_model = ns.model(
    "ImagePackagesInspectRegularModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "input_pakages": fields.Integer(description="number of input packages"),
        "not_in_branch": fields.Integer(
            description="number of packages not found in branch"
        ),
        "found_in_tasks": fields.Integer(
            description="number of packages found in build tasks"
        ),
        "not_found_in_db": fields.Integer(
            description="number of packages not found in database"
        ),
        "packages_in_tasks": fields.Nested(
            pkg_inspect_el2_model,
            description="list of packages that not in branch but found in build tasks",
            as_list=True,
        ),
        "packages_not_in_db": fields.Nested(
            pkg_inspect_el1_model,
            description="list of packages that not found in database",
            as_list=True,
        ),
    },
)

pkg_inspect_sp_pkg_model = ns.model(
    "ImagePackagesInspectSPPackageModel",
    {
        "found_in": fields.String(
            description="package found in [branch|task|last branch]"
        ),
        "version_check": fields.String(
            description="package version compared with last branch state"
        ),
        "image": fields.Nested(
            pkg_inspect_el1_model,
            description="package from image",
        ),
        "database": fields.Nested(
            pkg_inspect_el1_model,
            description="matching package found in database by NEVRDA",
        ),
        "last_branch": fields.Nested(
            pkg_inspect_el1_model,
            description="package matched from last branch state by NA",
        ),
    },
)
pkg_inspect_sp_model = ns.model(
    "ImagePackagesInspectSPModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "input_pakages": fields.Integer(description="number of input packages"),
        "in_branch": fields.Integer(description="number of packages found in branch"),
        "not_in_branch": fields.Integer(
            description="number of packages not found in branch"
        ),
        "found_in_tasks": fields.Integer(
            description="number of packages found in build tasks"
        ),
        "not_found_in_db": fields.Integer(
            description="number of packages not found in database"
        ),
        "packages": fields.Nested(
            pkg_inspect_sp_pkg_model,
            description="list of packages with inspection results",
            as_list=True,
        ),
    },
)

# regex patterns for JSON validation
hash_str_match = re.compile(r"^[0-9]{18,20}$")  # package hash string
arch_match = re.compile(r"^[a-z0-9\-\_]{3,}$")  # type: ignore
name_match = re.compile(r"^[\w\.\+\-]{2,}$")  # type: ignore # ref __pkg_name_match
description_match = re.compile(r"|^[a-zA-Z0-9+/]+={0,3}$")
url_match = re.compile(r'(|^https?://[^"\s<>]+\w)')
branch_match = re.compile(r"^[a-zA-Z0-9+/ _]+")
name_bugzilla_match = re.compile(r"|^[a-zA-Z0-9+/ _]+")
show_match = re.compile(r"^(hide|show)$")
version_match = re.compile(r"^[\w\.\+]+$")  # type: ignore # ref __pkg_VR_match
release_match = re.compile(r"^[\w\.\+]+$")  # type: ignore # ref __pkg_VR_match
disttag_match = re.compile(r"^$|^[a-z0-9\+\.]+$")  # type: ignore # empty string allowed
img_tag_match = re.compile(
    r"(^[a-z0-9\_]+):([\w\.\+\-]{2,}):(|[\w\.\+\-]{2,}):(|[[a-z0-9\+\_\.\-]+):([a-z0-9\+\_\.\-]+):([a-z0-9\-\_]{3,}):([a-z0-9\_\+\-\.]+):([a-z0-9\_\+\-\.]+)$"
)

pkgs_json_el_model = ns.model(
    "ImagePackagesJSONElementModel",
    {
        "pkg_hash": fields.String(
            required=True,
            description="package hash",
            pattern=hash_str_match.pattern,
            example="2758010506349322063",
        ),
        "pkg_name": fields.String(
            required=True,
            description="package name",
            example="curl",
            pattern=name_match.pattern,
        ),
        "pkg_epoch": fields.Integer(
            required=True, description="package epoch", example=0
        ),
        "pkg_version": fields.String(
            required=True,
            description="package version",
            example="1.0",
            pattern=version_match.pattern,
        ),
        "pkg_release": fields.String(
            required=True,
            description="package release",
            example="alt1",
            pattern=release_match.pattern,
        ),
        "pkg_arch": fields.String(
            required=True,
            description="package architecture",
            example="i586",
            pattern=arch_match.pattern,
        ),
        "pkg_disttag": fields.String(
            required=True,
            description="package disttag",
            example="sisyphus+275725.100.1.1",
            pattern=disttag_match.pattern,
        ),
        "pkg_buildtime": fields.Integer(
            required=True, description="package buildtime", example=1626030376
        ),
    },
)
pkgs_json_model = ns.model(
    "ImagePackagesJSONModel",
    {
        "branch": fields.String(
            required=True, description="image base branch", example="p10"
        ),
        "packages": fields.Nested(
            pkgs_json_el_model,
            required=True,
            description="list of packages",
            as_list=True,
        ),
    },
)

img_json_el_model = ns.model(
    "ImageJSONElementModel",
    {
        "img_edition": fields.String(
            required=True,
            description="ISO image edition",
            example="alt-kworkstation",
            pattern=name_match.pattern,
        ),
        "img_name": fields.String(
            required=True,
            description="ISO image name",
            example="ALT-KWORKSTATION 9.2 x86_64",
        ),
        "img_show": fields.String(
            required=True,
            description="hide - hide image, show - show image",
            example="hide",
            pattern=show_match.pattern,
        ),
        "img_summary_ru": fields.String(
            description="image summary in Russian", example="Image summary in Russian"
        ),
        "img_summary_en": fields.String(
            description="image summary in English", example="Image summary in English"
        ),
        "img_start_date": fields.DateTime(
            required=True, description="support start date"
        ),
        "img_end_date": fields.DateTime(required=True, description="support end date"),
        "img_mailing_list": fields.String(
            description="link to mailing list",
            example="https://lists.altlinux.org/mailman/listinfo/devel-ports",
            pattern=url_match.pattern,
        ),
        "img_name_bugzilla": fields.String(
            description="image name for bugzilla",
            example="p10",
            pattern=name_bugzilla_match.pattern,
        ),
        "img_json": fields.Raw(
            required=True,
            description="image mirror's auxilary info as JSON substructure",
            example="{}",
        ),
    },
)
img_json_model = ns.model(
    "ImageJSONModel",
    {
        "img_branch": fields.String(
            required=True, description="image base branch", example="p10"
        ),
        "img_description_ru": fields.String(
            description="html description in Russian in Base64 format",
            example="0YLQtdGB0YLQvtCy0L7QtSDQvtC/0LjRgdCw0L3QuNC1",
            pattern=description_match.pattern,
        ),
        "img_description_en": fields.String(
            description="html description in English in Base64 format",
            example="dGVzdCBkZXNjcmlwdGlvbg==",
            pattern=description_match.pattern,
        ),
        "images": fields.Nested(
            img_json_el_model,
            description="image info",
            as_list=True,
        ),
    },
)

image_status_get_el_model = ns.model(
    "ImageStatusGetElementModel",
    {
        "branch": fields.String(description="ISO image base branch"),
        "edition": fields.String(description="ISO image edition"),
        "name": fields.String(description="ISO image name"),
        "show": fields.String(description="hide - hide image, show - show image"),
        "start_date": fields.DateTime(description="support start date"),
        "end_date": fields.DateTime(description="support end date"),
        "summary_ru": fields.String(description="image summary in Russian"),
        "summary_en": fields.String(
            description="image summary in English", example="Image summary in English"
        ),
        "description_ru": fields.String(
            description="html description in Russian in Base64 format"
        ),
        "description_en": fields.String(
            description="html description in English in Base64 format"
        ),
        "mailing_list": fields.String(description="link to mailing list"),
        "name_bugzilla": fields.String(description="image name for bugzilla"),
        "json": fields.Raw(
            description="image mirror's auxilary info as JSON substructure"
        ),
    },
)
image_status_get_model = ns.model(
    "ImageStatusGetModel",
    {
        "images": fields.Nested(
            image_status_get_el_model, description="image info", as_list=True
        )
    },
)

img_tag_json_el_model = ns.model(
    "ImageTagJSONElementModel",
    {
        "img_tag": fields.String(
            required=True,
            description="ISO image package set tag",
            example="branch:edition:flavor:platform:release.ver_major.ver_minor.ver_sub:arch:variant:type",
            pattern=img_tag_match.pattern,
        ),
        "img_show": fields.String(
            required=True,
            description="hide - hide image, show - show image",
            example="hide",
            pattern=show_match.pattern,
        ),
    },
)
img_tag_json_model = ns.model(
    "ImageTagJSONModel",
    {
        "tags": fields.Nested(
            img_tag_json_el_model,
            description="iso image info",
            as_list=True,
        ),
    },
)

img_tag_status_get_el_model = ns.model(
    "ImageTagStatusGetElementModel",
    {
        "tag": fields.String(description="ISO image package set tag"),
        "show": fields.String(description="hide - hide image, show - show image"),
    },
)
img_tag_status_get_model = ns.model(
    "ImageTagStatusGetModel",
    {
        "tags": fields.Nested(
            img_tag_status_get_el_model, description="image info", as_list=True
        )
    },
)

packages_image_el_model = ns.model(
    "ImagePackagesElementModel",
    {
        "hash": fields.String(description="package hash UInt64 as string"),
        "name": fields.String(attribute="pkg_name", description="package name"),
        "version": fields.String(
            attribute="pkg_version", description="package version"
        ),
        "release": fields.String(
            attribute="pkg_release", description="package release"
        ),
        "arch": fields.String(attribute="pkg_arch", description="package architecture"),
        "summary": fields.String(
            attribute="pkg_summary", description="package summary"
        ),
        "buildtime": fields.Integer(
            attribute="pkg_buildtime", description="last binary package buildtime"
        ),
        "changelog_text": fields.String(description="package last changelog message"),
    },
)
packages_image_model = ns.model(
    "ImagePackagesModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "subcategories": fields.List(
            fields.String, description="list of subcategories"
        ),
        "packages": fields.Nested(
            packages_image_el_model,
            description="last packages list",
            as_list=True,
        ),
    },
)

last_packages_img_el_model = ns.model(
    "LastImagePackagesElementModel",
    {
        "task_id": fields.String(description="task id"),
        "task_changed": fields.DateTime(description="task changed date"),
        "tplan_action": fields.String(description="task type [add|delete]"),
        "branch": fields.String(description="package set name"),
        "hash": fields.String(
            attribute="pkg_hash",
            description="package hash UInt64 as string in the repository",
        ),
        "name": fields.String(attribute="pkg_name", description="package name"),
        "version": fields.String(
            attribute="pkg_version", description="package version in the repository"
        ),
        "release": fields.String(
            attribute="pkg_release", description="package release in the repository"
        ),
        "arch": fields.String(
            attribute="pkg_arch", description="package architecture in the repository"
        ),
        "img_hash": fields.String(
            attribute="img_pkg_hash",
            description="package hash UInt64 as string in the image",
        ),
        "img_version": fields.String(
            attribute="img_pkg_version", description="package version in the image"
        ),
        "img_release": fields.String(
            attribute="img_pkg_release", description="package release in the image"
        ),
        "summary": fields.String(
            attribute="pkg_summary", description="package summary"
        ),
        "chlog_name": fields.String(description="package last changelog name"),
        "chlog_nick": fields.String(description="maintainer nickname in the changelog"),
        "chlog_date": fields.DateTime(
            description="package last changelog message date"
        ),
        "chlog_text": fields.String(description="package last changelog message"),
    },
)
last_packages_image_model = ns.model(
    "LastImagePackagesModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "packages": fields.Nested(
            last_packages_img_el_model,
            description="last packages list",
            as_list=True,
        ),
    },
)

image_tag_uuid_model = ns.model(
    "ImageTagUUIDModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "uuid": fields.String(description="Image package set UUID"),
        "file": fields.String(description="ISO image file name"),
        "type": fields.String(description="Image type"),
        "components": fields.Raw(description="List of components for given tag"),
    },
)

image_category_model = ns.model(
    "SiteImageCategoryElementModel",
    {
        "category": fields.String(description="package category"),
        "count": fields.Integer(description="number of packages in category"),
    },
)
image_categories_model = ns.model(
    "SiteImageCategoriesModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of categories in list"),
        "categories": fields.Nested(
            image_category_model, description="found categories", as_list=True
        ),
    },
)

active_images_el_model = ns.model(
    "ActiveImagesElementModel",
    {
        "edition": fields.String(description="ISO image edition"),
        "tags": fields.List(
            fields.String, as_list=True, description="active tags list"
        ),
    },
)
active_images_model = ns.model(
    "ActiveImagesModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of images found"),
        "images": fields.Nested(
            active_images_el_model,
            description="active images list",
            as_list=True,
        ),
    },
)

find_images_by_pkg_el_model = ns.model(
    "FindImagesByPackageElementModel",
    {
        "pkghash": fields.String(description="package hash UInt64 as string"),
        "name": fields.String(description="package name"),
        "branch": fields.String(description="package set name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "arch": fields.String(description="package architecture"),
        "edition": fields.String(description="Image edition"),
        "tag": fields.String(description="Image package set tag"),
        "file": fields.String(description="Image file name"),
        "date": fields.DateTime(description="Image package set date"),
    },
)
find_images_by_pkg_model = ns.model(
    "FindImagesByPackageModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of images found"),
        "images": fields.Nested(
            find_images_by_pkg_el_model,
            description="list of found images",
            as_list=True,
        ),
    },
)

image_packageset_model = ns.model(
    "ImagePackageSetModel",
    {
        "length": fields.Integer(description="number of packagesets found"),
        "branches": fields.List(fields.String, description="list of packagesets"),
    },
)
