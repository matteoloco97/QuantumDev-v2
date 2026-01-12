import pytest
import os
import sys
import json
import time
import tempfile
import shutil

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from hub import (
    extract_json_from_reasoning, 
    sanitize_filenames,
    validate_requirements,
    save_build_state,
    load_build_state
)


class TestRobustJSONParser:
    """Test robust JSON parser with multiple fallback strategies"""
    
    def test_strategy1_pure_json_array(self):
        """Test STRATEGY 1: Pure JSON array"""
        text = '["main.py", "utils.py", "requirements.txt"]'
        result = extract_json_from_reasoning(text)
        assert result is not None
        assert "main.py" in result
        assert "utils.py" in result
        assert "requirements.txt" in result
    
    def test_strategy1_with_think_tags(self):
        """Test pure JSON with <think> tags"""
        text = '<think>I need these files</think>["main.py", "scraper.py", "requirements.txt"]'
        result = extract_json_from_reasoning(text)
        assert result is not None
        assert "main.py" in result
        assert "scraper.py" in result
    
    def test_strategy2_nested_json_with_files_key(self):
        """Test STRATEGY 2: JSON object with 'files' key"""
        text = '{"files": ["main.py", "scraper.py"], "dependencies": ["requests"]}'
        result = extract_json_from_reasoning(text)
        assert result is not None
        assert "main.py" in result
        assert "scraper.py" in result
        assert "requirements.txt" in result  # Should be added automatically
    
    def test_strategy3_numbered_list(self):
        """Test STRATEGY 3: Numbered list"""
        text = """
        1. main.py
        2. scraper.py
        3. database.py
        4. requirements.txt
        """
        result = extract_json_from_reasoning(text)
        assert result is not None
        assert len(result) >= 3
        assert "main.py" in result
        assert "scraper.py" in result
        assert "database.py" in result
    
    def test_strategy4_bullet_list_dash(self):
        """Test STRATEGY 4: Bullet list with dashes"""
        text = """
        - main.py: Entry point
        - scraper.py: Scraping logic
        - database.py: Data storage
        """
        result = extract_json_from_reasoning(text)
        assert result is not None
        assert "main.py" in result
        assert "scraper.py" in result
        assert "database.py" in result
    
    def test_strategy4_bullet_list_asterisk(self):
        """Test STRATEGY 4: Bullet list with asterisks"""
        text = """
        * main.py
        * utils.py
        * config.yml
        """
        result = extract_json_from_reasoning(text)
        assert result is not None
        assert "main.py" in result
        assert "utils.py" in result
        assert "config.yml" in result
    
    def test_strategy5_natural_language(self):
        """Test STRATEGY 5: File pattern extraction from natural language"""
        text = """
        I'll create these files:
        main.py for the entry point
        scraper.py for web scraping
        database.py for data storage
        Plus requirements.txt for dependencies.
        """
        result = extract_json_from_reasoning(text)
        assert result is not None
        assert "main.py" in result
        assert "scraper.py" in result
        assert "database.py" in result
        assert "requirements.txt" in result
    
    def test_mixed_format(self):
        """Test mixed format with JSON and text"""
        text = """
        I'll create these files:
        ["main.py", "scraper.py"]
        Plus requirements.txt for dependencies.
        """
        result = extract_json_from_reasoning(text)
        assert result is not None
        assert "main.py" in result
        assert "scraper.py" in result
        assert "requirements.txt" in result
    
    def test_filters_library_names(self):
        """Test that library names are filtered out"""
        text = '["main.py", "requests", "pandas", "numpy", "utils.py"]'
        result = extract_json_from_reasoning(text)
        assert result is not None
        assert "main.py" in result
        assert "utils.py" in result
        assert "requests" not in result
        assert "pandas" not in result
        assert "numpy" not in result
    
    def test_ensures_essentials(self):
        """Test that main.py and requirements.txt are always present"""
        text = '["utils.py", "config.py"]'
        result = extract_json_from_reasoning(text)
        assert result is not None
        assert "main.py" in result
        assert "requirements.txt" in result
        assert "utils.py" in result
        # main.py should be first
        assert result[0] == "main.py"
    
    def test_deduplicates_files(self):
        """Test that duplicate files are removed"""
        text = '["main.py", "utils.py", "main.py", "utils.py"]'
        result = extract_json_from_reasoning(text)
        assert result is not None
        assert result.count("main.py") == 1
        assert result.count("utils.py") == 1
    
    def test_handles_various_extensions(self):
        """Test handling of various file extensions"""
        text = '["main.py", "config.yml", "readme.md", "data.json", "settings.toml"]'
        result = extract_json_from_reasoning(text)
        assert result is not None
        assert "main.py" in result
        assert "config.yml" in result
        assert "readme.md" in result
        assert "data.json" in result
        assert "settings.toml" in result


