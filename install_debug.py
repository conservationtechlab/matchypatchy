import sys
from matchypatchy import tools


required_major = None
required_minor = None
if len(sys.argv) >= 3:
    try:
        required_major = int(sys.argv[1])
        required_minor = int(sys.argv[2])
    except Exception:
        required_major = None
        required_minor = None

ok, msg, info = tools.check_cuda(required_major, required_minor, require_gpu=True)
print("CUDA check result:", ok, msg, info)
if not ok:
    # Show a dialog in GUI mode; otherwise print
    tools.user_message_box("CUDA check", msg)
    # Exit with non-zero to allow installers to detect failure
    sys.exit(2)
sys.exit(0)