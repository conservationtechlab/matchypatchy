'''

'''
from PyQt6 import QtCore, QtWidgets

from ..database import mpdb

class SitePopup(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        fullLayout = QtWidgets.QVBoxLayout(self)

        self.container = QtWidgets.QWidget(objectName='container')
        fullLayout.addWidget(self.container, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.container.setSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum,
                                     QtWidgets.QSizePolicy.Policy.Maximum)
        
        layout = QtWidgets.QVBoxLayout(self.container)


        # SITE LIST
        # fetch from database
        self.site_list = QtWidgets.QListWidget()
        layout.addWidget(self.site_list)
        self.site_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.site_list.itemSelectionChanged.connect(self.checkInput)
 
        # buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_survey_new =  QtWidgets.QPushButton("New")
        button_survey_new.clicked.connect(self.add_site)
        button_layout.addWidget(button_survey_new)

        self.button_site_edit =  QtWidgets.QPushButton("Edit")
        self.button_site_edit.clicked.connect(self.edit_site)
        self.button_site_edit.setEnabled(False)
        button_layout.addWidget(self.button_site_edit)

        buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok|QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        button_layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addLayout(button_layout)


    def checkInput(self):
        self.button_site_edit.setEnabled(False)

    def get_sites(self,parent):
        self.sites = parent.mpDB.fetch_rows("site",columns=("id","name",),)
        self.survey_id = parent.active_survey

    def add_site(self):
        dialog = SitePopup(self)
        if dialog.exec():
            confirm = self.mpDB.add_site(dialog.get_name(),dialog.get_lat(),
                                         dialog.get_long(),self.survey_id[0])
            if confirm:
                self.survey_select.addItems([dialog.get_name()])
        del dialog
    
    def edit_site(self):
        return True
    

class SiteFillPopup(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        fullLayout = QtWidgets.QVBoxLayout(self)

        self.container = QtWidgets.QWidget(objectName='container')
        fullLayout.addWidget(self.container, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.container.setSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum,
                                     QtWidgets.QSizePolicy.Policy.Maximum)

        buttonSize = self.fontMetrics().height() 

        layout = QtWidgets.QVBoxLayout(self.container)
        layout.setContentsMargins(
            buttonSize * 2, buttonSize, buttonSize * 2, buttonSize)

        '''
        site_id INTEGER PRIMARY KEY,
                            name TEXT NOT NULL,
                            lat REAL NOT NULL,
                            long REAL NOT NULL,
                            survey_id INTEGER NOT NULL,
        '''

        title = QtWidgets.QLabel(
            'Enter a new Site', 
            objectName='title', alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # name
        layout.addWidget(QtWidgets.QLabel('Name'))
        self.name = QtWidgets.QLineEdit()
        layout.addWidget(self.name)

        #region
        layout.addWidget(QtWidgets.QLabel('Region'))
        self.region = QtWidgets.QLineEdit()
        layout.addWidget(self.region)

        # start year
        layout.addWidget(QtWidgets.QLabel('Start Year'))
        self.year_start = QtWidgets.QLineEdit()
        layout.addWidget(self.year_start)

        layout.addWidget(QtWidgets.QLabel(parent.survey_id))
        self.year_end = QtWidgets.QLineEdit()
        layout.addWidget(self.year_end)

        buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok|QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept_verify)
        buttonBox.rejected.connect(self.reject)
        self.okButton = buttonBox.button(buttonBox.StandardButton.Ok)
        self.okButton.setEnabled(False)

        self.name.textChanged.connect(self.checkInput)
        self.region.textChanged.connect(self.checkInput)
        self.year_start.textChanged.connect(self.checkInput)
        self.year_end.textChanged.connect(self.checkInput)

        self.name.returnPressed.connect(lambda:
                self.region.setFocus())
        self.region.returnPressed.connect(lambda:
                self.year_start.setFocus())
        self.year_start.returnPressed.connect(lambda:
                self.year_end.setFocus())
        self.year_end.returnPressed.connect(self.accept_verify)

        self.name.setFocus()

    def checkInput(self):
        # year end not necessary
        self.okButton.setEnabled(bool(self.get_name() and self.get_region() and self.get_year_start()))

    def get_name(self):
        return self.name.text()

    def get_region(self):
        return self.region.text()
    
    def get_year_start(self):
        return self.year_start.text()

    def get_year_end(self):
        return self.year_end.text()

    def accept_verify(self):
        if self.get_name() and self.get_region() and self.get_year_start():
            self.accept()
