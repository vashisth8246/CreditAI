"""Check the PDF downloaded by the Money Passport browser rehearsal."""
import sys
from pathlib import Path

from pypdf import PdfReader
from pypdf.generic import ContentStream

reader = PdfReader(Path(sys.argv[1]), strict=True)
pages = [page.extract_text() for page in reader.pages]
text = " ".join(" ".join(pages).split())
for phrase in (
    "Money Passport", "Student laptop", "Savings Goal", "EXAMPLE-BASED PLAN",
    "Retained profile: Student", "Original challenge plan", "₹1,000",
    "₹550.5", "₹449.5", "Planned milestones", "Actual recorded timeline",
    "Recorded contribution", "Privacy and limitations", "Explore CreditAI",
):
    assert phrase in text, phrase
assert "₹300.25" not in text, "The edited value must replace the old amount"
for index, page in enumerate(pages, 1):
    assert f"Page {index} of {len(pages)}" in page
    assert len(page.split()) > 20
rectangles = sum(
    operator == b"re"
    for page in reader.pages
    for _, operator in ContentStream(page.get_contents(), reader).operations
)
assert rectangles >= 4, rectangles
print(f"Passport PDF: {len(pages)} page(s), {rectangles} vector rectangles, current amounts and provenance verified")
