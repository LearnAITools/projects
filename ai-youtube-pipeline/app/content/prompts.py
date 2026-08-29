"""Prompt builders for Claude-based content generation."""


def build_topic_prompt(topic: str) -> str:
    """Build a structured prompt for generating a video brief."""
    return """
You are an expert YouTube content strategist and scriptwriter.

Create a high-quality video plan for the topic: "{topic}"

Requirements:
- Return valid JSON only.
- The JSON must match this schema:
{{
  "topic": "...",
  "title": "...",
  "hook": "...",
  "script": "...",
  "scenes": [
    {{
      "scene_number": 1,
      "narration": "...",
      "visual_description": "...",
      "duration_seconds": 5
    }}
  ],
  "youtube": {{
    "title": "...",
    "description": "...",
    "tags": ["..."]
  }}
}}

Guidelines:
- Make the title engaging and specific.
- Hook the audience in the first 10 seconds.
- Provide a complete narration script that can be spoken by AI voice.
- Include a scene list with scene descriptions and durations.
- Make the YouTube metadata click-worthy and SEO-friendly.
- Ensure the output is compact, practical, and polished.
- No markdown fences.
- No extra prose outside the JSON object.
""".format(topic=topic).strip()
