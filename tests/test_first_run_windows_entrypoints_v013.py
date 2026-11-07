"""Windows PowerShell 5.1 parser and streamlined launcher contracts."""
from pathlib import Path
import os
import shutil
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[1]


def test_first_run_gui_encoding_and_safe_quote():
    raw=(ROOT/'scripts/first_run_gui.ps1').read_bytes()
    assert raw.startswith(b'\xef\xbb\xbf')  # Windows PowerShell 5.1 must decode multilingual source.
    text=raw.decode('utf-8-sig')
    # PowerShell treats curly single quotes as actual quote delimiters, even inside an ASCII-quoted string.
    assert not any(c in text for c in ('\u2018', '\u2019'))
    assert "project''s GitHub Releases" in text


@pytest.mark.skipif(os.name!='nt' or not shutil.which('powershell.exe'), reason='Windows PowerShell parser is available only on Windows')
def test_all_release_powershell_scripts_parse_on_windows():
    files=sorted((ROOT/'scripts').glob('*.ps1'))
    for p in files:
        escaped=str(p).replace("'","''")
        script=("$tokens=$null;$errors=$null;"+
                "[System.Management.Automation.Language.Parser]::ParseFile('"+escaped+"',[ref]$tokens,[ref]$errors)|Out-Null;"+
                "if($errors.Count -gt 0){$errors|ForEach-Object {Write-Error $_.Message};exit 1}")
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],
                              text=True,capture_output=True,timeout=20)
        assert result.returncode==0, f'{p.name}: {result.stdout} {result.stderr}'


def test_root_has_three_user_launchers_and_advanced_works():
    # Only release-allowlisted entry points define the public product layout.
    # A developer may have private local repair .cmd files in the working tree;
    # they must not make source verification fail or become release assets.
    manifest=(ROOT/'release/public_source_files.txt').read_text(encoding='utf-8')
    public={line.strip() for line in manifest.splitlines()
            if line.strip() and not line.lstrip().startswith('#')}
    expected={'First Run Setup.cmd','Start AnimeVoiceTutor.cmd','Stop AnimeVoiceTutor.cmd'}
    released_root_cmds={name for name in public if '/' not in name and name.lower().endswith('.cmd')}
    assert released_root_cmds==expected
    assert all((ROOT/name).is_file() for name in expected)
    advanced={name.removeprefix('advanced/') for name in public
              if name.startswith('advanced/') and name.lower().endswith('.cmd')}
    assert len(advanced)==8
    for name in advanced:
        f=ROOT/'advanced'/name
        assert f.is_file()
        contents=f.read_text(encoding='utf-8')
        assert 'cd /d "%~dp0.."' in contents
        assert '%~dp0..\\scripts\\' in contents or 'First Run Setup.cmd' in contents


def test_setup_close_button_is_error_guarded_and_uses_the_actual_owner_form():
    text=(ROOT/'scripts/first_run_gui.ps1').read_text(encoding='utf-8-sig')
    assert '$close.Add_Click({' in text
    assert '$sender.FindForm()' in text
    assert '$close.Add_Click({$form.Close()})' not in text
    assert "Join-Path $logDir 'gui_errors.log'" in text
    assert '$form.Add_FormClosing({' in text
    assert '$script:taskProcess.HasExited' in text
    assert '$timer.Dispose()' in text
    assert 'exit 0' in text
    for key in ("'closeerror' = 'The setup", "'closeerror' = '安装", "'closeerror' = 'セット"):
        assert key in text


def test_language_switch_label_is_in_english_for_every_locale():
    text=(ROOT/'scripts/first_run_gui.ps1').read_text(encoding='utf-8-sig')
    assert text.count("'lang' = 'Language'")==3
    assert "$languageLabel.Text='Language'" in text
    assert 'language.Items.Add' in text
    assert "'advanced' = '高级选项'" in text
    assert "'advanced' = '詳細設定'" in text
    assert "'advanced' = 'Advanced options'" in text
    assert "'character_release'" in (ROOT/'scripts/first_run_tasks.ps1').read_text(encoding='utf-8-sig')
