# TechPulse 2050

Static GitHub Pages technology and gaming intelligence console.

## Architecture

techpulse-news/
├── index.html
├── app.js
├── styles.css
├── fetch_news.py
├── news.json
├── assets/icons/techpulse.svg
├── assets/audio/
└── config/
    ├── categories.json
    ├── sources.json
    ├── ranking.json
    ├── themes.json
    └── features.json

## Setup

1. Replace the disabled example feeds in `config/sources.json` with RSS/Atom feeds you are permitted to use.
2. Set `enabled` to true.
3. Run `python3 fetch_news.py`.
4. Commit `news.json` and push to GitHub.
5. Enable GitHub Pages for the repository.

The builder preserves the existing `news.json` when a new dataset is empty or invalid.

## Implemented baseline

Top 10, continuous issue ticker, category intelligence, radar, trending, saved stories, daily brief, intelligence popup, source/provenance display, original-source links, browser speech narration, local preferences, accessibility controls, policy pages and responsive design.

## Deliberate future items

Server-side AI claim verification, persistent accounts/roles, true multi-source fact verification, PWA installation, push notifications and voice conversation require additional infrastructure and are not faked in this static build.
