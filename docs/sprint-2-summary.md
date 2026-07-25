# Sprint 2 Summary

## Sprint Goal

The objective of Sprint 2 was to transform UrbanFlow from a working prototype into a more maintainable, testable, documented, and deployment-ready software project.

The focus was not on adding new analytical features, but on improving software architecture, code quality, project reproducibility, deployment reliability, and technical documentation.

## Completed Work

### Software Architecture

The backend was reorganised using a layered architecture:

```text
Router
  ↓
Service
  ↓
Repository
  ↓
PostgreSQL / PostGIS