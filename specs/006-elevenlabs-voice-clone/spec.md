# Feature Specification: 11Labs Voice Clone Integration

**Feature Branch**: `006-elevenlabs-voice-clone`  
**Created**: 2026-06-25  
**Status**: Draft  
**Input**: Integrate 11Labs Python API for voice cloning with actor voice samples stored in the Franchise Bible database

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Admin adds actor voice sample to Bible (Priority: P1)

A production admin adds a voice sample for an actor (e.g., Rachel Green from Friends) to the Franchise Bible so that when scripts are generated, the character's dialogue uses a cloned voice based on that sample.

**Why this priority**: Foundation for the entire feature; without this, voice cloning cannot occur. Unblocks all downstream generation workflows.

**Independent Test**: Can be fully tested by uploading an actor voice sample, verifying it's stored in the Bible, and retrieving it for generation. Delivers immediate value: system recognizes and persists actor voice data.

**Acceptance Scenarios**:

1. **Given** the admin is in the Bible management interface, **When** they upload a voice sample file (MP3/WAV) for an actor, **Then** the sample is validated, processed, and stored as a Bible entry with metadata (actor name, character name, date added)
2. **Given** a voice sample is stored in the Bible, **When** the admin queries for voice samples, **Then** the system returns all stored voice samples with their associated actors
3. **Given** an invalid audio file (corrupt, unsupported format, too short), **When** the admin uploads it, **Then** the system rejects it with a clear error message

---

### User Story 2 - Voice Agent uses 11Labs API with actor sample (Priority: P1)

During video production, the Voice Synthesis Agent calls 11Labs API to generate dialogue using a voice clone based on the stored actor sample, delivering output that sounds like the real actor.

**Why this priority**: Core production capability; without this, the voice cloning feature has no effect on output quality.

**Independent Test**: Can be fully tested by triggering script generation for a character with a stored voice sample, verifying the 11Labs API is called with the sample, and confirming the output audio matches the actor's voice profile. Delivers voice-cloned audio output.

**Acceptance Scenarios**:

1. **Given** a script with Rachel Green dialogue and a stored voice sample for Rachel, **When** the Voice Synthesis Agent processes the scene, **Then** it calls 11Labs API with the character name and retrieves a voice ID from the cloned sample
2. **Given** the 11Labs API returns a voice ID, **When** the agent generates dialogue ("That's not even a word!"), **Then** the resulting audio file sounds like the real actor and is saved to the production output
3. **Given** the 11Labs API is unavailable, **When** voice generation is triggered, **Then** the system gracefully falls back to a default Piper voice with a warning log

---

### User Story 3 - Expand Bible with more actor samples (Priority: P2)

After the initial Friends character is working, admins can add voice samples for other actors (Monica, Phoebe, Chandler, Joey, Ross) without modifying code.

**Why this priority**: Extends coverage; unblocks future franchises and characters once the foundation is proven.

**Independent Test**: Can be fully tested by adding a second actor voice sample and verifying it's usable in production independently of the first. Demonstrates system scalability.

**Acceptance Scenarios**:

1. **Given** the Rachel voice sample is working in production, **When** an admin adds a Monica voice sample using the same process, **Then** Monica scripts generate with her cloned voice without any code changes
2. **Given** multiple actor samples exist in the Bible, **When** the Voice Synthesis Agent processes a multi-character scene, **Then** each character's dialogue uses their corresponding voice clone

---

### Edge Cases

- What happens when an audio sample is corrupted or deleted from storage?
- How does the system handle a character with no stored voice sample (fallback to default voice)?
- How are audio formats handled (MP3 vs WAV vs OGG)?
- What happens if a voice sample file is too short (< 15 seconds) or too long (> 60 seconds)?
- How does system behave when approaching free tier limit (~10K chars/month)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow admins to upload audio files (MP3, WAV) via a Bible management interface
- **FR-002**: System MUST validate uploaded audio files for format, duration (30 seconds to 10 minutes), and quality before storing
- **FR-003**: System MUST store actor voice samples in the Franchise Bible database with metadata (actor_id, character_name, sample_file_path, upload_date, source_format)
- **FR-004**: Voice Synthesis Agent MUST integrate with 11Labs Python API using stored actor samples to generate character voice IDs
- **FR-005**: Voice Synthesis Agent MUST call 11Labs API with character name and voice sample to synthesize dialogue text into audio
- **FR-006**: System MUST persist generated voice IDs and map them to characters for future use (avoid re-cloning the same sample)
- **FR-007**: Voice Synthesis Agent MUST fall back to Piper TTS (default voice) if 11Labs API is unavailable or rate-limited
- **FR-008**: System MUST log all 11Labs API calls (character, text, success/failure, latency) for observability
- **FR-009**: System MUST support adding voice samples for multiple actors without code changes
- **FR-010**: Voice configuration (model, voice stability, similarity boost) MUST be configurable via environment variables or Bible metadata

### Key Entities

- **ActorVoiceSample**: Represents a stored audio sample for an actor
  - `actor_id`: Reference to actor/character
  - `character_name`: Display name (e.g., "Rachel Green")
  - `sample_file_path`: Path to stored audio file in MinIO
  - `sample_format`: Original format (MP3, WAV, etc.)
  - `duration_seconds`: Computed duration of sample
  - `elevenlabs_voice_id`: Generated voice ID from 11Labs (nullable until first use)
  - `upload_date`: Timestamp of when sample was added
  - `is_active`: Boolean to enable/disable a sample without deletion

- **VoiceSynthesisConfig**: Configuration for 11Labs API
  - `provider`: "elevenlabs" or "piper"
  - `model_id`: 11Labs model identifier (e.g., "eleven_monolingual_v1")
  - `voice_stability`: Float 0.0-1.0 (default 0.5)
  - `similarity_boost`: Float 0.0-1.0 (default 0.75)
  - `use_speaker_boost`: Boolean for audio quality enhancement

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Admins can upload a 15s voice sample for 1 character and have it stored in < 30 seconds
- **SC-002**: Voice-generated audio for cloned characters sounds recognizably similar (MVP quality, acceptable for POC; not high-fidelity)
- **SC-003**: Voice synthesis latency acceptable (< 15 seconds per 1000 characters on free tier)
- **SC-004**: System stays within 11Labs free tier limits (~10K chars/month)
- **SC-005**: 11Labs API unavailability does not block video production (fallback to Piper works)
- **SC-006**: Voice cloning feature works end-to-end for Rachel Green (Friends franchise MVP)

## Assumptions

- 11Labs **free tier** (no paid plan planned for MVP): ~10,000 characters/month budget
- 11Labs API credentials (API key) configured via environment variables (ELEVENLABS_API_KEY)
- Audio samples stored in MinIO under `voice-samples/` bucket prefix
- Voice samples: **15–60 seconds** (shorter than typical, MVP quality acceptable)
- Franchise Bible schema extended for voice sample metadata
- Single character (Rachel Green) MVP — no multi-character scaling planned
- Voice Synthesis Agent modified (not replaced) to use provider abstraction
- Existing Piper TTS remains fallback for characters without samples
- Quality expectations: MVP/POC quality, not polished production (voice may sound robotic or slightly off)
- Voice cloning quality depends on 11Labs free tier capabilities (limited fidelity)
