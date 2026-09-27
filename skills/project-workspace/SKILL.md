---
name: video-project-workspace
description: Decide whether an AI video prompt task needs a saved project folder and create a non-overwriting package when requested.
---

# Video Project Workspace

For a simple prompt response, give the final prompt inline and create no folder. A folder is useful when the user requests saved files, references, debug reports, multiple clips, or an artifact to continue editing. If needed but no destination or name was supplied, ask where to save the project. Do not infer a location outside the active workspace without a user choice.

After the ScenePlan is prepared, run `python scene_pipeline.py PLAN --project-dir PROJECT_FOLDER`. The command creates or uses the folder and writes `scene-plan.json`, `validation.json`, `project.json`, and `prompts/clip-XX.txt` when validation passes. If validation fails, the report is saved but no final prompts are saved. Existing output files are never overwritten. Keep user-provided reference media in place; `project.json` records their paths and roles, and the command does not copy them.
