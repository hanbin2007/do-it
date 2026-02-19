"""Create a desktop shortcut (.lnk) pointing to start.bat.

Run once:  python create_shortcut.py
"""

import os
import subprocess
import sys


def create_shortcut() -> None:
    project_dir = os.path.dirname(os.path.abspath(__file__))
    bat_path = os.path.join(project_dir, "start.bat")

    if not os.path.isfile(bat_path):
        print(f"Error: {bat_path} not found.")
        sys.exit(1)

    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    shortcut_path = os.path.join(desktop, "Do-It 运动计数器.lnk")

    # Use PowerShell to create a .lnk file (no extra dependencies)
    ps_script = f"""
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut('{shortcut_path}')
$sc.TargetPath = '{bat_path}'
$sc.WorkingDirectory = '{project_dir}'
$sc.WindowStyle = 7
$sc.Description = 'Do-It Motion Counter'
$sc.Save()
"""
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"✅ 快捷方式已创建: {shortcut_path}")
    except subprocess.CalledProcessError as exc:
        print(f"Failed to create shortcut: {exc.stderr}")
        sys.exit(1)


if __name__ == "__main__":
    create_shortcut()
