#!/usr/bin/env python3
"""
🔧 Script di riparazione file corrotti con escape sequences
"""
import os
import glob
import codecs
import sys


def fix_file(filepath):
    """Fix singolo file con escape sequences"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Controlla se è corrotto
        if '\\n' in content and content.count('\\n') > content.count('\n') * 0.3:
            print(f"🔧 Fixing {filepath}...")
            
            # Rimuovi backticks residui
            content = content.replace('```python\\n', '').replace('```', '')
            
            # Unescape
            try:
                fixed = codecs.decode(content, 'unicode_escape')
            except Exception as e:
                print(f"   ⚠️ Fallback to manual unescape due to: {e}")
                fixed = content.replace('\\n', '\n').replace('\\t', '\t')
            
            # Backup originale
            backup_path = filepath + '.backup'
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"   💾 Backup salvato in {backup_path}")
            
            # Salva versione corretta
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(fixed)
            
            print(f"✅ Fixed {filepath}")
            return True
        return False
    except Exception as e:
        print(f"❌ Error processing {filepath}: {e}")
        return False


def main():
    """Main function"""
    print("=" * 70)
    print("🔧 QUANTUM DEV - File Corruption Repair Tool")
    print("=" * 70)
    print()
    
    # Find all Python files in projects directory
    py_files = glob.glob("projects/**/*.py", recursive=True)
    
    if not py_files:
        print("⚠️ No Python files found in projects/ directory")
        return
    
    print(f"📁 Found {len(py_files)} Python files")
    print()
    
    # Process each file
    fixed_count = 0
    for filepath in py_files:
        if fix_file(filepath):
            fixed_count += 1
    
    # Summary
    print()
    print("=" * 70)
    print(f"✅ Repair complete: {fixed_count}/{len(py_files)} files repaired")
    print("=" * 70)
    
    if fixed_count > 0:
        print()
        print("💡 Tip: Backup files (.backup) have been created.")
        print("   If everything works, you can delete them with:")
        print("   find projects -name '*.backup' -delete")


if __name__ == "__main__":
    # Change to repository root if running from anywhere
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    main()
