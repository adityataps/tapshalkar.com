import base64
import json
import os
import functions_framework
from google.api_core.client_options import ClientOptions
from google.cloud import storage, documentai

RESUME_FILENAME = "Resume_Aditya_Tapshalkar.pdf"
OUTPUT_FILENAME = "resume_parsed.md"

# Layout Parser block types → markdown prefix
_HEADING_PREFIX = {
    "heading_1": "# ",
    "heading_2": "## ",
    "heading_3": "### ",
}


def _blocks_to_markdown(blocks) -> str:
    """Convert Layout Parser document_layout blocks to markdown."""
    lines = []
    for block in blocks:
        tb = block.text_block
        if not tb or not tb.text.strip():
            continue
        block_type = tb.type_.lower() if tb.type_ else "paragraph"
        text = tb.text.strip()
        if block_type in _HEADING_PREFIX:
            lines.append(f"{_HEADING_PREFIX[block_type]}{text}")
        elif block_type == "unordered_list":
            for item in text.splitlines():
                item = item.strip()
                if item:
                    lines.append(f"- {item}")
        elif block_type == "ordered_list":
            for i, item in enumerate(text.splitlines(), 1):
                item = item.strip()
                if item:
                    lines.append(f"{i}. {item}")
        else:
            lines.append(text)
        lines.append("")  # blank line between blocks
    return "\n".join(lines).strip()


@functions_framework.cloud_event
def parse_resume(cloud_event):
    # Triggered via Pub/Sub topic — unwrap the GCS notification from the message
    raw = base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8")
    gcs_event = json.loads(raw)
    bucket_name = gcs_event["bucket"]
    file_name = gcs_event["name"]

    if file_name != RESUME_FILENAME:
        print(f"Ignoring {file_name}")
        return

    print(f"Parsing {file_name} from gs://{bucket_name}/")

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    pdf_bytes = bucket.blob(file_name).download_as_bytes()
    print(f"Downloaded {len(pdf_bytes)} bytes")

    processor_name = os.environ["DOCUMENT_AI_PROCESSOR_NAME"]
    location = processor_name.split("/")[3]
    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
    docai_client = documentai.DocumentProcessorServiceClient(client_options=opts)

    result = docai_client.process_document(
        request=documentai.ProcessRequest(
            name=processor_name,
            raw_document=documentai.RawDocument(
                content=pdf_bytes,
                mime_type="application/pdf",
            ),
        )
    )

    doc = result.document
    layout_blocks = doc.document_layout.blocks if doc.document_layout else []

    if layout_blocks:
        body = _blocks_to_markdown(layout_blocks)
        print(f"Converted {len(layout_blocks)} layout blocks to markdown")
    else:
        # Fallback: plain text from document
        body = doc.text
        print(f"No layout blocks — falling back to plain text ({len(body)} chars)")

    output = f"# Resume — Aditya Tapshalkar\n\n{body}"
    blob = bucket.blob(OUTPUT_FILENAME)
    blob.upload_from_string(output, content_type="text/plain; charset=utf-8")
    print(f"Wrote gs://{bucket_name}/{OUTPUT_FILENAME} ({len(output)} chars)")
