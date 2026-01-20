# ALTRepo API
# Copyright (C) 2021-2026  BaseALT Ltd

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

from dataclasses import asdict, dataclass, field
from enum import Enum
from logging import Logger
from typing import Any

from flask import g
from flask_restx import Model, Namespace, OrderedModel, Resource, fields

from .auth.decorators import token_required
from .base import GET_RESPONSES_404, APIWorker, run_worker
from ..utils import url_logging


class KnownFilterTypes(str, Enum):
    """
    Enum class representing known filter types for metadata.
    """

    AUTOCOMPLETE = "autocomplete"
    STRING = "string"
    NUMBER = "number"
    CHOICE = "choice"
    MULTIPLE_CHOICE = "multiple_choice"
    NESTED_CHOICE = "nested_choice"
    DATE = "date"
    DATE_RANGE = "date_range"
    BOOLEAN = "boolean"


@dataclass
class MetadataChoiceItem:
    value: str
    display_name: str
    name: str | None = None
    label: str | None = None
    help_text: str | None = None
    choices: list["MetadataChoiceItem"] | None = None


@dataclass
class MetadataAutocompleteItem:
    endpoint: str
    data_path: str
    search_param: str | None = None
    pagination: bool | None = False


@dataclass
class MetadataItem:
    name: str
    label: str
    help_text: str
    type: KnownFilterTypes
    choices: list[MetadataChoiceItem] = field(default_factory=list)
    autocomplete: MetadataAutocompleteItem | None = None

    def asdict(self) -> dict[str, Any]:
        res = asdict(self)
        res["type"] = self.type.value
        return res


def _build_serializer(ns: Namespace) -> Model | OrderedModel:
    """
    Constructs the serializer model for metadata responses.
    """
    metadata_choice_model = ns.model(
        "MetadataChoiceModel",
        {
            "value": fields.String(
                description="the actual value of the choice", required=True
            ),
            "display_name": fields.String(
                description="the human-readable display name for the choice",
                required=True,
            ),
            "name": fields.String(
                description="Parameter name (if different from parent`s)",
                required=False,
            ),
            "label": fields.String(
                description="the user-friendly label for the field (if different from parent`s)",
                required=False,
            ),
            "help_text": fields.String(
                description="help text or description explaining the field (if different from parent`s)",
                required=False,
            ),
        },
    )
    metadata_choice_model["choices"] = fields.List(
        fields.Nested(metadata_choice_model),
        required=False,
        description="Nested choice item",
    )

    metadata_autocomplete_model = ns.model(
        "MetadataDynamicChoiceModel",
        {
            "endpoint": fields.String(
                description="API endpoint to fetch choices from",
                required=True,
            ),
            "data_path": fields.String(
                description="JSONPath-like path to data in response", required=True
            ),
            "search_param": fields.String(
                description="Query parameter name for search text"
            ),
            "pagination": fields.Boolean(
                description="Whether the endpoint supports pagination",
                default=False,
            ),
        },
    )
    metadata_item_model = ns.model(
        "MetadataItemModel",
        {
            "name": fields.String(
                description="the technical name/identifier of the field", required=True
            ),
            "label": fields.String(
                description="the user-friendly label for the field", required=True
            ),
            "help_text": fields.String(
                description="help text or description explaining the field",
                required=True,
            ),
            "type": fields.String(
                description="data type of the field (e.g., string, number, date)",
                enum=[tp for tp in KnownFilterTypes],
                required=True,
            ),
            "choices": fields.Nested(
                metadata_choice_model,
                description=(
                    "list of available options for fields with predefined choices"
                ),
                as_list=True,
            ),
            "autocomplete": fields.Nested(
                metadata_autocomplete_model,
                description="Configuration for autocomplete filter",
            ),
        },
    )
    metadata_response_model = ns.model(
        "metadataResponseModel",
        {
            "length": fields.Integer(
                description="total number of metadata items in the response",
                required=True,
            ),
            "metadata": fields.Nested(
                metadata_item_model,
                description="array of metadata field definitions",
                as_list=True,
                required=True,
            ),
        },
    )
    return metadata_response_model


def with_metadata(
    worker: type[APIWorker],
    ns: Namespace,
    logger: Logger,
    *,
    require_auth: bool = False,
):
    """
    Decorator factory that adds a metadata endpoint to a resource.

    The decorated resource will gain a new endpoint at `/metadata` that returns
    information about available filters and their properties.
    """
    metadata_model = _build_serializer(ns)

    class MetadataResource(Resource):
        """
        Resource for serving metadata with authentication requirement.
        """

        @ns.marshal_with(metadata_model)
        @token_required("", validate_role=False)
        def get(self):
            url_logging(logger, f"{g.url}/metadata")
            w = worker(g.connection)  # pyright: ignore[reportCallIssue]
            return run_worker(
                worker=w, run_method=w.metadata, check_method=lambda: True, args=None
            )

    class MetadataResourceNoAuth(Resource):
        """
        Resource for serving metadata without authentication.
        """

        @ns.marshal_with(metadata_model)
        def get(self):
            url_logging(logger, f"{g.url}/metadata")
            w = worker(g.connection)  # pyright: ignore[reportCallIssue]
            return run_worker(
                worker=w, run_method=w.metadata, check_method=lambda: True, args=None
            )

    def decorator(cls: Resource) -> Resource:
        """
        Attaches the metadata endpoint to the target resource class.
        """

        # only proceed if the class has a GET method
        if not hasattr(cls, "get"):
            return cls

        # find the original route and add metadata endpoint
        for resource in ns.resources:
            if resource.resource == cls:
                original_route = resource.urls[0]
                meta_cls = MetadataResource if require_auth else MetadataResourceNoAuth

                operation_id = (
                    f"get_{original_route.lstrip('/').replace('/', '_')}_metadata"
                )

                ns.doc(
                    id=operation_id,
                    description="Retrieve metadata describing all available filters",
                    responses=GET_RESPONSES_404,
                    security="Bearer" if require_auth else None,
                )(meta_cls.get)

                ns.route(
                    f"{original_route}/metadata",
                )(meta_cls)
                break

        return cls

    return decorator
