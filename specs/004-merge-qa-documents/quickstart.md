# Quickstart: Consolidated Question & Answer Document Merger

## Overview
This document provides instructions for using and testing the **Consolidar P&R** tool feature.

## User Workflow

1. Open the application interface in your web browser.
2. Select the **Consolidar P&R** tab in the main top navigation panel.
3. Choose your input format mode: **JSON** or **TXT**.
4. Drag and drop or browse to select multiple `.json` or `.txt` Q&A documents.
5. Click **Iniciar Consolidação** to execute deduplication and merging.
6. View the execution status, logs, and merged Q&A results on screen.
7. Click the **Baixar JSON** or **Baixar TXT** buttons to download consolidated output files.

## Running Tests

### Backend Unit & Integration Tests

Run backend tests using pytest:

```bash
cd backend
pytest tests/unit/test_qna_merger.py tests/integration/test_merger_api.py -v
```

### Manual Testing with Sample Files

1. Prepare two sample TXT files or JSON files with overlapping questions.
2. Upload via the interface.
3. Confirm that duplicate questions have their `frequencia` counts summed and that both `.txt` and `.json` files are produced.
