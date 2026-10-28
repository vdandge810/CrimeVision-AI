# Software Requirements Specification (SRS)

## 1. Purpose
CrimeVision AI is an educational prototype for organizing image, video, and audio evidence and surfacing machine-generated observations for human review.

## 2. User
An authorized investigator or student demonstrator working with lawfully obtained test evidence.

## 3. Functional requirements
- FR-01: Register media against a case ID.
- FR-02: Reject unsupported file extensions and oversized uploads.
- FR-03: Compute and store a SHA-256 digest at intake.
- FR-04: Display evidence metadata and processing status.
- FR-05: Optionally detect generic objects in images and sampled video frames.
- FR-06: Optionally transcribe audio and retain segment timestamps when provided.
- FR-07: Store model observations as reviewable events.
- FR-08: Answer simple case questions from stored evidence records.
- FR-09: Export an evidence register and recorded events to PDF.
- FR-10: Communicate limitations and require human verification.

## 4. Non-functional requirements
- NFR-01: Clear API responses and error messages.
- NFR-02: Persistent local storage for prototype data.
- NFR-03: Configurable upload size limit.
- NFR-04: No unsupported claim of model certainty or legal admissibility.
- NFR-05: Production version must implement authentication, authorization, encryption, auditability, backups, and retention controls.

## 5. Out of scope for MVP
- Person identification or face recognition.
- Definitive weapon classification or intent inference.
- Automatic determination of guilt or event causality.
- Validated forensic acquisition and court-admissibility certification.
- Production multi-user access control.
