# ALTRepo API
# Copyright (C) 2021-2023  BaseALT Ltd

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

from altrepo_api.api.misc import lut


BDU_ID_TYPE = "BDU"
BDU_ID_PREFIX = f"{BDU_ID_TYPE}:"
CVE_ID_TYPE = "CVE"
CVE_ID_PREFIX = f"{CVE_ID_TYPE}-"

ERRATA_PACKAGE_UPDATE_PREFIX = f"{lut.errata_package_update_prefix}-"
ERRATA_BRANCH_BULLETIN_PREFIX = f"{lut.errata_branch_update_prefix}-"
ERRATA_CHNAGE_PREFIX = f"{lut.errata_change_prefix}-"
