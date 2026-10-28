
from pydantic import ValidationError
from core.schemas import ScholarshipCreate

scholarship = ScholarshipCreate(
    name="Example International Scholarship",
    provider="Example University",
    host_country="Germany",
    degree_level=["Master's"],
    eligible_countries=["Nigeria"],
    funding_coverage={
        "tuition": "Full",
        "living_stipend": "Unknown",
    },
    official_url="https://example.com/scholarship",
)

print("Valid scholarship!")
print(scholarship.model_dump(mode="json"))

try:
    ScholarshipCreate(name="X", unexpected_field="test")
except ValidationError:
    print("Invalid record correctly rejected!")
