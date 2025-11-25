# Storage Manager Refactoring Plan

## Overview
Refactor `scripts/storage_manager.py` into `app/management/storage_manager.py` with a wrapper script `scripts/storage_manager.sh` that:
- Sources centralized environment configuration (`doco.env`)
- Passes environment context to the Python module via CLI arguments
- Supports both PROD and TEST environments seamlessly

---

## Staged Implementation Plan

### **STAGE 1: Directory & Module Setup**

**Objective**: Create the new module structure

**Tasks**:
1. Create `app/management/` directory
2. Create `app/management/__init__.py` (empty)
3. Create `app/management/storage_manager.py` (copy from scripts/storage_manager.py)
4. Update `app/management/storage_manager.py` imports (update sys.path reference)

**Expected Changes**:
- New path: `/app/management/storage_manager.py` (main logic stays the same)
- Accessible as: `python -m app.management.storage_manager`

**Testing**: Verify module can be imported and run from project root

---

### **STAGE 2: Add Environment Arguments to Python Module**

**Objective**: Make storage_manager.py accept and use environment context

**Changes to `app/management/storage_manager.py`**:

1. **Add new CLI arguments to argparse** (parent parser level):
   ```
   --doco-env (PROD|TEST) - Override environment mode
   --data-root            - Override data directory (defaults from DOCO_DATA env var)
   --token-store          - Override token store path (defaults from DOCO_TOKEN_STORE env var)
   --storage-dir          - Override storage directory (existing, deprecated in favor of data-root)
   ```

2. **Update `resolve_storage_dir()` function**:
   - Priority: CLI args > ENV variables > Config defaults
   - Check `args.data_root` first (new)
   - Fall back to `args.storage_dir` (existing)
   - Fall back to `DOCO_DATA` environment variable
   - Fall back to Config defaults

3. **Update main()** to accept args with new fields

**Affected Functions**:
- `resolve_storage_dir()` - Enhanced with priority chain
- `main()` - Add argument parsing for new options

**No Breaking Changes**: Existing functionality preserved, new args optional

---

### **STAGE 3: Create Wrapper Shell Script**

**Objective**: Create `scripts/storage_manager.sh` that bridges environments

**File**: `/scripts/storage_manager.sh`

**Features**:
```bash
#!/bin/bash
# Storage Manager CLI Wrapper
# Usage: ./storage_manager.sh [--env PROD|TEST] <resource> <command> [options]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/doco.env"

# Parse --env flag if provided
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            export DOCO_ENV="$2"
            shift 2
            ;;
        *)
            break
            ;;
    esac
done

# Re-source with potentially updated DOCO_ENV
source "$SCRIPT_DIR/doco.env"

# Call Python module with environment variables as CLI args
cd "$DOCO_ROOT"
python -m app.management.storage_manager \
    --doco-env "$DOCO_ENV" \
    --data-root "$DOCO_DATA" \
    --token-store "$DOCO_TOKEN_STORE" \
    "$@"
```

**Benefits**:
- Single entry point for storage management
- Automatic environment detection
- Consistent with other scripts
- Supports: `./storage_manager.sh --env PROD sessions list`

---

### **STAGE 4: Update Documentation & References**

**Objective**: Update calling code to use new wrapper

**Files to Update**:
1. `README.md` - Update storage manager usage examples
2. Any scripts that call `python scripts/storage_manager.py` → `scripts/storage_manager.sh`
3. `STORAGE_MANAGEMENT.md` (if exists) - Update paths and examples

**Search & Replace**:
```bash
# Find all references
grep -r "storage_manager.py" /home/doco/devroot/doco --include="*.sh" --include="*.md"

# Update references to point to wrapper script
```

---

### **STAGE 5: Testing & Validation**

**Objective**: Verify all functionality works in both modes

**Test Cases**:

**TEST Environment**:
```bash
export DOCO_ENV=TEST
./scripts/storage_manager.sh sessions list
./scripts/storage_manager.sh storage stats
./scripts/storage_manager.sh --env TEST sessions list  # Explicit override
```

**PROD Environment**:
```bash
export DOCO_ENV=PROD
./scripts/storage_manager.sh sessions list
./scripts/storage_manager.sh storage stats
```

**Backward Compatibility**:
```bash
# Direct Python call (should still work with default env)
cd /home/doco/devroot/doco
python -m app.management.storage_manager sessions list
```

---

### **STAGE 6: Cleanup**

**Objective**: Remove old script, verify no dangling references

**Tasks**:
1. Delete `scripts/storage_manager.py` (after confirming no direct imports)
2. Search for any remaining direct imports of storage_manager module
3. Update any Python code that does `from scripts.storage_manager import ...` (if any)
4. Verify all tests pass

**Validation**:
```bash
grep -r "from scripts.storage_manager" /home/doco/devroot/doco
grep -r "import storage_manager" /home/doco/devroot/doco
```

---

## Directory Structure After Refactoring

```
app/
  management/                    [NEW]
    __init__.py                  [NEW]
    storage_manager.py           [MOVED from scripts/]

scripts/
  storage_manager.sh             [NEW - wrapper]
  doco.env                       [existing - centralized config]
  restart_servers.sh             [existing]
  run_mcp.sh                     [existing]
  run_web.sh                     [existing]
  ... (other scripts)

# OLD FILE (to delete)
scripts/storage_manager.py       [DELETE after stage 6]
```

---

## Implementation Order

| Stage | Task | Risk | Time |
|-------|------|------|------|
| 1 | Create directory & copy module | Low | 5 min |
| 2 | Add argparse parameters | Low | 10 min |
| 3 | Create wrapper script | Low | 5 min |
| 4 | Update documentation | Low | 5 min |
| 5 | Run all test cases | Medium | 10 min |
| 6 | Cleanup old files | Low | 2 min |

**Total Estimated Time**: ~40 minutes

---

## Rollback Plan

If issues occur during refactoring:
1. Keep original `scripts/storage_manager.py` backed up
2. If wrapper fails: restore old script temporarily
3. If argparse changes break functionality: revert to using environment variables only
4. If module import issues: adjust `sys.path` in new location

---

## Success Criteria

✅ `./scripts/storage_manager.sh sessions list` works in both TEST and PROD  
✅ `./scripts/storage_manager.sh --env TEST storage stats` works  
✅ `python -m app.management.storage_manager sessions list` works  
✅ All existing tests pass  
✅ No breaking changes to public API  
✅ Environment variables properly flow through wrapper to Python module
