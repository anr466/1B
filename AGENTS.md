# 🧠 Reasoning.md — Universal System Reasoning Specification

## 1. Purpose

Define a consistent, deterministic reasoning framework that governs:

* Decision-making
* Planning
* Execution
* State awareness
* Memory updates
* Tool interaction

This file acts as the system’s cognitive contract.

---

## 2. Core Principles

* Determinism over randomness
* Explicit reasoning over implicit behavior
* Validation before execution
* State-aware decisions
* Continuous feedback integration
* Separation of concerns

---

## 3. System State Model

The system must always maintain awareness of:

### 3.1 Internal State

* Current task
* Active processes
* Resource availability
* Errors and warnings

### 3.2 External State

* Environment conditions
* Input validity
* Dependency availability

### 3.3 Historical State

* Previous decisions
* Outcomes
* Performance metrics

---

## 4. Execution Lifecycle

The execution lifecycle is DEPRECATED in this generic document to avoid conflicts. 
You MUST adhere strictly to the "Cognitive Loop" and "Execution Protocol" defined in your `.clinerules` or `.opencode.md` files.

---

## 5. Reasoning Protocol

### 5.1 Decision Preconditions

A decision may only be made if:

* Inputs are valid
* Required state is available
* No blocking constraints exist

### 5.2 Decision Logic

All decisions must:

* Be explainable
* Be reproducible
* Follow defined rules or policies

### 5.3 Conflict Resolution

If multiple valid actions exist:

* Rank by priority
* Evaluate risk
* Select optimal outcome based on objective function

---

## 6. Planning Layer

Planning must:

* Define clear objectives
* Break tasks into atomic steps
* Identify dependencies
* Estimate risks
* Allow dynamic adjustment

Plans are not static and must adapt to new information.

---

## 7. Tool Interaction Rules

* Tools must not be invoked without validation
* Each tool call must have:

  * Clear intent
  * Defined input
  * Expected output structure
* Tool results must be verified before use
* Failures must trigger fallback or retry logic

---

## 8. Memory Model

Memory updates must strictly adhere to the `Continuous Memory Protocol` defined in `.clinerules`. 
- Use Git diffs for short-term contextual tracking.
- Do NOT log excessive outputs or code states into Markdown memory to prevent Token limits (Session Compression).

---

## 9. Error Handling

* Detect errors early
* Classify errors (critical / non-critical)
* Prevent propagation of invalid states
* Apply retry, fallback, or abort strategies

---

## 10. Validation Layer

Before execution, the system MUST verify:

* Logical consistency
* State compatibility
* Resource availability
* Constraint satisfaction

Failure in validation MUST block execution.

---

## 11. Logging & Traceability

Detailed logging is DEPRECATED as it causes Context Window Compression. 
You MUST follow the "Clean UI" directive from `.clinerules` and only track tasks via `task.md`.

---

## 12. Self-Improvement

The system must:

* Analyze past outcomes
* Detect inefficiencies
* Adjust internal parameters or rules
* Avoid repeating failed patterns

---

## 13. Constraints

* No action without justification
* No assumption without validation
* No execution under uncertainty beyond threshold
* No silent failures

---

## 14. Termination Conditions

The system must stop or pause when:

* Objectives are achieved
* Critical failure occurs
* Constraints are violated
* External interruption is received

---

## 15. Extensibility

This reasoning framework must:

* Support modular extension
* Allow new tools and rules
* Remain backward compatible
* Maintain consistency across updates
