"""Verify browser-generated PDF evidence with pypdf."""
import argparse
from pathlib import Path

from pypdf import PdfReader
from pypdf.generic import ContentStream


EXPECTED = {
    "sample-Student": ("₹1,200", "Education", "EXAMPLE INPUT", "76.00%", "24.00%", "Scenario ₹1,500"),
    "sample-Working": ("₹14,000", "Monthly take-home salary", "EXAMPLE INPUT"),
    "sample-Freelancer": ("₹15,000", "Lower-income month estimate", "EXAMPLE INPUT"),
    "sample-Other": ("₹800", "Discretionary expenses", "EXAMPLE INPUT"),
    "personal-Student": ("₹1,200.29", "Education", "SELF-REPORTED", "Unavailable", "Purchase savings goal", "4 whole months"),
    "personal-Working": ("₹14,000", "Monthly take-home salary", "SELF-REPORTED", "Scenario ₹8,000"),
    "personal-Freelancer": ("₹15,000", "Lower-income month estimate", "SELF-REPORTED"),
    "personal-Other": ("-₹3.25", "Discretionary expenses", "SELF-REPORTED", "Unavailable"),
}


def inspect(directory: Path) -> None:
    for name, expected in EXPECTED.items():
        reader = PdfReader(directory / f"{name}.pdf")
        assert len(reader.pages) >= 2, name
        page_text = [page.extract_text() for page in reader.pages]
        text = " ".join(" ".join(page_text).split())
        for phrase in (*expected, "5W1H", "Complete input register", "Calculation:",
                       "Monthly cash-flow comparison", "Expense breakdown", "Where your money goes",
                       "Emergency savings coverage", "What could you improve?", "Local rehearsal link"):
            assert phrase in text, (name, phrase)
        for index, page in enumerate(page_text, 1):
            assert f"Page {index} of {len(page_text)}" in page, (name, index)
            assert len(page.split()) > 20, (name, index, "near-empty page")
        rectangles = sum(
            operator == b"re"
            for page in reader.pages
            for _, operator in ContentStream(page.get_contents(), reader).operations
        )
        assert rectangles >= 16, (name, rectangles)
        print(f"{name}: {len(page_text)} pages, {rectangles} vector rectangles, expected text verified")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    inspect(parser.parse_args().directory)
