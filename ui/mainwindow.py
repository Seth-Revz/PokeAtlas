import pathlib
import platform

from PySide6.QtCore import (
    Qt,
    QDir,
    QFile,
    QFileSystemWatcher,
    QPoint,
    QProcess,
    QSize,
    QTimer,
    QSortFilterProxyModel,
)

from PySide6.QtGui import (
    QAction,
    QDesktopServices,
    QIcon,
    QPixmap, 
    QResizeEvent,
)
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QLabel,
    QToolBar,
    QFileDialog,
    QFileSystemModel,
    QLineEdit,
    QListView,
    QHBoxLayout,
    QVBoxLayout,
    QSlider,
    QStyledItemDelegate, 
    QFileIconProvider,
    QSizePolicy,
    QMessageBox,
)

from pokatlas import decomp, rebuild

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 400

class Label(QLabel):

    def __init__(self):
        super(Label, self).__init__()
        self.pixmap_width: int = 1
        self.pixmapHeight: int = 1

    def setPixmap(self, pm: QPixmap) -> None:
        self.pixmap_width = pm.width()
        self.pixmapHeight = pm.height()

        self.updateMargins()
        super(Label, self).setPixmap(pm)

    def resizeEvent(self, a0: QResizeEvent) -> None:
        self.updateMargins()
        super(Label, self).resizeEvent(a0)

    def updateMargins(self):
        if self.pixmap() is None:
            return
        pixmapWidth = self.pixmap().width()
        pixmapHeight = self.pixmap().height()
        if pixmapWidth <= 0 or pixmapHeight <= 0:
            return
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return

        if w * pixmapHeight > h * pixmapWidth:
            m = int((w - (pixmapWidth * h / pixmapHeight)) / 2)
            self.setContentsMargins(m, 0, m, 0)
        else:
            m = int((h - (pixmapHeight * w / pixmapWidth)) / 2)
            self.setContentsMargins(0, m, 0, m)

class NameDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        if isinstance(index.model(), QFileSystemModel):
            if not index.model().isDir(index):
                option.text = index.model().fileInfo(index).baseName()

    def setEditorData(self, editor, index):
        if isinstance(index.model(), QFileSystemModel):
            if not index.model().isDir(index):
                editor.setText(index.model().fileInfo(index).baseName())
            else:
                super().setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        if isinstance(model, QFileSystemModel):
            fi = model.fileInfo(index)
            if not model.isDir(index):
                model.setData(index, editor.text() + "." + fi.suffix())
            else:
                super().setModelData(editor, model.index)

