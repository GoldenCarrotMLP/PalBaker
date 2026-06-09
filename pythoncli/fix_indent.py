with open('palbaker_cli.py', 'r') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'elif args.action == "set-icon":' in line:
        lines[i] = '            elif args.action == "set-icon":\n'
    if 'if not args.path:' in line and 'set-icon' not in line:
        pass # Wait, let's just strip the extra 4 spaces from line 221 to 230
        
# A safer way
import re
content = "".join(lines)
content = content.replace('            elif args.action == "set-icon":', 'TMP_SET_ICON')
content = content.replace('                        elif args.action == "set-icon":', 'TMP_SET_ICON')

replacement = """            elif args.action == "set-icon":
                if not args.path:
                    error_print("Missing --path for set-icon")
                    sys.exit(1)
                import shutil
                icon_dir = os.path.join(mod_data["mod_dir"], "Resources")
                os.makedirs(icon_dir, exist_ok=True)
                dest = os.path.join(icon_dir, "icon.png")
                shutil.copy2(args.path, dest)
                json_print({"status": "success", "message": f"Icon set for {args.mod}"})"""

content = re.sub(r'TMP_SET_ICON\n                if not args\.path:.*?(?=            else:)', replacement + '\n', content, flags=re.DOTALL)
with open('palbaker_cli.py', 'w') as f:
    f.write(content)
