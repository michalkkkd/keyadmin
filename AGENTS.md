# Agent Programming Principles & Rules

The AI Agent operating in this workspace MUST strictly adhere to the following enhanced programming principles at all times. These rules govern architectural decisions, code generation, refactoring strategies, and problem-solving.

**[SHARED KNOWLEDGE BASE RULE]**
This file (AGENTS.md) and all documents it references (in the docs/agent_knowledge/ and docs/security/ folders) are the centralized knowledge base for both the **KeySec** and **KeyFirmware** projects. Agents working on KeyFirmware must reference these rules here. You no longer need to duplicate or synchronize these files to KeyFirmware.

### COMPILATION & FLASHING INSTRUCTIONS FOR THE AGENT
1. To compile: cd cmake_gcc && cmake --build --preset default_config inside KeyFirmware.
2. To flash: Execute the batch script explicitly cd C:\Users\god\Documents\STORMPROJECTS\KeyFirmware\flashbat && .\xiao_mg24_flash.bat (Note: Agent CAN and SHOULD flash the device autonomously using this command when needed).

## 1. KISS — Keep It Simple, Stupid
**Prefer the simplest solution that correctly solves the problem.**
- Avoid unnecessary abstraction, premature optimization, and cleverness. 
- Simple code is secure code; complexity breeds vulnerabilities and bugs.
- If a straightforward built-in function or sequential logic does the job, do not build a complex design pattern or custom wrapper around it.

## 2. DRY — Don't Repeat Yourself
**Avoid duplicating knowledge or logic.**
- Extract shared behavior when duplication represents the exact same concept or business rule.
- *Caveat:* Do not blindly deduplicate code that just happens to look similar but represents fundamentally different domains (beware of false DRY). 

## 3. SoC — Separation of Concerns
**Keep different responsibilities separate so each part of the system has a clear purpose.**
- UI/CLI or presentation logic must never mix with transport/protocol or database logic.
- Low-level hardware/serial interactions (e.g., PySerial loops, sl_iostream) must belong in dedicated transport layers, completely hidden from the high-level API business logic.

## 4. SRP — Single Responsibility Principle
**A module, class, or function should have one clear responsibility and one primary reason to change.**
- Functions should ideally fit on a single screen and do exactly what their name implies—nothing more.
- If a class or function requires the word "And" in its description (e.g.,  alidate_and_save_user), it violates SRP and must be split.

## 5. Fail Fast
**Detect invalid states and inputs as early as possible rather than allowing bad data to propagate through the system.**
- Validate all incoming data (especially raw bytes over UART/USB buffers) immediately upon receipt.
- Use explicit assertions and raise descriptive, immediate exceptions upon detecting anomalies.
- **Never** silently swallow exceptions (except Exception: pass) or return default fallback values when a critical operation fails.

## 6. POLA — Principle of Least Surprise (Principle of Least Astonishment)
**Code should behave in ways that other developers would reasonably expect.**
- Prefer conventional, predictable behavior over clever, undocumented, or esoteric language tricks.
- Adhere strictly to language conventions (PEP 8 for Python, standard embedded C guidelines for C).
- Naming must be unambiguous, descriptive, and perfectly reveal the intent of the variable or function.

## 7. YAGNI — You Aren't Gonna Need It
**Do not write code for future, speculative requirements.**
- Implement only what is strictly necessary for the current task. 
- Avoid creating generic interfaces, speculative base classes, or overly complex class hierarchies "just in case" they might be needed later.

## 8. Secure by Default & Defensive Programming
**[CRITICAL DIRECTIVE] SECURITY IS PRIORITY NUMBER 1. THE MOST IMPORTANT ASPECT OF THIS PROJECT.**
- **NEVER COMPROMISE SECURITY TO FIX A BUG.** If there are errors, build failures, or integration problems, we FIX the problem by implementing the missing features properly. We NEVER lower the level of security, bypass cryptography, or use weaker fallbacks just to make it work.
- **In a hardware security project, the default state must always be the secure state.**
- Default to least privilege. Variables should be as tightly scoped as possible.
- Assume all external input (from PC to Dongle, or Dongle to PC) is malicious until fully parsed and verified (e.g., CRC, bounds checking).
- Magic numbers are strictly forbidden; always use named constants, defines, or enums (e.g.,  x08 must be MSG_ADMIN_USERS).

