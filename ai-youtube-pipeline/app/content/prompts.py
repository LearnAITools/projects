"""Prompt builders for Claude-based content generation."""

from app.content.models import VideoFormat


def build_topic_prompt(
    topic: str, video_format: VideoFormat = VideoFormat.LONG_FORM
) -> str:
    """Build a structured prompt for generating a video brief."""
    requirements = video_format.rendering_requirements
    return """
You are an expert YouTube content strategist and scriptwriter.

Create a high-quality video plan for the topic: "{topic}"

Format: {video_format}. Rendering requirements: {rendering_requirements}.
{format_guidance}

Requirements:
- Return valid JSON only.
- The JSON must match this schema:
{{
  "topic": "...",
  "format": "{video_format}",
  "rendering_requirements": {rendering_requirements_json},
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
""".format(
    topic=topic,
    video_format=video_format.value,
    rendering_requirements=requirements,
    rendering_requirements_json=str(requirements).replace("'", '"'),
    format_guidance=_format_guidance(video_format),
    ).strip()


def _format_guidance(video_format: VideoFormat) -> str:
    if video_format is VideoFormat.SHORT:
        return """Short requirements:
- Write a hook that lands in the first 2 seconds.
- Keep the spoken script concise and paced for a video under 180 seconds.
- Use 3 to 8 fast-moving scenes with short, visually clear narration.
- Make the title, description, and tags clearly suited to YouTube Shorts."""
    return """Long-form requirements:
- Develop a strong hook for the first 10 seconds.
- Use a coherent multi-scene structure with enough detail for a long-form video.
- Make the title, description, and tags suited to long-form YouTube discovery."""