class EmptyIconProvider(QFileIconProvider):
    def icon(self, _):
        return QIcon()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.atlas_dir = None
        self.sprites_dir = None
        self.output_dir = None
        self.selected_sprite_filename = None

        self.setupUI()

    def setupUI(self):
        self.setWindowIcon(QIcon('./ui/icon.png'))
        self.setWindowTitle('Pokatlas')
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)

        self.toolbar = QToolBar('Main Toolbar')
        self.toolbar.setMovable(False)
        self.toolbar.toggleViewAction().setEnabled(False)
        self.addToolBar(self.toolbar)

        self.open_atlas_action = QAction('Open Atlas', self)
        self.open_atlas_action.triggered.connect(self.openAtlas)
        self.toolbar.addAction(self.open_atlas_action)

        self.replace_action = QAction('Replace Sprite', self)
        self.replace_action.triggered.connect(self.replaceSingleSprite)
        self.replace_action.setVisible(False)
        self.toolbar.addAction(self.replace_action)

        self.save_atlas_action = QAction('Save Atlas', self)
        self.save_atlas_action.triggered.connect(self.saveAtlas)
        self.save_atlas_action.setVisible(False)
        self.toolbar.addAction(self.save_atlas_action)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar.addWidget(spacer)

        self.open_sprite_folder_action = QAction('Sprite Folder', self)
        self.open_sprite_folder_action.triggered.connect(self.openSpriteFolder)
        self.open_sprite_folder_action.setVisible(False)
        self.toolbar.addAction(self.open_sprite_folder_action)

        self.mass_replace_action = QAction('Mass Replace', self)
        self.mass_replace_action.triggered.connect(self.replaceMultipleSprites)
        self.mass_replace_action.setVisible(False)
        self.toolbar.addAction(self.mass_replace_action)

        widget = QWidget(self)
        layout = QVBoxLayout(widget)

        label = QLabel()
        label.setText("<font color='grey'>Open main.atlas<br /><br />Replace Sprites<br /><br />Save Spritesheet</font>")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        font = self.font()
        font.setPointSize(13)
        label.setFont(font)

        layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(widget)

    def displayAtlas(self):
        widget = QWidget(self)
        self.model = QFileSystemModel()
        self.model.setIconProvider(EmptyIconProvider())
        self.model_root_path = self.model.setRootPath(self.sprites_dir)

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setRecursiveFilteringEnabled(True)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        self.sprite_list = QListView()
        self.sprite_list.setModel(self.proxy_model)
        self.sprite_list.setRootIndex(self.proxy_model.mapFromSource(self.model.index(self.sprites_dir)))
        delegate = NameDelegate(self.sprite_list)
        self.sprite_list.setItemDelegate(delegate)
        self.sprite_list.setViewMode(QListView.ViewMode.ListMode)
        self.sprite_list.setResizeMode(QListView.ResizeMode.Adjust)
        self.sprite_list.setMinimumWidth(WINDOW_WIDTH // 3.5)
        self.sprite_list.setMaximumWidth(WINDOW_WIDTH // 3.5)
        self.sprite_list.selectionModel().currentChanged.connect(self.listClicked)
        self.sprite_list.doubleClicked.connect(self.replaceSingleSprite)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText('Filter')
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setMinimumWidth(WINDOW_WIDTH // 3.5)
        self.search_edit.setMaximumWidth(WINDOW_WIDTH // 3.5)
        self.search_edit.textEdited.connect(self.searchList)

        file_vbox = QVBoxLayout()
        file_vbox.addWidget(self.search_edit)
        file_vbox.addWidget(self.sprite_list)

        self.sprite_image_label = Label() 
        pixmap = QPixmap(f'{self.atlas_dir}/main.png')
        self.sprite_image_label.setPixmap(pixmap.scaled(QSize(WINDOW_WIDTH, WINDOW_HEIGHT), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.sprite_image_label.setScaledContents(True)
        self.sprite_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.scaleSlider = QSlider(Qt.Orientation.Horizontal)
        self.scaleSlider.setRange(1, 12)
        self.scaleSlider.setValue(1)
        self.scaleSlider.valueChanged.connect(self.scaleSprite)
        self.scaleSlider.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Maximum)
        self.scaleSlider.setVisible(False)

        self.size_label = QLabel()
        self.size_label.setStyleSheet("QLabel{font-size: 14pt;}")
        self.size_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Maximum)
        self.size_label.setScaledContents(True)
        self.size_label.setAlignment(Qt.AlignmentFlag.AlignCenter|Qt.AlignmentFlag.AlignBottom)

        label_vbox = QVBoxLayout()
        label_vbox.addStretch()
        label_vbox.addWidget(self.sprite_image_label, alignment=Qt.AlignmentFlag.AlignCenter)
        label_vbox.addStretch()
        label_vbox.addWidget(self.scaleSlider, alignment=Qt.AlignmentFlag.AlignCenter|Qt.AlignmentFlag.AlignBottom)
        label_vbox.addWidget(self.size_label, alignment=Qt.AlignmentFlag.AlignCenter|Qt.AlignmentFlag.AlignBottom)

        layout = QHBoxLayout(widget)
        layout.addLayout(file_vbox)
        layout.addLayout(label_vbox, 2)

        self.setCentralWidget(widget)

        if self.replace_action.isVisible():
            self.replace_action.setVisible(False)
        if self.save_atlas_action.isVisible():
            self.save_atlas_action.setVisible(False)
        if not self.open_sprite_folder_action.isVisible():
            self.open_sprite_folder_action.setVisible(True)
        if not self.mass_replace_action.isVisible():
            self.mass_replace_action.setVisible(True)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(1000)
        self.refresh_timer.timeout.connect(self.refreshSpritePreview)

        self.fs_watcher = QFileSystemWatcher()
        self.fs_watcher.fileChanged.connect(self.setSaveButtonVisible)

    def openAtlas(self):

        atlas_filename = QFileDialog.getOpenFileName(self, 'Open main.atlas')[0]

        if atlas_filename == '':
            return

        self.atlas_file = atlas_filename
        self.atlas_dir = '/'.join(self.atlas_file.strip().split('/')[:-1])
        self.sprites_dir = f'{self.atlas_dir}/sprites'
        self.output_dir = f'{self.atlas_dir}/output'
        decomp(self.atlas_file)
        self.displayAtlas()

        for file_str in QDir(self.sprites_dir).entryList():
            self.fs_watcher.addPath(f'{self.sprites_dir}/{file_str}')
        
        self.sprite_list.setCurrentIndex(self.sprite_list.indexAt(QPoint(0,0)))

    def saveAtlas(self):
        rebuild(self.atlas_file)
        self.openDirectory(pathlib.Path(self.output_dir))

    def searchList(self, text):
        self.proxy_model.setFilterFixedString(text)
        self.sprite_list.setRootIndex(self.proxy_model.mapFromSource(self.model.index(self.sprites_dir)))

    def listClicked(self, current_selection, previous_selection):
        
        if not self.replace_action.isVisible():
            self.replace_action.setVisible(True)

        self.selected_sprite_filename = current_selection.data()
        self.selected_sprite_fullpath = self.model.filePath(self.proxy_model.mapToSource(current_selection))
        self.selected_sprite_size = QPixmap(self.selected_sprite_fullpath).size()
        
        self.refreshSpritePreview()

        if not self.scaleSlider.isVisible():
            self.scaleSlider.setVisible(True)

        self.refresh_timer.start()

    def refreshSpritePreview(self):
        if not self.selected_sprite_fullpath:
            return
        pixmap = QPixmap(self.selected_sprite_fullpath)
        w = pixmap.width()
        ratio = 1
        while w > 1600:
            ratio += 1
            w = pixmap.width() // ratio

        self.selected_sprite_size = pixmap.size()
        self.sprite_image_label.setPixmap(pixmap.scaled(QSize(pixmap.size().width() / ratio * self.scaleSlider.value(), pixmap.size().height() * self.scaleSlider.value()), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation))
        self.sprite_image_label.setScaledContents(True)
        self.size_label.setText(f'{self.selected_sprite_size.width()} x {self.selected_sprite_size.height()}')

    def scaleSprite(self, factor):
        if not self.selected_sprite_fullpath:
            return
        pixmap = QPixmap(self.selected_sprite_fullpath)
        self.sprite_image_label.setPixmap(pixmap.scaled(QSize(factor * pixmap.size().width(), factor * pixmap.size().height()), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation))

    def replaceSingleSprite(self, idx):
        if not self.selected_sprite_filename:
            return

        replacement_filename = QFileDialog.getOpenFileName(self, f'Select Replacement {self.selected_sprite_filename}')[0]        
        if replacement_filename == '':
            return
        
        self.current_replacement_file = replacement_filename

        self.replaceSprite(self.current_replacement_file, self.selected_sprite_fullpath)
        self.refreshSpritePreview()

    def openSpriteFolder(self):
        self.openDirectory(pathlib.Path(self.sprites_dir))

    def replaceMultipleSprites(self):
        msgbox = QMessageBox()
        msgbox.setWindowIcon(QIcon('./ui/icon.png'))
        msgbox.setWindowTitle('Warning')
        msgbox.setText('Matching Sprite File Names' + ' '*30)
        msgbox.setInformativeText('Only files in the selected folder with names matching the dumped sprites will be replaced.')
        msgbox.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        msgbox.setDefaultButton(QMessageBox.StandardButton.Ok)
        msgbox_return = msgbox.exec()

        if msgbox_return == QMessageBox.StandardButton.Cancel:
            return
        
        mass_replacement_folder = QFileDialog.getExistingDirectory(self, 'Select replacement sprites directory', self.atlas_dir)

        sprite_qdir = QDir(self.sprites_dir)
        sprite_files = sprite_qdir.entryList(filters=QDir.Filter.NoDotAndDotDot | QDir.Filter.AllEntries)
        replacement_qdir = QDir(mass_replacement_folder)
        replacement_files = replacement_qdir.entryList(filters=QDir.Filter.NoDotAndDotDot | QDir.Filter.AllEntries)

        for f in replacement_files:
            if f in sprite_files:
                self.replaceSprite(f'{mass_replacement_folder}/{f}', f'{self.sprites_dir}/{f}')
                self.sprite_list.setCurrentIndex(self.proxy_model.mapFromSource(self.model.index(f'{self.sprites_dir}/{f}')))

        self.refreshSpritePreview()

    def replaceSprite(self, src: str, dst: str):
        if not QFile.exists(dst) or QFile.remove(dst):
            if not QFile.copy(src, dst):
                print('Could not copy file')
                return False
            else:
                self.setSaveButtonVisible()
        else:
            print('Could not remove file')
            return False

    def setSaveButtonVisible(self):
        if not self.save_atlas_action.isVisible():
            self.save_atlas_action.setVisible(True)

    def openDirectory(self, path: pathlib.Path):
        path_str = str(path.absolute())
        if platform.system() == 'Windows':
            QProcess.startDetached(f'explorer', [path_str])
        else:
            QDesktopServices.openUrl(path_str)
