# News Radar Skills Guide

This document describes the new skill layer for the TechEyes News Radar module.

## Overview

The skill layer wraps News Radar capabilities into reusable, orchestrated calls.

Base path:

- `/api/radar/skills`
- `/api/radar/skills/execute`
- `/api/radar/skills/workflow`

## Skill List

`GET /api/radar/skills`

Returns available skills and their input schema.

Implemented skills:

- `refresh_hot_news`
- `get_hot_news`
- `get_news_detail`
- `analyze_entities`
- `followup`
- `generate_report`
- `run_full_workflow`

## Execute One Skill

`POST /api/radar/skills/execute`

Request body example:

```json
{
  "skill": "analyze_entities",
  "args": {
    "entities": ["OpenAI", "NVIDIA"],
    "question": "请分析它们近期合作与竞争格局"
  }
}
```

Another example (requires login token):

```json
{
  "skill": "generate_report",
  "args": {
    "news_id": "news_xxx"
  }
}
```

## Run Full Workflow

`POST /api/radar/skills/workflow`

The workflow can execute a complete chain:

1. optional ingest from query
2. optional refresh
3. get hot news
4. select target news
5. get graph detail
6. analyze entities
7. optional followup
8. optional report generation

Request body example:

```json
{
  "query": "AI chips and model releases this week",
  "hot_limit": 10,
  "ingest_limit": 8,
  "force_refresh": true,
  "entities": ["OpenAI", "Google", "NVIDIA"],
  "analysis_question": "总结最新竞争态势与机会",
  "followup_question": "未来3个月重点风险是什么？",
  "generate_report": true
}
```

## Curl Examples

List skills:

```bash
curl -X GET "http://localhost:8000/api/radar/skills"
```

Execute single skill:

```bash
curl -X POST "http://localhost:8000/api/radar/skills/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "skill": "get_hot_news",
    "args": {"limit": 5, "force_refresh": false}
  }'
```

Run workflow:

```bash
curl -X POST "http://localhost:8000/api/radar/skills/workflow" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "AI startup funding",
    "hot_limit": 8,
    "force_refresh": true,
    "analysis_question": "给出竞争格局结论",
    "generate_report": false
  }'
```

Run workflow with auth (for report persistence):

```bash
curl -X POST "http://localhost:8000/api/radar/skills/workflow" \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "hot_limit": 8,
    "followup_question": "这条新闻对应企业的下一步动作是什么？",
    "generate_report": true
  }'
```

## Notes

- `generate_report` requires authenticated user identity.
- Workflow still runs without login, but report generation will be skipped.
- Errors for missing required fields return HTTP `400`.