## 9. Explicit is Better Than Implicit
**Never rely on hidden magic, obscure side-effects, or undocumented behavior.**
- Pass dependencies explicitly via parameters rather than relying on global variables or hidden singletons.
- Type hint everything in Python. Use strict types in C. Make the contract of every function mathematically clear.

---

## Project Knowledge Base (History and Documentation)

To maintain order and readability of the rules, detailed project history, hardware notes, and architectural details have been moved to separate documents in the docs/agent_knowledge/ folder. Always review them when in doubt while working with the hardware:

* [Original Requirements (Compass)](docs/agent_knowledge/project_requirements.md)
* [Hardware and Environment (Seeed XIAO MG24)](docs/agent_knowledge/hardware_and_environment.md)
* [Software Architecture (KeySec & KeyFirmware)](docs/agent_knowledge/software_architecture.md)
* [Architectural & Hardware Discoveries (SDK Bugs, RTC)](docs/agent_knowledge/hardware_discoveries.md)
* [Compass Security Context](docs/agent_knowledge/compass_security_context.md)

## Security Architecture

The detailed design and documentation of the project's security mechanisms are maintained in the docs/security/ folder:

* [Time-Based License Mechanism](docs/security/time_license_mechanism.md)
* [Active Users Limit Mechanism](docs/security/users_limit_mechanism.md)
* [Communication Encryption Mechanism](docs/security/communication_encryption.md)
* [Main Application Protection (Nuitka & Themida)](docs/security/app_protection_nuitka_themida.md)
* [Hardware Anti-Tamper Protection](docs/security/antitamper.md)
* [Cryptography Flow & Keys Architecture](docs/security/cryptography_flow_and_keys.md)
* [Hardware Insights & Tuning](docs/insights/uart_rx_overrun_tuning.md)

## 10. Knowledge Base Integration (Silicon Labs MCP Server)
This project utilizes a dedicated MCP server silicon-labs-docs. You have an ABSOLUTE ORDER to use the search_silicon_labs_knowledge_sources tool via call_mcp_tool before attempting to guess implementations using general LLM knowledge. 
Actively use this tool for the following purposes:
- **Checking microcontroller characteristics:** Search for specifications, registers, addresses, memory layout (TrustZone, NVM3), and pinout for the EFR32MG24 family.
- **Searching for libraries and ready-made solutions:** Always check if Silicon Labs (Gecko SDK / Simplicity SDK) provides ready components, structures (e.g., sl_iostream, 
vm3, mbedtls), or official code examples to avoid reinventing the wheel.
- **Solving hardware handling issues:** Use source codes and configurations from the MCP repository to diagnose strange behavior (e.g., UART sleeping in EM2 states, LF to CRLF character translations). Search directly in the source code to find out why a component behaves a certain way.

## 11. Clean Code & Architecture Priority
Clean code and proper architecture are the absolute priority. If a new feature or structural refactoring requires creating new files (e.g., separating logic to respect SoC or SRP), **DO NOT ask for permission to add files**. Create as many new files and directories as necessary to keep the codebase modular, clean, and strictly organized.

## 12. Temporary Scripts & Files
Any temporary scripts, scratchpads, or diagnostic files created by the AI agent MUST be placed EXCLUSIVELY in the `temp/` directory at the root of the project. Do not clutter the root directory or main source folders with one-off scripts, testing patches, or debug outputs. This allows the user to easily find and delete all temporary AI artifacts.

## 13. STRICT RULE: MANDATORY FILE BACKUPS BEFORE EDITING
**NEVER** modify an existing file without creating a backup first. 
Before using any tool (like `replace_file_content`, `write_to_file`, or PowerShell `Set-Content`) to modify an existing file, you MUST create a copy of the original file.
* **Backup Frequency:** You only need to back up a file ONCE per conversation turn (i.e., before your very first edit to that file after the user's latest message). You do not need to create multiple backups of the same file if you edit it multiple times during a single turn.
* **Backup Location:** `backup/<folder_path_flattened>/<filename>__<detailed_timestamp>`
* **Example:** If you are about to edit `app/frontend/pkge_dashboard.py`, you must first copy it to `backup/app_frontend/pkge_dashboard.py__20261002_220645`.
* **Requirement:** Create the `backup` directory and the flattened subdirectories if they do not exist.
This ensures that uncommitted work is never permanently lost due to autonomous agent edits.
