# Fixing Unreal Engine Connections

PalBaker communicates with your running Unreal Engine Editor session in real-time to automate asset imports, material links, and C++ rigging compiles. If your pipeline fails to connect or times out, follow this troubleshooting guide.

## 1. Verify Project Settings
Open your ModKit project in Unreal Editor and verify that Python remote execution scripting is checked:
- Go to **Edit -> Project Settings**.
- Search for the **Python** category.
- Ensure **Enable Remote Execution** is checked.

---

## 2. Network Adapter Conflict (Common Cause)
If you utilize virtual network adapters (such as WSL, Hyper-V, VMware, or virtual VR headsets), they frequently hijack local UDP multicast traffic. Python's socket library can bind to these virtual interfaces instead of your loopback adapter, blocking connection.

**To resolve this:**
- Open your Windows **Control Panel**.
- Navigate to **Network and Internet -> Network Connections**.
- Locate any non-essential virtual adapters (e.g., *Oculus Virtual Device*, *vEthernet*, or *VMware Network Adapter*).
- Right-click and select **Disable**.
- Restart Unreal Editor and try again!

---

## 3. Configure Firewall Rules
Ensure that both your configured `UnrealEditor.exe` and your active `python.exe` have Private and Public network permissions allowed in your Windows Defender Firewall panel.