import base64
import json
import os
import functions_framework
from google.api_core.client_options import ClientOptions
from google.cloud import storage, documentai

RESUME_FILENAME = "Resume_Aditya_Tapshalkar.pdf"
OUTPUT_FILENAME = "resume_parsed.md"


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

    processor_name = os.environ["DOCUMENT_AI_PROCESSOR_NAME"]
    parts = processor_name.split("/")
    if len(parts) != 6 or parts[0] != "projects" or parts[2] != "locations" or parts[4] != "processors":
        raise ValueError(
            f"DOCUMENT_AI_PROCESSOR_NAME has unexpected format: {processor_name!r}\n"
            "Expected: projects/PROJECT/locations/LOCATION/processors/PROCESSOR_ID"
        )

    location = parts[3]
    print(f"Parsing gs://{bucket_name}/{file_name} with processor {processor_name}")

    storage_client = storage.Client()
    pdf_bytes = storage_client.bucket(bucket_name).blob(file_name).download_as_bytes()
    print(f"Downloaded {len(pdf_bytes)} bytes")

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

    text = result.document.text
    print(f"Extracted {len(text)} chars")

    output = f"# Resume — Aditya Tapshalkar\n\n{text}"
    storage_client.bucket(bucket_name).blob(OUTPUT_FILENAME).upload_from_string(
        output, content_type="text/plain; charset=utf-8"
    )
    print(f"Wrote gs://{bucket_name}/{OUTPUT_FILENAME} ({len(output)} chars)")
