# ALTRepo API
# Copyright (C) 2021  BaseALT Ltd

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

iso_image_comp_model = ns.model(
    "ISOImageComponentModel",
    {
        "name": fields.String(description="ISO component name"),
        "size": fields.String(
            description="ISO component size (human readable)", attribute="image_size"
        ),
        "packages": fields.Integer(
            description="ISO component packages count", attribute="pkg_count"
        ),
        "uuid": fields.String(description="ISO component package set UUID"),
        "ruuid": fields.String(description="ISO component package set root UUID"),
        "kv": fields.Raw(description="ISO component metadata"),
    },
)
iso_image_el_model = ns.model(
    "ISOImageElementModel",
    {
        "date": fields.DateTime(description="ISO image package set date"),
        "uuid": fields.String(description="ISO image package set UUID"),
        "tag": fields.String(description="ISO image package set tag"),
        "branch": fields.String(description="ISO image base branch"),
        "edition": fields.String(description="ISO image edition"),
        "flavor": fields.String(description="ISO image flavor"),
        "platform": fields.String(description="ISO image platform"),
        "release": fields.String(description="ISO image release type"),
        "version_major": fields.Integer(description="ISO image version major"),
        "version_minor": fields.Integer(description="ISO image version minor"),
        "version_sub": fields.Integer(description="ISO image version sub"),
        "arch": fields.String(description="ISO image architecture"),
        "variant": fields.String(description="ISO image variant"),
        "type": fields.String(description="Image type"),
        "file": fields.String(description="ISO image file name"),
        "url": fields.List(fields.String(description="download URL")),
        "md5sum": fields.String(description="Image MD5 checksum"),
        "gost12sum": fields.String(description="Image GOST12 checksum"),
        "sha256sum": fields.String(description="Image SHA256 checksum"),
        "components": fields.Nested(
            iso_image_comp_model,
            description="list of ISO image components information",
            as_list=True,
        ),
    },
)
iso_image_model = ns.model(
    "ISOImageModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of ISO images"),
        "images": fields.Nested(
            iso_image_el_model,
            description="list of ISO images information",
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
    }
)
pkg_inspect_el2_model = ns.inherit(
    "ImagePackagesElement2Model",
    pkg_inspect_el1_model,
    {
        "task_id": fields.Integer(description="build task id"),
        "subtask_id": fields.Integer(description="build task subtask id"),
    }
)
pkg_inspect_regular_model = ns.model(
    "ImagePackagesInspectRegularModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "input_pakages": fields.Integer(description="number of input packages"),
        "not_in_branch": fields.Integer(description="number of packages not found in branch"),
        "found_in_tasks": fields.Integer(description="number of packages found in build tasks"),
        "not_found_in_db": fields.Integer(description="number of packages not found in database"),
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
    }
)

pkg_inspect_sp_pkg_model = ns.model(
    "ImagePackagesInspectSPPackageModel",
    {
        "found_in": fields.String(description="package found in [branch|task|last branch]"),
        "version_check": fields.String(description="package version compared with last branch state"),
        "image": fields.Nested(
            pkg_inspect_el1_model, description="package from image",
        ),
        "database": fields.Nested(
            pkg_inspect_el1_model,
            description="matching package found in database by NEVRDA",
        ),
        "last_branch": fields.Nested(
            pkg_inspect_el1_model,
            description="package matched from last branch state by NA",
        )
    }
)
pkg_inspect_sp_model = ns.model(
    "ImagePackagesInspectSPModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "input_pakages": fields.Integer(description="number of input packages"),
        "in_branch": fields.Integer(description="number of packages found in branch"),
        "not_in_branch": fields.Integer(description="number of packages not found in branch"),
        "found_in_tasks": fields.Integer(description="number of packages found in build tasks"),
        "not_found_in_db": fields.Integer(description="number of packages not found in database"),
        "packages": fields.Nested(
            pkg_inspect_sp_pkg_model,
            description="list of packages with inspection results",
            as_list=True,
        ),
    }
)

# regex patterns for JSON validation
hash_str_match = re.compile("^[0-9]{18,20}$")  # package hash string
arch_match = re.compile("^[a-z0-9\-\_]{3,}$")  # type: ignore
name_match = re.compile("^[\w\.\+\-]{2,}$")  # type: ignore # ref __pkg_name_match
version_match = re.compile("^[\w\.\+]+$")  # type: ignore # ref __pkg_VR_match
release_match = re.compile("^[\w\.\+]+$")  # type: ignore # ref __pkg_VR_match
disttag_match = re.compile("^$|^[a-z0-9\+\.]+$")  # type: ignore # empty string allowed

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
        "branch": fields.String(required=True, description="image base branch", example="p10"),
        "packages": fields.Nested(
            pkgs_json_el_model,
            description="list of packages",
            as_list=True,
        ),
    },
)
