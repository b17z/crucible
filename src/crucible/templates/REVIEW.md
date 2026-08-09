---
triggers:
  - paths: ["src/**/*.py"]
    min_changed_lines: 50
    note: "Substantial source changes — run `crucible review` before committing"
  - paths: ["**/auth*", "**/crypto*"]
    note: "Security-sensitive paths — review with the security-engineer skill"
---
# Review Conventions

## Severity bar
<!-- What blocks a merge here vs what is advisory -->

## Focus areas
<!-- What reviewers (human or agent) should weight for this project -->

## Checklist
<!-- The project's review checklist -->
