```markdown
# repo-loop-harness Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches the development conventions and workflows for the `repo-loop-harness` Python codebase. It covers file naming, import/export styles, commit message patterns, and testing practices, providing clear examples and command suggestions for efficient collaboration and maintenance.

## Coding Conventions

### File Naming
- Use **camelCase** for file names.
  - Example: `loopHarness.py`, `dataProcessor.py`

### Imports
- Use **relative imports** within the codebase.
  - Example:
    ```python
    from .utils import processData
    ```

### Exports
- Use **named exports** (explicitly listing what is exported).
  - Example:
    ```python
    __all__ = ['LoopHarness', 'runLoop']
    ```

### Commit Messages
- Follow **Conventional Commits** with the `feat` prefix for new features.
  - Example:
    ```
    feat: add support for custom loop intervals
    ```

## Workflows

### Feature Development
**Trigger:** When adding a new feature  
**Command:** `/feature-development`

1. Create a new branch for your feature.
2. Implement the feature using camelCase file naming and relative imports.
3. Add or update tests as needed.
4. Commit changes using the `feat:` prefix and a concise description.
5. Open a pull request for review.

### Code Import/Export Management
**Trigger:** When organizing or refactoring code modules  
**Command:** `/manage-imports-exports`

1. Use relative imports for all internal modules.
2. Explicitly define exported symbols using `__all__` in each module.
3. Refactor any absolute imports to relative style.

## Testing Patterns

- **Test Framework:** Unknown (no framework detected).
- **Test File Pattern:** Test files are named with the `.test.ts` extension, suggesting some TypeScript-based testing or legacy files.
- **Best Practice:** Ensure all new features and bug fixes include corresponding test files, even if the main codebase is Python.

  Example test file name:
  ```
  loopHarness.test.ts
  ```

## Commands
| Command                  | Purpose                                           |
|--------------------------|---------------------------------------------------|
| /feature-development     | Start a new feature branch and follow conventions |
| /manage-imports-exports  | Refactor or check imports/exports                 |
```