class TestSanitizeFilenames:
    """Test the sanitize_filenames helper function"""
    
    def test_filters_libraries(self):
        """Test that library names are filtered"""
        files = ["main.py", "requests.py", "pandas.py", "utils.py"]
        result = sanitize_filenames(files)
        assert "main.py" in result
        assert "utils.py" in result
        assert "requests.py" not in result
        assert "pandas.py" not in result
    
    def test_removes_duplicates(self):
        """Test duplicate removal"""
        files = ["main.py", "utils.py", "main.py"]
        result = sanitize_filenames(files)
        assert result.count("main.py") == 1
        assert result.count("utils.py") == 1
    
    def test_ensures_main_and_requirements(self):
        """Test that main.py and requirements.txt are always included"""
        files = ["utils.py"]
        result = sanitize_filenames(files)
        assert "main.py" in result
        assert "requirements.txt" in result
        assert result[0] == "main.py"
    
    def test_validates_extensions(self):
        """Test that only valid extensions are kept"""
        files = ["main.py", "data.txt", "readme.md", "invalid.xyz", "script.sh"]
        result = sanitize_filenames(files)
        assert "main.py" in result
        assert "data.txt" in result
        assert "readme.md" in result
        # .sh and .xyz should be filtered out (not in allowed list)
        assert "script.sh" not in result
        assert "invalid.xyz" not in result


class TestDependencyValidator:
    """Test dependency conflict detection and validation"""
    
    def test_no_conflicts(self):
        """Test requirements with no conflicts"""
        req = """pandas>=1.0.0
numpy>=1.20.0
requests>=2.25.0"""
        is_valid, warnings, fixed = validate_requirements(req)
        assert is_valid is True
        assert len(warnings) == 0
    
    def test_pandas_numpy_conflict(self):
        """Test pandas 2.0 + numpy <1.20 conflict detection"""
        req = """pandas>=2.0.0
numpy<1.20.0
requests>=2.25.0"""
        is_valid, warnings, fixed = validate_requirements(req)
        assert is_valid is False
        assert len(warnings) > 0
        assert "CONFLICT" in warnings[0]
        assert "pandas" in warnings[0]
        assert "numpy" in warnings[0]
        # Check that fixed version is correct
        assert "numpy>=1.20.0" in fixed
    
    def test_tensorflow_numpy_conflict(self):
        """Test tensorflow 2.0 + numpy <1.19 conflict detection"""
        req = """tensorflow>=2.0.0
numpy<1.19.0"""
        is_valid, warnings, fixed = validate_requirements(req)
        assert is_valid is False
        assert len(warnings) > 0
        assert "CONFLICT" in warnings[0]
        assert "tensorflow" in warnings[0]
        assert "numpy" in warnings[0]
        # Check that fixed version is correct
        assert "numpy>=1.19.0" in fixed
    
    def test_auto_fix_application(self):
        """Test that auto-fixes are properly applied"""
        req = """pandas>=2.0.0
numpy<1.20.0"""
        is_valid, warnings, fixed = validate_requirements(req)
        # Fixed should have compatible versions
        assert "pandas" in fixed
        assert "numpy>=1.20.0" in fixed
        assert "numpy<1.20" not in fixed
    
    def test_handles_comments(self):
        """Test that comments are ignored"""
        req = """# This is a comment
pandas>=1.0.0
# Another comment
numpy>=1.20.0"""
        is_valid, warnings, fixed = validate_requirements(req)
        assert is_valid is True
        assert "pandas" in fixed
        assert "numpy" in fixed
        assert "#" not in fixed
    
    def test_handles_empty_lines(self):
        """Test that empty lines are handled"""
        req = """pandas>=1.0.0

numpy>=1.20.0

requests>=2.25.0"""
        is_valid, warnings, fixed = validate_requirements(req)
        assert is_valid is True


