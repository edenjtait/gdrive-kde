# tests/test_utils.py
import unittest
import os
import json
import tempfile
from unittest.mock import MagicMock, patch

# Define the utility functions we need to test
def minutes_to_ms(minutes):
    """Convert minutes to milliseconds"""
    return minutes * 60 * 1000

def parse_rsync_options(options_str):
    """Parse rsync options from string to list"""
    if not options_str:
        return ['-av', '--delete']
    return options_str.split()

def load_json_config(config_file):
    """Load a JSON configuration file"""
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}

def ensure_directory_exists(directory):
    """Ensure a directory exists, creating it if needed"""
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception:
        return False

def validate_sync_job(job):
    """Validate a sync job configuration"""
    if not job.get('name'):
        return False, "Job name is required"

    if not job.get('source_dir'):
        return False, "Source directory is required"

    if not job.get('dest_dir'):
        return False, "Destination directory is required"

    return True, ""

def run_rsync_command(source, dest, options=None):
    """Run an rsync command"""
    if options is None:
        options = ['-av', '--delete']

    cmd = ['rsync'] + options + [source, dest]

    try:
        import subprocess
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr
    except Exception as e:
        return False, str(e)

class TestUtils(unittest.TestCase):

    def test_minutes_to_ms(self):
        """Test converting minutes to milliseconds"""
        self.assertEqual(minutes_to_ms(1), 60000)
        self.assertEqual(minutes_to_ms(2), 120000)
        self.assertEqual(minutes_to_ms(0), 0)

    def test_parse_rsync_options(self):
        """Test parsing rsync options from string to list"""
        # Test with empty string
        self.assertEqual(parse_rsync_options(""), ['-av', '--delete'])

        # Test with a single option
        self.assertEqual(parse_rsync_options("-avz"), ['-avz'])

        # Test with multiple options
        self.assertEqual(
            parse_rsync_options("-avz --delete --exclude='*.tmp'"),
            ['-avz', '--delete', "--exclude='*.tmp'"]
        )

    def test_load_json_config(self):
        """Test loading a JSON configuration file"""
        # Create a temp config file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            config_file = f.name
            json.dump({"test": "data"}, f)

        try:
            # Test loading valid config
            config = load_json_config(config_file)
            self.assertEqual(config, {"test": "data"})

            # Test loading non-existent config
            config = load_json_config("/nonexistent/path.json")
            self.assertEqual(config, {})

            # Test loading invalid JSON
            with open(config_file, 'w') as f:
                f.write("This is not JSON")

            config = load_json_config(config_file)
            self.assertEqual(config, {})
        finally:
            # Clean up
            if os.path.exists(config_file):
                os.unlink(config_file)

    @patch('os.makedirs')
    def test_ensure_directory_exists(self, mock_makedirs):
        """Test ensuring a directory exists"""
        # Test successful directory creation
        mock_makedirs.return_value = None
        self.assertTrue(ensure_directory_exists("/test/dir"))
        mock_makedirs.assert_called_once_with("/test/dir", exist_ok=True)

        # Test failure due to permissions
        mock_makedirs.reset_mock()
        mock_makedirs.side_effect = PermissionError("Permission denied")
        self.assertFalse(ensure_directory_exists("/protected/dir"))

    def test_validate_sync_job(self):
        """Test validating a sync job configuration"""
        # Valid job
        valid_job = {
            "name": "test-job",
            "source_dir": "/test/source",
            "dest_dir": "/test/dest",
            "options": ["-av"]
        }
        valid, _ = validate_sync_job(valid_job)
        self.assertTrue(valid)

        # Missing name
        invalid_job = {
            "source_dir": "/test/source",
            "dest_dir": "/test/dest"
        }
        valid, error = validate_sync_job(invalid_job)
        self.assertFalse(valid)
        self.assertEqual(error, "Job name is required")

        # Missing source directory
        invalid_job = {
            "name": "test-job",
            "dest_dir": "/test/dest"
        }
        valid, error = validate_sync_job(invalid_job)
        self.assertFalse(valid)
        self.assertEqual(error, "Source directory is required")

        # Missing destination directory
        invalid_job = {
            "name": "test-job",
            "source_dir": "/test/source"
        }
        valid, error = validate_sync_job(invalid_job)
        self.assertFalse(valid)
        self.assertEqual(error, "Destination directory is required")

    @patch('subprocess.run')
    def test_run_rsync_command(self, mock_run):
        """Test running an rsync command"""
        # Set up mock subprocess.run
        mock_result = MagicMock()
        mock_result.stdout = "Sync successful"
        mock_run.return_value = mock_result

        # Test successful sync
        success, output = run_rsync_command("/test/source", "/test/dest")
        self.assertTrue(success)
        self.assertEqual(output, "Sync successful")

        # Verify command
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "rsync")
        self.assertIn("-av", args)
        self.assertIn("--delete", args)
        self.assertEqual(args[-2], "/test/source")
        self.assertEqual(args[-1], "/test/dest")

        # Test with custom options
        mock_run.reset_mock()
        success, output = run_rsync_command(
            "/test/source",
            "/test/dest",
            options=["-avzP", "--exclude=*.tmp"]
        )

        # Verify command with custom options
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "rsync")
        self.assertIn("-avzP", args)
        self.assertIn("--exclude=*.tmp", args)

if __name__ == '__main__':
    unittest.main()
