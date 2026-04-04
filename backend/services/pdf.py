from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TableStructureOptions,
    TableFormerMode,
)
from logger import logger


def extract_markdown(file_path: str) -> str:
    """
    Convert a PDF file to markdown using Docling.
    Returns the markdown string, or raises on failure.
    """
    logger.info(f"[PDF] Converting {file_path} to markdown")

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False  # Bank statements have native text, no OCR needed
    pipeline_options.do_table_structure = True  # Enable table structure recognition
    pipeline_options.table_structure_options = TableStructureOptions(
        do_cell_matching=True,       # Align predicted structure with actual PDF text
        mode=TableFormerMode.ACCURATE,  # Full model; slower but handles irregular layouts
    )

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    result = converter.convert(file_path)
    markdown = result.document.export_to_markdown()

    logger.info(f"[PDF] Conversion complete ({len(markdown)} chars)")

    # Save markdown alongside the PDF for offline debugging / re-runs
    md_path = file_path + ".md"
    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown)
        logger.info(f"[PDF] Saved markdown to {md_path}")
    except Exception as e:
        logger.warning(f"[PDF] Could not save markdown file: {e}")

    return markdown
