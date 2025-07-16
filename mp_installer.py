'''
MP Installer
'''
import time
start_time = time.time()
import sys
import os
os.environ["CHROMA_TELEMETRY"] = "FALSE"

import torch
print("CUDA available:", torch.cuda.is_available())
print("cuDNN enabled:", torch.backends.cudnn.enabled)
print("cuDNN version:", torch.backends.cudnn.version())
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False
torch.set_num_threads(1)
torch.set_num_interop_threads(1)

try:
    x = torch.randn(1, 3, 224, 224).cuda()
    y = torch.randn(1, 3, 224, 224).cuda()
    z = x + y
    print("Inference test passed:", z.shape)
except Exception as e:
    print("Runtime error:", e)


from PyQt6.QtWidgets import QApplication

# START GUI
from matchypatchy.gui import MainWindow, AlertPopup
from matchypatchy.database import mpdb
from matchypatchy import config
from matchypatchy.algo import models

def main():
    app = QApplication(sys.argv)
    cfg = config.initiate()
    mpDB = mpdb.MatchyPatchyDB(cfg['DB_DIR'])
    window = MainWindow(mpDB)
    window.show()
    
    if not mpDB.key:
        dialog = AlertPopup(window, prompt='Existing database contains an error. Please select a valid database in the configuration settings.')
        if dialog.exec():
            del dialog
    
    models.update_model_yml()
    print(f"Startup took {time.time() - start_time:.2f} seconds")
    sys.exit(app.exec())
    

if __name__ == "__main__":
    main()
