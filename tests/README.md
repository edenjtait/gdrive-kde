# Headless PyQt Testing Guide

This guide explains how to test PyQt applications in headless environments (such as CI/CD pipelines, containers, or servers without a display).

## Understanding the Challenge

Testing GUI applications without a display presents specific challenges:

1. **Missing Display Server**: PyQt expects to connect to a display server (like X11)
2. **Widget Rendering**: Widgets attempt to render, which requires a display
3. **Event Loop Interaction**: Modal dialogs block the test execution
4. **Native Resources**: Some components try to access native resources

## Solution Overview

The approach involves:

1. Using the "offscreen" Qt platform plugin
2. Mocking widget methods that require a display
3. Structuring tests to avoid actual widget rendering
4. Ensuring proper QApplication initialization

## Implementation Steps

### 1. Set Up Environment Variables

Before importing any PyQt modules, set the required environment variables:

```python
import os
# Use the offscreen platform plugin
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Only after this import PyQt modules
from PyQt6.QtWidgets import QApplication
```

### 2. Create a Headless QApplication

Ensure a headless QApplication instance exists before creating any widgets:

```python
app = QApplication.instance() or QApplication(sys.argv)
```

### 3. Mock Dialog Methods

Modal dialog methods (`exec`, `show`, etc.) need to be mocked:

```python
with patch('PyQt6.QtWidgets.QDialog.exec', return_value=1), \
     patch('PyQt6.QtWidgets.QFileDialog.getExistingDirectory', return_value="/mock/path"):
    # Your test code here
```

### 4. Mock Widget Creation

Prefer mocking widget construction rather than creating real widgets:

```python
dialog = MagicMock(spec=YourDialog)
dialog.some_widget = MagicMock()
```

## Common Issues and Solutions

### "QWidget: Must construct a QApplication before a QWidget"

**Solution**: Ensure QApplication is initialized before any QWidget creation, even in imports.

```python
# Set platform first
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Then create QApplication
app = QApplication(sys.argv)

# Only then import modules that might create widgets
from your_module import YourWidgetClass
```

### "Could not connect to display"

**Solution**: Use the offscreen platform and ensure you're not creating actual widgets:

```python
os.environ["QT_QPA_PLATFORM"] = "offscreen"
```

### "No Qt platform plugin could be initialized"

**Solution**: Ensure the Qt platform plugins are available. You may need to install additional packages:

```bash
# For Ubuntu/Debian
sudo apt-get install libxcb-cursor0
```

### Modal Dialog Testing

**Solution**: Mock the exec method and test internal methods separately:

```python
# Mock the modal behavior
with patch('PyQt6.QtWidgets.QDialog.exec', return_value=1):
    # Call the method that would show the dialog
    result = obj.method_that_shows_dialog()
    
    # Verify the expected behaviors
    assert result == expected_value
```

## Best Practices

1. **Early Platform Selection**: Set `QT_QPA_PLATFORM=offscreen` before importing any Qt modules
2. **Single QApplication**: Ensure only one QApplication instance exists across all tests
3. **Mock Not Create**: Mock widget creation instead of creating actual widgets
4. **Focus on Behavior**: Test the behavior, not the rendering
5. **Separate UI Logic**: Design your code to separate UI logic from business logic
6. **Use Fixtures**: Create reusable fixtures for common patterns

## Debugging Tips

If you're having trouble with headless testing, try these debugging techniques:

```python
# Enable Qt plugin debugging
os.environ["QT_DEBUG_PLUGINS"] = "1"

# Print platform information
print(f"Qt platform: {os.environ.get('QT_QPA_PLATFORM', 'default')}")
print(f"Display: {os.environ.get('DISPLAY', 'not set')}")

# Check available plugins
from PyQt6.QtGui import QGuiApplication
print(f"Available platforms: {QGuiApplication.platformName()}")
```

By following these guidelines, you can successfully test PyQt applications in headless environments, making your tests more reliable and compatible with automated testing pipelines.
