import json
import os
import anthropic

# Initialize the Anthropic client (reads ANTHROPIC_API_KEY from environment)
client = anthropic.Anthropic()


# Fetch an active model ID directly from your Anthropic account
def get_available_model():
    try:
        models_page = client.models.list()
        if models_page.data:
            selected_model = models_page.data[0].id
            print(
                f"Using available model from your API key: '{selected_model}'\n",
                flush=True,
            )
            return selected_model
    except Exception as e:
        print(
            f"Notice: Could not list models ({e}). Falling back to default.", flush=True
        )

    return "claude-3-5-sonnet-latest"


ACTIVE_MODEL = get_available_model()

TEST_NOTES = [
    "Pump 4 vibration levels remain within normal range after service.",
    "Conveyor belt 12 motor overheating, smoke smell reported, line stopped.",
    "Compressor unit 7 pressure gauge reading slightly inconsistent, monitoring.",
    "Emergency shutoff valve on Tank 3 failed to engage during test.",
    "Routine filter replacement completed on HVAC unit 2, no issues found.",
]

STYLES = {
    "1_zero_shot": "Classify the urgency of this maintenance note as LOW, MEDIUM, or HIGH: {note}",
    "2_role": """You are a plant safety coordinator.
    Getting urgency wrong could put workers at risk or waste emergency response resources.
    Classify the urgency of this maintenance note as LOW, MEDIUM, or HIGH: {note}""",
    "3_few_shot": """Classify maintenance notes as LOW, MEDIUM, or HIGH urgency.

Example 1:
Note: "Backup generator tested successfully, no faults found."
Urgency: LOW

Example 2:
Note: "Boiler pressure valve stuck, steam leaking near control panel, area evacuated."
Urgency: HIGH

Now classify this note:
{note}
Urgency:""",
    "4_cot": """Classify the urgency of this maintenance note as LOW, MEDIUM, or HIGH.
Think step by step:
1) What equipment/system is involved?
2) Is there an immediate safety risk?
3) What happens if this is ignored?
Then give your final answer as "Urgency: LOW/MEDIUM/HIGH".

Note: {note}""",
    "5_structured": """Classify the urgency of this maintenance note as LOW, MEDIUM, or HIGH.
Return ONLY valid JSON, no other text, in this exact format:
{{"urgency": "LOW|MEDIUM|HIGH", "reason": "one sentence explanation"}}

Note: {note}""",
}

results = []

print("Running API queries across 5 prompt styles x 5 notes...\n", flush=True)

# Loop over defined STYLES dictionary
for style_name, prompt_template in STYLES.items():
    for note in TEST_NOTES:
        prompt = prompt_template.format(note=note)

        response = client.messages.create(
            model=ACTIVE_MODEL,
            max_tokens=300,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )

        output_text = response.content[0].text.strip()
        results.append({"style": style_name, "note": note, "output": output_text})

        print(f"[{style_name}] {note[:45]}...", flush=True)
        print(f"  -> {output_text}\n", flush=True)

# Save JSON output in current directory
output_filename = "exercise1_results.json"
with open(output_filename, "w") as f:
    json.dump(results, f, indent=2)

print(f"Done! 25 results successfully saved to '{output_filename}'.", flush=True)
