'''

'''
from PyQt6 import QtCore, QtWidgets

from ..database import mpdb
from .popup_confirm import ConfirmPopup

class SitePopup(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Sites")
        fullLayout = QtWidgets.QVBoxLayout(self)

        self.container = QtWidgets.QWidget(objectName='container')
        fullLayout.addWidget(self.container, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.container.setSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum,
                                     QtWidgets.QSizePolicy.Policy.Maximum)
        
        layout = QtWidgets.QVBoxLayout(self.container)

        # SITE LIST
        self.survey_id = parent.active_survey
        self.mpDB = parent.mpDB
        # fetch from database
        self.site_select = QtWidgets.QListWidget()
        layout.addWidget(self.site_select)
        self.site_select.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.site_select.itemSelectionChanged.connect(self.set_editdel)
 
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_survey_new =  QtWidgets.QPushButton("New")
        button_survey_new.clicked.connect(self.add_site)
        button_layout.addWidget(button_survey_new)

        self.button_site_edit = QtWidgets.QPushButton("Edit")
        self.button_site_edit.clicked.connect(self.edit_site)
        self.button_site_edit.setEnabled(False)
        button_layout.addWidget(self.button_site_edit)
        
        self.button_site_del = QtWidgets.QPushButton("Delete")
        self.button_site_del.clicked.connect(self.delete_site)
        self.button_site_del.setEnabled(False)
        button_layout.addWidget(self.button_site_del)

        buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok|QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        button_layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addLayout(button_layout)
        
        self.update_sites()


    def set_editdel(self):
        # currentRow() returns -1 if nothing selected
        flag = bool(self.site_select.currentRow()+1) 
        self.button_site_edit.setEnabled(flag)
        self.button_site_del.setEnabled(flag)

    def update_sites(self):
        self.site_select.clear()
        cond = f'survey_id={self.survey_id[0]}'
        sites = self.mpDB.fetch_rows("site", cond, columns="id, name")
        self.site_list = dict(sites)
        self.site_list_ordered = sites
        if self.site_list_ordered:
            self.site_select.addItems([el[1] for el in sites])
        self.set_editdel()   
        

    def add_site(self):
        dialog = SiteFillPopup(self)
        if dialog.exec():
            confirm = self.mpDB.add_site(dialog.get_name(),dialog.get_lat(),
                                         dialog.get_long(),self.survey_id[0])
            if confirm:
                self.site_select.addItems([dialog.get_name()])
        del dialog
    
    def edit_site(self):
        return True
    
    def delete_site(self):
        selected = self.site_select.currentItem().text()
        prompt = f'Are you sure you want to delete {selected}?'
        print(prompt)
        dialog = ConfirmPopup(self, prompt)
        if dialog.exec():
            row = self.site_list_ordered[self.site_select.currentRow()][0]
            cond = f'id={row}'
            self.mpDB.delete("site",cond)
        del dialog
        self.update_sites()


class SiteFillPopup(QtWidgets.QDialog):
    def __init__(self, parent, name=None, lat=None, long=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Site")
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
        self.name.setText(name)
        layout.addWidget(self.name)

        #region
        layout.addWidget(QtWidgets.QLabel('Latitude'))
        self.lat = QtWidgets.QLineEdit()
        self.lat.setText(lat)
        layout.addWidget(self.lat)

        # start year
        layout.addWidget(QtWidgets.QLabel('Longitude'))
        self.long = QtWidgets.QLineEdit()
        self.long.setText(long)
        layout.addWidget(self.long)

        buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok|QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept_verify)
        buttonBox.rejected.connect(self.reject)
        self.okButton = buttonBox.button(buttonBox.StandardButton.Ok)
        self.okButton.setEnabled(False)

        self.name.textChanged.connect(self.checkInput)
        self.lat.textChanged.connect(self.checkInput)
        self.long.textChanged.connect(self.checkInput)

        self.name.returnPressed.connect(lambda:
                self.lat.setFocus())
        self.lat.returnPressed.connect(lambda:
                self.long.setFocus())
        self.long.returnPressed.connect(self.accept_verify)

        self.name.setFocus()

    def checkInput(self):
        # year end not necessary
        self.okButton.setEnabled(bool(self.get_name() and self.get_lat() and self.get_long()))

    def get_name(self):
        return self.name.text()

    def get_lat(self):
        return self.lat.text()
    
    def get_long(self):
        return self.long.text()

    def accept_verify(self):
        if self.get_name() and self.get_lat() and self.get_long():
            self.accept()
