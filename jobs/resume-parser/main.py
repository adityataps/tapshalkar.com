import os
import functions_framework
from google.api_core.client_options import ClientOptions
from google.cloud import storage, documentai

RESUME_FILENAME = "Resume_Aditya_Tapshalkar.pdf"
OUTPUT_FILENAME = "resume_parsed.md"


@functions_framework.cloud_event
def parse_resume(cloud_event):
    data = cloud_event.data
    bucket_name = data["bucket"]
    file_name = data["name"]

    if file_name != RESUME_FILENAME:
        print(f"Ignoring {file_name}")
        return

    print(f"Parsing {file_name} from gs://{bucket_name}/")

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    pdf_bytes = bucket.blob(file_name).download_as_bytes()
    print(f"Downloaded {len(pdf_bytes)} bytes")

    processor_name = os.environ["DOCUMENT_AI_PROCESSOR_NAME"]
    # Processor name: projects/.../locations/{location}/processors/...
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

    text = result.document.text
    print(f"Extracted {len(text)} chars from Document AI")

    output = f"# Resume — Aditya Tapshalkar\n\n{text}"
    blob = bucket.blob(OUTPUT_FILENAME)
    blob.upload_from_string(output, content_type="text/plain; charset=utf-8")
    print(f"Wrote gs://{bucket_name}/{OUTPUT_FILENAME} ({len(output)} chars)")
