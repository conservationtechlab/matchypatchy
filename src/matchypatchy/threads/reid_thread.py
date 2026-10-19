"""
PairX visual explanation thread, disabled until torch is returned as a dependency

Viewpoint and re-id embeddings run in process_thread.ProcessThread
"""

# from matchypatchy.pairx.core import explain
# from matchypatchy.pairx import xai_dataset


"""
# NOTE: Currently disabled until torch is returned as a dependency
class PairXThread(QThread):
    explained_img = pyqtSignal(list)  # Signal to update the alert prompt
    done = pyqtSignal()

    def __init__(self, query, match, model):
        super().__init__()
        self.query = query
        self.match = match
        self.model = model
        self.device = config.load_cfg('DEVICE')
        self.img_transforms = transforms.Compose([transforms.Resize((440, 440)),
                                                  transforms.ToTensor(),
                                                  transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                                                       std=[0.229, 0.224, 0.225])])

    def run(self):
        explained_imgs = self.explain()
        self.explained_img.emit(explained_imgs[0])
        self.done.emit()

    def explain(self):
        img_0, img_1, img_np_0, img_np_1 = xai_dataset.get_img_pair_from_paths(self.device, self.query, self.match,
                                                                               (440,440), self.img_transforms)
        explained_imgs = explain(self.device, img_0, img_1,
                                 img_np_0, img_np_1,
                                 self.model, ["backbone.blocks.3"],
                                 k_lines=20, k_colors=10)
        return explained_imgs

    def get_bbox(self, roi):
        '''
        Return the bbox coordinates for a given roi row
        '''
        return roi[['bbox_x', 'bbox_y', 'bbox_w', 'bbox_h']]
"""
