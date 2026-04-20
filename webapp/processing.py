"""PDF processing logic — no Streamlit dependencies."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from monopoly.banks import BankDetector, banks
from monopoly.generic import GenericBank
from monopoly.pdf import MissingOCRError, PdfDocument, PdfParser
from monopoly.pipeline import Pipeline
from monopoly.statements.base import SafetyCheckError
from pydantic import SecretStr

from webapp.models import ProcessedFile, TransactionMetadata


@dataclass
class ProcessingWarning:
    level: str  # "info" | "warning" | "error"
    message: str


@dataclass
class ProcessingResult:
    file: ProcessedFile
    warnings: list[ProcessingWarning] = field(default_factory=list)


def _build_pipeline(document: PdfDocument, password: str | None = None) -> tuple[Pipeline, PdfParser]:
    analyzer = BankDetector(document)
    bank = analyzer.detect_bank(banks) or GenericBank
    parser = PdfParser(bank, document)
    passwords = [SecretStr(password)] if password else []
    pipeline = Pipeline(parser, passwords=passwords)
    return pipeline, parser


def process_pdf(
    document: PdfDocument,
    password: str | None = None,
    on_warning: Callable[[str, str], None] | None = None,
) -> ProcessingResult:
    """Parse a PDF bank statement without any Streamlit dependencies."""
    warnings: list[ProcessingWarning] = []

    def warn(level: str, msg: str) -> None:
        warnings.append(ProcessingWarning(level=level, message=msg))
        if on_warning:
            on_warning(level, msg)

    try:
        pipeline, parser = _build_pipeline(document, password)
    except MissingOCRError:
        warn("info", f"No text layer in {document.name} — applying OCR.")
        analyzer = BankDetector(document)
        bank = analyzer.detect_bank(banks) or GenericBank
        if cropbox := bank.pdf_config.page_bbox:
            for page in document:
                page.set_cropbox(cropbox)
        document = PdfParser.apply_ocr(document)
        pipeline, parser = _build_pipeline(document, password)

    statement = pipeline.extract(safety_check=False)
    bank_name = parser.bank.__name__

    if statement.config.safety_check:
        try:
            statement.perform_safety_check()
        except SafetyCheckError:
            warn("error", f"Safety check failed for {document.name} — transactions may be incomplete.")

    if not statement.config.safety_check:
        warn("warning", f"{bank_name} has no safety check — review transactions carefully.")

    if bank_name == "GenericBank":
        warn("warning", "Unrecognized bank — used generic parser.")

    metadata = TransactionMetadata(bank_name)
    return ProcessingResult(file=ProcessedFile(pipeline.transform(statement), metadata), warnings=warnings)
