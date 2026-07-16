from typing import Any

from growthos.main import app

_DEFAULT_RESPONSES = frozenset({"200", "422"})


def test_content_paths_methods_and_operation_ids_remain_stable() -> None:
    expected = {
        ("/api/v1/contents", "get"): (
            "list_contents_api_v1_contents_get",
            _DEFAULT_RESPONSES,
        ),
        ("/api/v1/contents/generate", "post"): (
            "generate_content_api_v1_contents_generate_post",
            frozenset({"201", "422"}),
        ),
        ("/api/v1/contents/{content_id}", "get"): (
            "get_content_api_v1_contents__content_id__get",
            _DEFAULT_RESPONSES,
        ),
        ("/api/v1/contents/{content_id}/submit-internal", "post"): (
            "submit_internal_api_v1_contents__content_id__submit_internal_post",
            _DEFAULT_RESPONSES,
        ),
        ("/api/v1/contents/{content_id}/send-to-client", "post"): (
            "send_to_client_api_v1_contents__content_id__send_to_client_post",
            _DEFAULT_RESPONSES,
        ),
        ("/api/v1/contents/{content_id}/decisions/{component}/approve", "post"): (
            "approve_content_component_api_v1_contents__content_id__decisions__component__approve_post",
            _DEFAULT_RESPONSES,
        ),
        (
            "/api/v1/contents/{content_id}/decisions/{component}/request-changes",
            "post",
        ): (
            "request_content_component_changes_api_v1_contents__content_id__decisions__component__request_changes_post",
            _DEFAULT_RESPONSES,
        ),
        ("/api/v1/contents/{content_id}/revisions", "post"): (
            "create_revision_api_v1_contents__content_id__revisions_post",
            _DEFAULT_RESPONSES,
        ),
        ("/api/v1/contents/{content_id}/visual-revisions", "post"): (
            "create_visual_revision_api_v1_contents__content_id__visual_revisions_post",
            _DEFAULT_RESPONSES,
        ),
        ("/api/v1/contents/{content_id}/publication", "post"): (
            "record_manual_publication_api_v1_contents__content_id__publication_post",
            _DEFAULT_RESPONSES,
        ),
    }
    actual: dict[tuple[str, str], tuple[str, frozenset[str]]] = {}
    for path, path_item in app.openapi()["paths"].items():
        if not path.startswith("/api/v1/contents"):
            continue
        for method, operation in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            operation_data: dict[str, Any] = operation
            actual[(path, method)] = (
                operation_data["operationId"],
                frozenset(operation_data["responses"]),
            )

    assert actual == expected