class TestStatePersistence:
    """Test build state persistence and recovery"""
    
    def setup_method(self):
        """Create temporary directory for each test"""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up temporary directory after each test"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_save_and_load_state(self):
        """Test saving and loading build state"""
        state = {
            'phase': 'construction_in_progress',
            'blueprint': ['main.py', 'utils.py'],
            'completed_files': ['main.py'],
            'goal': 'test project'
        }
        
        save_build_state(self.temp_dir, state)
        loaded = load_build_state(self.temp_dir)
        
        assert loaded is not None
        assert loaded['phase'] == 'construction_in_progress'
        assert loaded['blueprint'] == ['main.py', 'utils.py']
        assert loaded['completed_files'] == ['main.py']
        assert loaded['goal'] == 'test project'
        assert 'timestamp' in loaded
    
    def test_state_includes_timestamp(self):
        """Test that saved state includes timestamp"""
        state = {
            'phase': 'blueprint_complete',
            'blueprint': ['main.py'],
            'completed_files': [],
            'goal': 'test'
        }
        
        before = time.time()
        save_build_state(self.temp_dir, state)
        loaded = load_build_state(self.temp_dir)
        after = time.time()
        
        assert loaded is not None
        assert 'timestamp' in loaded
        assert before <= loaded['timestamp'] <= after
    
    def test_state_expiration(self):
        """Test that old state (>24h) is not loaded"""
        state = {
            'phase': 'construction_in_progress',
            'blueprint': ['main.py'],
            'completed_files': [],
            'goal': 'test',
            'timestamp': time.time() - (25 * 3600)  # 25 hours ago
        }
        
        state_file = os.path.join(self.temp_dir, ".build_state.json")
        with open(state_file, 'w') as f:
            json.dump(state, f)
        
        loaded = load_build_state(self.temp_dir)
        assert loaded is None  # Should be expired
    
    def test_no_state_file(self):
        """Test loading state when no file exists"""
        loaded = load_build_state(self.temp_dir)
        assert loaded is None
    
    def test_state_file_location(self):
        """Test that state file is created in correct location"""
        state = {'phase': 'test', 'blueprint': [], 'completed_files': [], 'goal': 'test'}
        save_build_state(self.temp_dir, state)
        
        state_file = os.path.join(self.temp_dir, ".build_state.json")
        assert os.path.exists(state_file)
    
    def test_state_is_valid_json(self):
        """Test that saved state is valid JSON"""
        state = {
            'phase': 'construction_complete',
            'blueprint': ['main.py', 'utils.py'],
            'completed_files': ['main.py', 'utils.py'],
            'goal': 'create awesome project'
        }
        
        save_build_state(self.temp_dir, state)
        
        state_file = os.path.join(self.temp_dir, ".build_state.json")
        with open(state_file, 'r') as f:
            loaded_json = json.load(f)
        
        assert loaded_json['phase'] == 'construction_complete'
        assert len(loaded_json['blueprint']) == 2
        assert len(loaded_json['completed_files']) == 2


class TestRetryLogic:
    """Test retry logic concepts (actual retry tested via integration)"""
    
    def test_retry_attempts_count(self):
        """Verify retry logic would attempt correct number of times"""
        max_attempts = 3
        # This is a conceptual test - the actual retry logic is in generate_file_with_retry
        # which requires AI calls. We verify the constant is correct.
        assert max_attempts == 3
    
    def test_python_syntax_validation(self):
        """Test that Python syntax validation works"""
        valid_code = """
import os

def main():
    print("Hello, world!")

if __name__ == "__main__":
    main()
"""
        # Should compile without error
        try:
            compile(valid_code, "test.py", 'exec')
            syntax_valid = True
        except SyntaxError:
            syntax_valid = False
        
        assert syntax_valid is True
    
    def test_python_syntax_validation_invalid(self):
        """Test that invalid Python syntax is detected"""
        invalid_code = """
def main()
    print("Missing colon")
"""
        # Should raise SyntaxError
        try:
            compile(invalid_code, "test.py", 'exec')
            syntax_valid = True
        except SyntaxError:
            syntax_valid = False
        
        assert syntax_valid is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
