import unittest
import os
import sys
import tempfile
import shutil
from unittest.mock import MagicMock, patch

# Ensure headless operation
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Fix Python path to find src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

class TestSyncManager(unittest.TestCase):

    def setUp(self):
        """Set up test environment"""
        # Create a patch for subprocess.Popen
        self.popen_patcher = patch('subprocess.Popen')
        self.mock_popen = self.popen_patcher.start()

        # Set up mock process
        self.mock_process = MagicMock()
        self.mock_process.communicate.return_value = ("Output", "")
        self.mock_process.returncode = 0
        self.mock_popen.return_value = self.mock_process

        # Import the actual SyncManager to test
        from src.sync_manager import SyncManager
        self.sync_manager = SyncManager()

    def tearDown(self):
        """Clean up after tests"""
        self.popen_patcher.stop()

    def test_add_job(self):
        """Test adding a sync job"""
        self.sync_manager.add_job(
            name="test-job",
            source_dir="/test/source",
            dest_dir="/test/dest",
            options=["-avz"],
            auto_sync=True,
            interval=30
        )

        jobs = self.sync_manager.get_jobs()
        self.assertIn("test-job", jobs)
        job = jobs["test-job"]
        self.assertEqual(job["source_dir"], "/test/source")
        self.assertEqual(job["dest_dir"], "/test/dest")
        self.assertEqual(job["options"], ["-avz"])
        self.assertTrue(job["auto_sync"])
        self.assertEqual(job["interval"], 30)

    def test_add_job_with_default_options(self):
        """Test adding a job with default options"""
        self.sync_manager.add_job(
            name="test-job",
            source_dir="/test/source",
            dest_dir="/test/dest"
        )

        jobs = self.sync_manager.get_jobs()
        self.assertIn("test-job", jobs)
        self.assertEqual(jobs["test-job"]["options"], ["-av", "--delete"])

    def test_add_job_with_options(self):
        """Test adding a job with custom options"""
        self.sync_manager.add_job(
            name="test-job",
            source_dir="/test/source",
            dest_dir="/test/dest",
            options=["-avzP", "--exclude=*.tmp"]
        )

        jobs = self.sync_manager.get_jobs()
        self.assertIn("test-job", jobs)
        self.assertEqual(jobs["test-job"]["options"], ["-avzP", "--exclude=*.tmp"])

    def test_add_job_with_auto_sync(self):
        """Test adding a job with auto sync"""
        self.sync_manager.add_job(
            name="test-job",
            source_dir="/test/source",
            dest_dir="/test/dest",
            auto_sync=True,
            interval=15
        )

        jobs = self.sync_manager.get_jobs()
        self.assertIn("test-job", jobs)
        self.assertTrue(jobs["test-job"]["auto_sync"])
        self.assertEqual(jobs["test-job"]["interval"], 15)

    def test_remove_job(self):
        """Test removing a job"""
        # Add a job first
        self.sync_manager.add_job(
            name="test-job",
            source_dir="/test/source",
            dest_dir="/test/dest"
        )

        # Make sure it's there
        self.assertIn("test-job", self.sync_manager.get_jobs())

        # Remove it
        self.sync_manager.remove_job("test-job")

        # Make sure it's gone
        self.assertNotIn("test-job", self.sync_manager.get_jobs())

    def test_clear_jobs(self):
        """Test clearing all jobs"""
        # Add a few jobs
        self.sync_manager.add_job(
            name="job1",
            source_dir="/test/source1",
            dest_dir="/test/dest1"
        )

        self.sync_manager.add_job(
            name="job2",
            source_dir="/test/source2",
            dest_dir="/test/dest2"
        )

        # Make sure they're there
        self.assertEqual(len(self.sync_manager.get_jobs()), 2)

        # Clear all jobs
        self.sync_manager.clear_jobs()

        # Make sure they're gone
        self.assertEqual(len(self.sync_manager.get_jobs()), 0)

    @patch('os.path.exists')
    def test_start_sync_success(self, mock_exists):
        """Test successful sync operation"""
        # Set up mocks
        mock_exists.return_value = True

        # Connect signals to mocks
        started_handler = MagicMock()
        finished_handler = MagicMock()
        self.sync_manager.sync_started.connect(started_handler)
        self.sync_manager.sync_finished.connect(finished_handler)

        # Add a job
        self.sync_manager.add_job(
            name="test-job",
            source_dir="/test/source",
            dest_dir="/test/dest"
        )

        # Reset the mock to clear any previous calls
        self.mock_popen.reset_mock()

        # Start sync
        self.sync_manager.start_sync("test-job")

        # Verify the process was started correctly
        self.assertEqual(self.mock_popen.call_count, 1)

        args, kwargs = self.mock_popen.call_args

        # Check rsync command
        self.assertEqual(args[0][0], "rsync")
        self.assertIn("-av", args[0][1:3])
        self.assertIn("--delete", args[0][1:3])
        self.assertEqual(args[0][-2], "/test/source")
        self.assertEqual(args[0][-1], "/test/dest")

        # Check signals
        self.assertEqual(started_handler.call_count, 1)
        started_handler.assert_called_with("test-job")

        self.assertEqual(finished_handler.call_count, 1)
        finished_handler.assert_called_with("test-job", True)

    @patch('os.path.exists')
    def test_start_sync_error(self, mock_exists):
        """Test sync operation with error"""
        # Set up mocks
        mock_exists.return_value = True

        # Create a temporary directory structure for better error message matching
        temp_dir = tempfile.mkdtemp()
        try:
            # Make subprocess.Popen return an error
            self.mock_process.returncode = 1
            self.mock_process.communicate.return_value = ("", "Permission denied")

            # Connect signals to mocks
            error_handler = MagicMock()
            finished_handler = MagicMock()
            self.sync_manager.sync_error.connect(error_handler)
            self.sync_manager.sync_finished.connect(finished_handler)

            # Add a job
            self.sync_manager.add_job(
                name="test-job",
                source_dir="/test/source",
                dest_dir="/test/dest"
            )

            # Start sync
            self.sync_manager.start_sync("test-job")

            # Verify error was handled
            self.assertEqual(error_handler.call_count, 1)
            error_args = error_handler.call_args[0]
            self.assertEqual(error_args[0], "test-job")
            self.assertEqual(error_args[1], "Permission denied")

            self.assertEqual(finished_handler.call_count, 1)
            finished_handler.assert_called_with("test-job", False)
        finally:
            # Clean up
            shutil.rmtree(temp_dir)

    @patch('os.path.exists')
    def test_start_sync_nonexistent_source(self, mock_exists):
        """Test starting sync with a source directory that doesn't exist"""
        # Set up mocks
        mock_exists.return_value = False

        # Connect signals to mocks
        error_handler = MagicMock()
        self.sync_manager.sync_error.connect(error_handler)

        # Add a job
        self.sync_manager.add_job(
            name="test-job",
            source_dir="/nonexistent/source",
            dest_dir="/test/dest"
        )

        # Start sync
        self.sync_manager.start_sync("test-job")

        # Verify error handling
        self.assertEqual(error_handler.call_count, 1)
        error_args = error_handler.call_args[0]
        self.assertEqual(error_args[0], "test-job")
        self.assertIn("Source directory does not exist", error_args[1])

    def test_start_sync_nonexistent_job(self):
        """Test starting sync for a job that doesn't exist"""
        # Connect signals to mocks
        error_handler = MagicMock()
        self.sync_manager.sync_error.connect(error_handler)

        # Start sync for non-existent job
        self.sync_manager.start_sync("nonexistent-job")

        # Verify error handling
        self.assertEqual(error_handler.call_count, 1)
        error_handler.assert_called_with("nonexistent-job", "Sync job not found")

    @patch('os.path.exists')
    def test_start_all_sync(self, mock_exists):
        """Test starting all sync jobs"""
        # Set up mocks
        mock_exists.return_value = True

        # Add a few jobs
        self.sync_manager.add_job(
            name="job1",
            source_dir="/test/source1",
            dest_dir="/test/dest1"
        )

        self.sync_manager.add_job(
            name="job2",
            source_dir="/test/source2",
            dest_dir="/test/dest2"
        )

        # Connect signals to mocks
        started_handler = MagicMock()
        self.sync_manager.sync_started.connect(started_handler)

        # Start all sync jobs
        self.sync_manager.start_all_sync()

        # Verify all jobs were started
        self.assertEqual(started_handler.call_count, 2)

        # Get job names from calls
        started_jobs = [call_args[0][0] for call_args in started_handler.call_args_list]
        self.assertIn("job1", started_jobs)
        self.assertIn("job2", started_jobs)

    @patch('subprocess.Popen')
    def test_exception_handling(self, mock_popen):
        """Test handling of exceptions during sync process"""
        # Set up mocks to raise an exception
        mock_popen.side_effect = Exception("Test exception")

        # Connect signals to mocks
        error_handler = MagicMock()
        finished_handler = MagicMock()
        self.sync_manager.sync_error.connect(error_handler)
        self.sync_manager.sync_finished.connect(finished_handler)

        # Add a job
        self.sync_manager.add_job(
            name="test-job",
            source_dir="/test/source",
            dest_dir="/test/dest"
        )

        # Start sync
        with patch('os.path.exists', return_value=True):
            self.sync_manager.start_sync("test-job")

        # Verify error handling
        self.assertEqual(error_handler.call_count, 1)
        self.assertEqual(error_handler.call_args[0][0], "test-job")
        self.assertEqual(error_handler.call_args[0][1], "Test exception")

        self.assertEqual(finished_handler.call_count, 1)
        finished_handler.assert_called_with("test-job", False)

if __name__ == '__main__':
    unittest.main()
